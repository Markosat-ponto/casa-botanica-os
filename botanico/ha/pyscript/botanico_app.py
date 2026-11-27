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


def _montar_cadastro():
    """Hóspede atual a partir do snapshot persistido (sobrevive ao check-out,
    quando o script de encerramento apaga nome/telefone/código)."""
    cad = guests.Cadastro(sal=_SAL)
    d = task.executor(_ler_json, ARQ_HOSPEDE)
    if d and d.get("checkin") and d.get("checkout"):
        cad.adicionar(guests.Reserva(
            id=d.get("id", "atual"), nome=d.get("nome", ""),
            quarto=d.get("quarto", "oliva"),
            checkin=datetime.fromisoformat(d["checkin"]),
            checkout=datetime.fromisoformat(d["checkout"]),
            telefone=d.get("telefone", ""), codigo_hash=d.get("codigo_hash", ""),
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


def _entregar(sessao, texto):
    canal, remetente = sessao.split(":", 1)
    event.fire("botanico_resposta", sessao=sessao, canal=canal,
               remetente=remetente, texto=texto)
    if canal == "painel":
        input_text.set_value(entity_id="input_text.botanico_hospede_resposta",
                             value=texto[:254])


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
    for r in bot.receber(str(canal), str(remetente), str(texto)[:500]):
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
    """Guarda (com o código em hash) os dados do hóspede enquanto o acesso
    está ativo, e registra a hora em que a credencial expirou."""
    dados = task.executor(_ler_json, ARQ_HOSPEDE) or {}
    if state.get("input_boolean.hospede_acesso_ativo") == "on":
        try:
            r = service.call("calendar", "get_events", return_response=True,
                             entity_id="calendar.reservas_quarto_oliva",
                             duration={"days": 30})
            ev = r["calendar.reservas_quarto_oliva"]["events"]
            atual = [e for e in ev if str(e["start"]) <=
                     datetime.now().isoformat() <= str(e["end"]) + "T23:59"]
        except Exception:
            atual = []
        codigo = state.get("input_text.hospede_codigo_de_acesso_atual") or ""
        dados.update({
            "nome": state.get("input_text.hospede_nome") or dados.get("nome", ""),
            "telefone": state.get("input_text.hospede_telefone_whatsapp")
            or dados.get("telefone", ""),
            "codigo_hash": guests.hash_codigo(codigo, _SAL) if codigo
            else dados.get("codigo_hash", ""),
            "quarto": "oliva",
        })
        if atual:
            ini, fim = str(atual[0]["start"]), str(atual[0]["end"])
            dados["checkin"] = (ini if "T" in ini else ini + "T14:00:00")[:19]
            dados["checkout"] = (fim if "T" in fim else fim + "T11:00:00")[:19]
        dados["credencial_expira"] = None
    elif dados and not dados.get("credencial_expira"):
        dados["credencial_expira"] = datetime.now().isoformat(timespec="seconds")
    task.executor(_gravar_json, ARQ_HOSPEDE, dados)
