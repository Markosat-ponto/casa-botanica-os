"""Adaptador pyscript: liga o núcleo do Botânico ao Home Assistant real.

STATUS: instalado em modo SIMULADO (27/11/2026). Escrito contra a API do pyscript e as entidades
confirmadas em 27/11/2026, mas ainda não executado no HA. Instalação e
validação seguem docs/botanico/06-manutencao.md.

Instalação prevista:
  /config/pyscript/modules/botanico/      (cópia de botanico/__init__.py e
                                           botanico/core/ — interpretado pelo
                                           pyscript, para poder chamar
                                           service.call/state.get)
  /config/pyscript/apps/botanico_app.py   (este arquivo)
  /config/botanico/                       (auditoria e snapshot do hóspede)
  pyscript: allow_all_imports: true, hass_is_global: false

Canais entram por evento (desacoplado):
  event_type: botanico_mensagem   data: {canal, remetente, texto}
Respostas saem por evento + helper do painel:
  event_type: botanico_resposta   data: {sessao, canal, remetente, texto}

Segurança:
- Só chama script.portao_abrir / script.portao_fechar (já existentes).
- Nunca usa script.portao_alternar_inteligente (alterna sem saber posição).
- Começa em modo "simulado"; só o Theo muda input_select.botanico_modo_de_execucao_fisica.
- Agente LLM usado aqui precisa estar SEM acesso a dispositivos.
"""

import json
import time
from datetime import datetime

import botanico.core.agent as agent
import botanico.core.audit as audit
import botanico.core.config as config
import botanico.core.gate as gate
import botanico.core.guests as guests

COVER = config.PORTAO["entidade_cover"]
CAMERA = config.PORTAO["camera_entidade"]
H_MODO = "input_select.botanico_modo_de_execucao_fisica"
H_SUSPENSO = "input_boolean.botanico_suspender_acoes_autonomas"
H_FOTOCELULA = "input_boolean.portao_fotocelula_instalada_e_validada_so_o_theo"
H_STATUS = "input_text.botanico_ultimo_evento"
AGENTE_LLM = "conversation.botanico_hospede"
AI_TASK = "ai_task.openai_ai_task"
NOTIFY = ["mobile_app_iphone", "mobile_app_realme_theo_android"]
ARQ_AUDIT = "/config/botanico/auditoria.jsonl"
ARQ_HOSPEDE = "/config/botanico/hospede_atual.json"


@pyscript_compile
def _ler_json(caminho):
    import json
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


@pyscript_compile
def _gravar_json(caminho, dados):
    import json
    import os
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False)


class MundoHA:
    """Implementa a interface de mundo do núcleo usando o HA."""

    def agora(self):
        return time.time()

    def agora_dt(self):
        return datetime.now()

    def leitura_portao(self):
        estado = state.get(COVER)
        try:
            desde = state.get(COVER + ".last_changed").timestamp()
        except Exception:
            desde = time.time()
        return gate.LeituraPortao(estado, desde, _trocas_recentes())

    def pulso_portao(self, direcao):
        alvo = "script.portao_abrir" if direcao == "abrir" else "script.portao_fechar"
        try:
            service.call("script", "turn_on", entity_id=alvo)
            return True
        except Exception as e:
            log.error("Botânico: falha no comando %s: %s" % (direcao, e))
            return False

    def analisar_camera(self):
        try:
            r = service.call(
                "ai_task", "generate_data", return_response=True,
                task_name="botanico_area_portao", entity_id=AI_TASK,
                instructions=("Analise a área de movimentação do portão da "
                              "garagem. Responda 'obstaculo' se houver pessoa, "
                              "animal, veículo ou objeto na passagem; senão "
                              "'livre'. Na dúvida, 'obstaculo'."),
                structure={"situacao": {"selector": {"select": {
                    "options": ["livre", "obstaculo"]}}, "required": True}},
                attachments=[{"media_content_id":
                              "media-source://camera/" + CAMERA,
                              "media_content_type": "image/jpeg"}])
            v = (r or {}).get("data", {}).get("situacao", "")
            return v if v in ("livre", "obstaculo") else "obstaculo"
        except Exception as e:
            log.warning("Botânico: câmera indisponível: %s" % e)
            return "indisponivel"

    def notificar_theo(self, texto, urgente):
        dados = {"push": {"interruption-level":
                          "time-sensitive" if urgente else "active"}}
        for alvo in NOTIFY:
            try:
                service.call("notify", alvo, title="🌿 Botânico",
                             message=texto, data=dados)
            except Exception as e:
                log.warning("Botânico: notificação %s falhou: %s" % (alvo, e))

    def suspenso(self):
        return state.get(H_SUSPENSO) != "off"   # desconhecido = suspenso

    def modo_execucao(self):
        return "autonomo" if state.get(H_MODO) == "autonomo" else "simulado"

    def quarto_livre_no_dia(self, quarto, data):
        ent = "calendar.reservas_quarto_" + quarto
        try:
            r = service.call("calendar", "get_events", return_response=True,
                             entity_id=ent,
                             start_date_time=data.isoformat() + "T12:00:00",
                             end_date_time=data.isoformat() + "T23:59:00")
            eventos = r.get(ent, {}).get("events", [])
            return not any([str(e.get("start", ""))[:10] == data.isoformat()
                            for e in eventos])
        except Exception:
            return False          # sem dados -> trata como ocupado

    def diaria(self, quarto):
        try:
            v = float(state.get("input_number.reservas_diaria_quarto_%s_site"
                                % quarto))
            return v if v > 0 else None
        except Exception:
            return None

    def responder_llm(self, texto, reserva):
        r = service.call("conversation", "process", return_response=True,
                         text=texto, agent_id=AGENTE_LLM, language="pt-BR")
        return r["response"]["speech"]["plain"]["speech"]

    def definir_expiracao(self, reserva, quando):
        dados = task.executor(_ler_json, ARQ_HOSPEDE) or {}
        dados["credencial_expira"] = quando.isoformat()
        task.executor(_gravar_json, ARQ_HOSPEDE, dados)


_TROCAS = []


def _trocas_recentes():
    agora = time.time()
    return len([t for t in _TROCAS if agora - t < 60])


def _cfg_portao():
    cfg = dict(config.PORTAO)
    cfg["fotocelula_instalada_e_validada"] = state.get(H_FOTOCELULA) == "on"
    return cfg


def _validar_no_portal(codigo):
    """Pergunta ao portal do hóspede se o código de acesso é válido.
    Contrato (tarefa 036 do canal): pyscript.oliva_validar_codigo
    {quarto, codigo} -> {"valido": bool}. O portal limita tentativas e o
    Botânico nunca recebe nem guarda a senha. Sem o serviço: inválido."""
    try:
        r = service.call("pyscript", "oliva_validar_codigo",
                         return_response=True, quarto="oliva",
                         codigo=str(codigo))
        return bool((r or {}).get("valido", False))
    except Exception:
        return False


def _montar_cadastro():
    """Hóspede atual a partir do snapshot persistido (sobrevive ao check-out,
    quando o script de encerramento apaga nome/telefone/código)."""
    cad = guests.Cadastro(sal=_SAL, validador_externo=_validar_no_portal)
    d = task.executor(_ler_json, ARQ_HOSPEDE)
    if d and d.get("checkin") and d.get("checkout"):
        cad.adicionar(guests.Reserva(
            id=d.get("id", "atual"), nome=d.get("nome", ""),
            quarto=d.get("quarto", "oliva"),
            checkin=datetime.fromisoformat(d["checkin"]),
            checkout=datetime.fromisoformat(d["checkout"]),
            telefone=d.get("telefone", ""), codigo_hash=d.get("codigo_hash", ""),
            codigo_reserva_hash=d.get("codigo_reserva_hash", ""),
            credencial_expira=datetime.fromisoformat(
                d.get("credencial_expira") or d["checkout"])))
    return cad


_SAL = "casa-botanica"   # trocar por valor do secrets.yaml na instalação
_AUD = audit.Auditoria()
_BOT = None


def _bot():
    global _BOT
    if _BOT is None:
        _BOT = agent.Botanico(MundoHA(), _montar_cadastro(), _AUD, _cfg_portao())
    _BOT.cfg = _cfg_portao()
    _BOT.cad = _montar_cadastro()
    return _BOT


_ENVIADAS = {}      # remetente -> (texto, epoch) para evitar eco/loop


def _entregar(sessao, texto):
    canal, remetente = sessao.split(":", 1)
    event.fire("botanico_resposta", sessao=sessao, canal=canal,
               remetente=remetente, texto=texto)
    if canal == "painel":
        input_text.set_value(entity_id="input_text.botanico_hospede_resposta",
                             value=texto[:254])
    elif canal == "whatsapp":
        # Texto simples (sem áudio = sem custo de API). Só chega aqui para
        # remetente identificado como hóspede da reserva atual.
        _ENVIADAS[remetente] = (texto.strip(), time.time())
        try:
            service.call("whatsapp", "send_message", target=remetente,
                         message="🌿 " + texto if not texto.startswith("🌿")
                         else texto)
        except Exception as e:
            log.error("Botânico: falha ao responder no WhatsApp: %s" % e)


@pyscript_compile
def _append_auditoria(caminho, evs):
    import json
    import os
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "a", encoding="utf-8") as f:
        for e in evs:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def _persistir_auditoria(qtd_antes):
    novos = _AUD.eventos[qtd_antes:]
    if not novos:
        return

    task.executor(_append_auditoria, ARQ_AUDIT, novos)
    ultimo = novos[-1]
    input_text.set_value(entity_id=H_STATUS,
                         value=("%s %s" % (ultimo["ts"][11:16],
                                           ultimo["resumo"]))[:254])


@event_trigger("botanico_mensagem")
def botanico_mensagem(canal=None, remetente=None, texto=None, **kw):
    if not canal or not remetente or not texto:
        return
    bot = _bot()
    n = len(_AUD.eventos)
    canal, remetente, texto = str(canal), str(remetente), str(texto)[:500]
    if canal == "whatsapp":
        # 1) eco da nossa própria resposta (proteção contra loop)
        ult = _ENVIADAS.get(remetente)
        if ult and ult[0] in texto and time.time() - ult[1] < 120:
            return
        # 2) só responde hóspede da reserva atual / janela de saída;
        #    número desconhecido: não responde (o aviso ao Theo já existe)
        sess = bot.sessoes.get("whatsapp:" + remetente)
        ja_verificado = sess is not None and sess.verificado
        conhecido = guests.identificar(bot.cad, "whatsapp", remetente,
                                       datetime.now()) is not None
        traz_codigo = bool(guests.extrair_codigo_reserva(texto))
        if not (ja_verificado or conhecido or traz_codigo):
            _AUD.registrar(datetime.now().isoformat(timespec="seconds"),
                           "ignorado", "whatsapp",
                           "mensagem de número que não é hóspede atual")
            _persistir_auditoria(n)
            return
    for r in bot.receber(canal, remetente, texto):
        _entregar("%s:%s" % (canal, remetente), r)
    _persistir_auditoria(n)


@state_trigger(COVER)
def botanico_sensor_portao(**kw):
    _TROCAS.append(time.time())
    _tick()


@time_trigger("period(now, 2s)")
def botanico_relogio():
    if _BOT is None:
        return
    if any([s.estado in ("abrindo", "fechando", "fechamento_agendado",
                         "aguardando_veiculo") for s in _BOT.sessoes.values()]):
        _tick()


def _tick():
    bot = _bot()
    n = len(_AUD.eventos)
    for sessao, texto in bot.tick():
        _entregar(sessao, texto)
    _persistir_auditoria(n)


@time_trigger("period(now, 5min)")
@state_trigger("input_boolean.hospede_acesso_ativo")
def botanico_snapshot_hospede(**kw):
    """Mantém o cadastro da reserva atual a partir do calendário do Airbnb
    (datas + código da reserva em hash) e, enquanto o acesso estiver ativo,
    dos helpers do painel (nome, telefone, código de acesso em hash).
    Sobrevive ao check-out, quando o encerramento apaga os helpers."""
    import re as _re
    dados = task.executor(_ler_json, ARQ_HOSPEDE) or {}
    agora_iso = datetime.now().isoformat()
    try:
        r = service.call("calendar", "get_events", return_response=True,
                         entity_id="calendar.reservas_quarto_oliva",
                         duration={"days": 30})
        ev = r["calendar.reservas_quarto_oliva"]["events"]
        atual = [e for e in ev if str(e["start"]) <= agora_iso <=
                 str(e["end"])[:10] + "T23:59"]
    except Exception:
        atual = []
    if atual:
        e = atual[0]
        ini, fim = str(e["start"]), str(e["end"])
        if dados.get("checkin") and str(dados["checkin"])[:10] != ini[:10]:
            dados = {}              # reserva nova: não herda a anterior
        dados["checkin"] = (ini if "T" in ini else ini + "T14:00:00")[:19]
        dados["checkout"] = (fim if "T" in fim else fim + "T11:00:00")[:19]
        m = _re.search(r"details/(HM[A-Z0-9]+)", str(e.get("description", "")))
        if m:
            dados["codigo_reserva_hash"] = guests.hash_codigo(m.group(1), _SAL)
        dados["quarto"] = "oliva"
        dados["id"] = ini[:10]
    if (state.get("input_boolean.hospede_acesso_ativo") == "on" and dados
            and dados.get("origem") != "portal"):
        codigo = state.get("input_text.hospede_codigo_de_acesso_atual") or ""
        tel = state.get("input_text.hospede_telefone_whatsapp") or ""
        nome = state.get("input_text.hospede_nome") or ""
        if nome:
            dados["nome"] = nome
        if tel:
            dados["telefone"] = tel
        if codigo:
            dados["codigo_hash"] = guests.hash_codigo(codigo, _SAL)
        dados["acesso_ja_ativo"] = True
        dados["credencial_expira"] = None
    elif (dados.get("acesso_ja_ativo") and not dados.get("credencial_expira")
          and dados.get("origem") != "portal"):
        # só o painel antigo usa o helper; o portal avisa por evento
        dados["credencial_expira"] = datetime.now().isoformat(timespec="seconds")
    task.executor(_gravar_json, ARQ_HOSPEDE, dados)


@event_trigger("botanico_acesso_hospede")
def botanico_acesso_do_portal(acao=None, quarto=None, nome=None, telefone=None,
                              saida_prevista=None, geracao=None, **kw):
    """Aviso do portal do hóspede (contrato da tarefa 036): acesso gerado,
    encerrado ou expirado. Nunca traz senha/código."""
    if str(quarto or "oliva") != "oliva" or acao not in (
            "gerado", "encerrado", "expirado"):
        return
    dados = task.executor(_ler_json, ARQ_HOSPEDE) or {}
    dados["origem"] = "portal"
    if acao == "gerado":
        dados["acesso_ja_ativo"] = True
        dados["geracao"] = str(geracao or "")
        if nome:
            dados["nome"] = str(nome)
        if telefone:
            dados["telefone"] = str(telefone)     # só indício, não prova
        dados["credencial_expira"] = (str(saida_prevista)[:19]
                                      if saida_prevista else None)
    else:
        agora = datetime.now().isoformat(timespec="seconds")
        atual = dados.get("credencial_expira")
        if not atual or str(atual) > agora:
            dados["credencial_expira"] = agora
    task.executor(_gravar_json, ARQ_HOSPEDE, dados)
    _AUD.registrar(datetime.now().isoformat(timespec="seconds"), "portal",
                   "portal", "acesso do hóspede %s pelo portal" % acao)
    _persistir_auditoria(len(_AUD.eventos) - 1)
