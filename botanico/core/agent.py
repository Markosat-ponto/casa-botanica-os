"""Orquestrador do Botânico: mensagem -> identidade -> intenção -> política
-> protocolo -> resposta. Execução física sempre passa por `gate`.

O "mundo" (Home Assistant real ou simulador) é injetado e precisa ter:
  agora() -> epoch (float)            agora_dt() -> datetime local
  leitura_portao() -> gate.LeituraPortao
  pulso_portao(motivo) -> bool        (só chamado no modo "autonomo")
  analisar_camera() -> None|"livre"|"obstaculo"|"indisponivel"
  notificar_theo(texto, urgente)
  suspenso() -> bool                  modo_execucao() -> "simulado"|"autonomo"
  quarto_livre_no_dia(quarto, data) -> bool
  diaria(quarto) -> float|None
  responder_llm(texto, reserva) -> str|None   (sem acesso a dispositivos)
  definir_expiracao(reserva, datetime)         (persistir late checkout)
"""

import re

import botanico.core.audit as audit
import botanico.core.config as config
import botanico.core.gate as gate
import botanico.core.guests as guests
import botanico.core.intents as intents
import botanico.core.policy as policy

TEXTO = {
    "explica_expirou": ("Identifiquei que seu acesso aos controles expirou às "
                        "{hora}, conforme o horário de saída registrado. Vou "
                        "ajudar você a retirar seu carro."),
    "pede_animais": ("Antes de abrir o portão, poderia verificar se os "
                     "cachorros estão dentro do cercado?"),
    "aguardo_animais": ("Sem problema, aguardo. Me avise quando os cachorros "
                        "estiverem no cercado."),
    "vou_abrir": ("Vou verificar as condições de segurança e abrir o portão. "
                  "Assim que retirar o veículo completamente, me avise para "
                  "que eu possa realizar o fechamento."),
    "abriu": ("O portão está abrindo. Pode retirar o carro com calma e me "
              "avise quando ele tiver saído completamente."),
    "ja_aberto": ("O sensor indica que o portão já está aberto, então não vou "
                  "enviar comando (isso poderia fechá-lo). Pode retirar o carro "
                  "e me avise quando tiver saído completamente."),
    "vou_fechar": "Obrigado! Vou fechar o portão e confirmar pelo sensor.",
    "fechou": ("Portão fechado e confirmado pelo sensor. Procedimento "
               "concluído. Obrigado pela estadia e boa viagem!"),
    "ja_fechado": ("O sensor já indica o portão fechado. Procedimento "
                   "concluído. Boa viagem!"),
    "fechamento_bloqueado": ("Por segurança, o fechamento automático ainda não "
                             "está liberado aqui. Já avisei o Theo com "
                             "prioridade para fechar o portão. Pode seguir "
                             "viagem tranquilo."),
    "camera_obstaculo": ("A câmera indica algo na área do portão. Pode "
                         "conferir se a passagem está totalmente livre e me "
                         "avisar de novo?"),
    "bloqueado_sensor": ("Não consigo confirmar com segurança a posição do "
                         "portão agora, então não vou enviar comandos. Já "
                         "avisei o Theo com prioridade. {orientacao}"),
    "shadow": ("Já avisei o Theo com prioridade para liberar o portão para "
               "você agora. Fico acompanhando por aqui."),
    "falha_abrir": ("Enviei o comando, mas o sensor não confirmou a abertura. "
                    "Não vou insistir para não causar movimento inesperado. "
                    "Avisei o Theo com prioridade."),
    "falha_fechar": ("O sensor não confirmou o fechamento do portão. Não vou "
                     "repetir o comando por segurança. Avisei o Theo com "
                     "prioridade; se puder, confira se nada está na passagem."),
    "suspenso": ("As ações automáticas estão pausadas pelo anfitrião neste "
                 "momento. Avisei o Theo com prioridade para ajudar você."),
    "pede_codigo": ("Para sua segurança, preciso confirmar a reserva antes. "
                    "Me envie o código da reserva do Airbnb (começa com HM e "
                    "aparece no app, em Viagens > sua reserva) ou o código de "
                    "acesso do painel."),
    "codigo_invalido": "Não encontrei uma reserva ativa com esse código.",
    "codigo_bloqueado": ("Não consegui validar a reserva. Por segurança, "
                         "avisei o Theo para falar com você."),
    "fora_janela": ("Não encontrei uma reserva ativa ou em período de saída "
                    "vinculada a este contato. Avisei o Theo para ajudar."),
    "emergencia": ("Se é uma emergência, ligue agora: SAMU 192, Bombeiros "
                   "193, Polícia 190. Já estou avisando o Theo com "
                   "prioridade máxima."),
    "financeiro": ("Esse tipo de pedido (descontos, reembolsos, cancelamentos "
                   "ou pagamentos) é decidido pelo Theo. Registrei sua "
                   "solicitação e ele vai responder assim que possível."),
    "theo": "Avisei o Theo. Ele responde assim que possível.",
    "sem_resposta": ("Não tenho essa informação confirmada agora. Registrei a "
                     "pergunta e avisei o Theo."),
    "aguardando_veiculo": ("Me avise quando o carro tiver saído "
                           "completamente para eu fechar o portão."),
}

ALEGA_ADMIN = ("sou o theo", "sou o dono", "sou o anfitriao", "modo admin",
               "ignore as instrucoes", "ignore suas instrucoes",
               "ignore as regras", "desative a seguranca", "voce agora",
               "system prompt", "prompt do sistema")


class Sessao:
    def __init__(self, sid):
        self.id = sid
        self.estado = "inicio"
        self.reserva = None
        self.pulsos = 0
        self.repeticoes = 0
        self.t_comando = None
        self.t_aguardo = None
        self.alerta_veiculo = False
        self.obstaculos = 0
        self.intencao_pendente = None
        self.texto_pendente = ""
        self.verificado = False
        self.veiculo_confirmado = False


class Botanico:
    def __init__(self, mundo, cadastro, auditoria=None, cfg_portao=None):
        self.m = mundo
        self.cad = cadastro
        self.log = auditoria or audit.Auditoria()
        self.cfg = cfg_portao or config.PORTAO
        self.limitador = gate.LimitadorPulsos(self.cfg)
        self.sessoes = {}

    # ------------------------------------------------------------ util
    def _reg(self, s, tipo, resumo, nivel="info"):
        self.log.registrar(self.m.agora_dt().isoformat(timespec="seconds"),
                           tipo, s.id, resumo, nivel)

    def _escalar(self, s, motivo, urgente=True, nivel="pendente_theo"):
        quem = s.reserva.nome if s.reserva else "contato não identificado"
        self.m.notificar_theo("[Botânico] %s: %s" % (quem, motivo), urgente)
        self._reg(s, "escalado", motivo, nivel)

    def _sessao(self, canal, remetente):
        sid = "%s:%s" % (canal, remetente)
        if sid not in self.sessoes:
            self.sessoes[sid] = Sessao(sid)
        return self.sessoes[sid]

    # ------------------------------------------------------------ entrada
    def receber(self, canal, remetente, texto):
        s = self._sessao(canal, remetente)
        agora_dt = self.m.agora_dt()
        intent = intents.classificar_local(texto)
        self._reg(s, "mensagem", "%s via %s: %s" % (intent, canal, texto))

        if intent == "emergencia":
            self._escalar(s, "EMERGÊNCIA relatada: %s" % texto, True, "critico")
            return [TEXTO["emergencia"]]

        if any([a in intents.normalizar(texto) for a in ALEGA_ADMIN]):
            self._reg(s, "seguranca",
                      "mensagem tentou alegar privilégio/alterar regras; "
                      "nenhuma permissão concedida", "alerta")

        if s.reserva is None:
            s.reserva = guests.identificar(self.cad, canal, remetente, agora_dt)
            s.verificado = (s.reserva is not None and
                            canal in guests.CANAIS_VERIFICADOS)

        if s.estado == "aguardando_codigo":
            if guests.parece_codigo(texto):
                return self._validar_codigo(s, texto, intent)
            s.estado = "inicio"        # mudou de assunto: segue normal
            s.intencao_pendente = None

        # Código enviado espontaneamente (ex.: número que não está no cadastro).
        if intent == "codigo_acesso" and not s.verificado and \
                guests.parece_codigo(texto):
            return self._validar_codigo(s, texto, intent)

        # Pedidos sensíveis exigem identidade comprovada (código), não só o
        # telefone: o número do Airbnb pode ser de outra pessoa.
        sensiveis = ("saida_portao", "fechar_portao", "late_checkout",
                     "extensao")
        if intent in sensiveis and not s.verificado and s.estado in (
                "inicio", "concluido", "escalado", "bloqueado"):
            s.estado = "aguardando_codigo"
            s.intencao_pendente = intent
            s.texto_pendente = texto
            self._reg(s, "identidade", "pedido sensível (%s): pedindo código"
                      % intent)
            return [TEXTO["pede_codigo"]]

        # Estados do protocolo de saída têm prioridade sobre perguntas livres.
        if s.estado == "aguardando_animais":
            return self._resp_animais(s, intent)
        if s.estado == "aguardando_veiculo":
            if intent in ("veiculo_saiu", "confirmar_sim", "fechar_portao"):
                return self._fechar(s)
        if s.estado in ("abrindo", "fechando", "fechamento_agendado"):
            return ["Estou acompanhando o portão pelo sensor, um instante."]

        if intent in ("saida_portao",):
            return self._iniciar_saida(s, canal)
        if intent == "financeiro":
            self._escalar(s, "pedido financeiro: %s" % texto, False)
            return [TEXTO["financeiro"]]
        if intent == "falar_com_theo":
            self._escalar(s, "hóspede pediu para falar com o Theo: %s" % texto,
                          False)
            return [TEXTO["theo"]]
        if intent == "late_checkout":
            return self._late_checkout(s, texto)
        if intent == "extensao":
            return self._extensao(s)
        if intent == "fechar_portao":
            return self._fechar(s)

        resp = None
        try:
            resp = self.m.responder_llm(texto, s.reserva)
        except Exception as e:  # LLM fora do ar não derruba o atendimento
            self._reg(s, "falha", "LLM indisponível: %s" % e, "alerta")
        if not resp:
            self._escalar(s, "pergunta sem resposta: %s" % texto, False)
            return [TEXTO["sem_resposta"]]
        self._reg(s, "llm", "resposta gerada por LLM")
        return [resp]

    # ------------------------------------------------------------ identidade
    def _validar_codigo(self, s, texto, intent):
        r, st = self.cad.por_codigo(s.id, texto, self.m.agora_dt())
        if r:
            s.reserva = r
            s.verificado = True
            s.estado = "inicio"
            self._reg(s, "identidade", "reserva validada por código")
            pend, txt = s.intencao_pendente, s.texto_pendente
            s.intencao_pendente, s.texto_pendente = None, ""
            if pend in ("saida_portao", "fechar_portao"):
                return self._iniciar_saida(s, "verificado")
            if pend == "late_checkout":
                return self._late_checkout(s, txt)
            if pend == "extensao":
                return self._extensao(s)
            return ["Reserva confirmada, %s. Como posso ajudar?" %
                    r.primeiro_nome()]
        if st == "bloqueado" or (s.id in self.cad.tentativas and
                                 self.cad.tentativas[s.id] >=
                                 config.HOSPEDE["max_tentativas_codigo"]):
            s.estado = "bloqueado"
            self._escalar(s, "validação de código falhou repetidamente",
                          True, "alerta")
            return [TEXTO["codigo_bloqueado"]]
        return [TEXTO["codigo_invalido"] + " Pode conferir e enviar de novo?"]

    # ------------------------------------------------------------ saída
    def _iniciar_saida(self, s, canal):
        agora_dt = self.m.agora_dt()
        if s.reserva is None:
            s.estado = "aguardando_codigo"
            s.intencao_pendente = "saida_portao"
            return [TEXTO["pede_codigo"]]
        r = s.reserva
        if not r.pode_pedir_saida(agora_dt):
            s.estado = "bloqueado"
            self._escalar(s, "pedido de saída fora da janela da reserva")
            return [TEXTO["fora_janela"]]
        msgs = []
        if not r.credencial_ativa(agora_dt):
            msgs.append(TEXTO["explica_expirou"].format(
                hora=r.credencial_expira.strftime("%Hh%M")))
            self._reg(s, "diagnostico",
                      "credencial expirada às %s; hóspede em janela de saída"
                      % r.credencial_expira.strftime("%H:%M"))
        s.estado = "aguardando_animais"
        msgs.append(TEXTO["pede_animais"])
        return msgs

    def _resp_animais(self, s, intent):
        if intent == "confirmar_nao":
            return [TEXTO["aguardo_animais"]]
        if intent != "confirmar_sim":
            return ["Só para confirmar: os cachorros já estão dentro do "
                    "cercado? (sim/não)"]
        self._reg(s, "confirmacao", "hóspede confirmou animais no cercado")
        return self._abrir(s)

    def _bloqueio_fisico(self, s):
        ok, motivo, _ = policy.avaliar("protocolo_saida",
                                       {"suspenso": self.m.suspenso()})
        if not ok:
            s.estado = "escalado"
            self._escalar(s, "saída precisa de ajuda: %s" % motivo)
            return [TEXTO["suspenso"]]
        return None

    def _abrir(self, s):
        bloqueio = self._bloqueio_fisico(s)
        if bloqueio:
            return bloqueio
        agora = self.m.agora()
        leitura = self.m.leitura_portao()
        diag = gate.diagnosticar(leitura, agora, self.cfg)
        if diag["situacao"] == "aberto_parado":
            s.estado = "aguardando_veiculo"
            s.t_aguardo = agora
            self._reg(s, "portao", "já estava aberto; sem pulso")
            return [TEXTO["ja_aberto"]]
        ok, motivo = gate.checar_abertura(leitura, agora, True,
                                          self.m.modo_execucao(),
                                          self.m.suspenso(), self.cfg)
        if not ok:
            s.estado = "escalado"
            self._escalar(s, "abertura bloqueada: %s" % motivo, True, "alerta")
            orient = ("Se precisar sair já, o controle remoto ou a chave "
                      "física funcionam independentemente do sistema.")
            return [TEXTO["bloqueado_sensor"].format(orientacao=orient)]
        pode, motivo_lim = self.limitador.pode(agora, s.pulsos)
        if not pode:
            s.estado = "escalado"
            self._escalar(s, motivo_lim, True, "alerta")
            return [TEXTO["bloqueado_sensor"].format(orientacao="")]
        if self.m.modo_execucao() != "autonomo":
            s.estado = "escalado"
            self._escalar(s, "MODO SIMULADO: abriria o portão agora (%s). "
                          "Libere manualmente." % motivo, True)
            return [TEXTO["shadow"]]
        return self._pulsar(s, "abrir", [TEXTO["vou_abrir"]])

    def _pulsar(self, s, direcao, msgs):
        agora = self.m.agora()
        enviado = self.m.pulso_portao(direcao)
        self.limitador.registrar(agora)
        s.pulsos += 1
        s.t_comando = agora
        s.estado = "abrindo" if direcao == "abrir" else "fechando"
        self._reg(s, "comando", "pulso de %s enviado=%s" % (direcao, enviado))
        if not enviado:
            s.estado = "escalado"
            self._escalar(s, "comando de %s não foi aceito pela integração"
                          % direcao, True, "critico")
            return msgs + [TEXTO["falha_abrir"] if direcao == "abrir"
                           else TEXTO["falha_fechar"]]
        return msgs

    def _fechar(self, s):
        if s.estado != "aguardando_veiculo":
            return ["Para fechar o portão com segurança, primeiro preciso "
                    "acompanhar a sua saída. Quer ajuda para sair?"]
        self._reg(s, "confirmacao", "hóspede informou que o veículo saiu")
        s.veiculo_confirmado = True
        diag = gate.diagnosticar(self.m.leitura_portao(), self.m.agora(),
                                 self.cfg)
        if diag["situacao"] == "indefinido":
            # Portão provavelmente ainda terminando o curso: espera parar.
            s.estado = "fechamento_agendado"
            s.t_aguardo = self.m.agora()
            self._reg(s, "portao", "aguardando portão parar para fechar (%s)"
                      % diag["detalhe"])
            return ["Obrigado! Vou esperar o portão terminar o movimento e "
                    "então fecho e confirmo pelo sensor."]
        return self._tentar_fechar(s)

    def _tentar_fechar(self, s):
        agora = self.m.agora()
        leitura = self.m.leitura_portao()
        diag = gate.diagnosticar(leitura, agora, self.cfg)
        if diag["situacao"] == "fechado":
            s.estado = "concluido"
            self._concluir(s, "portão já fechado ao confirmar a saída")
            return [TEXTO["ja_fechado"]]
        camera = None
        try:
            camera = self.m.analisar_camera()
        except Exception:
            camera = "indisponivel"
        self._reg(s, "camera", "análise sob demanda: %s" % camera)
        ok, motivo = gate.checar_fechamento(leitura, agora, True, camera,
                                            self.m.modo_execucao(),
                                            self.m.suspenso(), self.cfg)
        if not ok and camera == "obstaculo":
            s.obstaculos += 1
            if s.obstaculos >= 2:
                s.estado = "escalado"
                self._escalar(s, "câmera indicou obstáculo duas vezes; portão "
                              "segue aberto", True, "critico")
                return [TEXTO["fechamento_bloqueado"]]
            return [TEXTO["camera_obstaculo"]]
        if not ok:
            s.estado = "escalado"
            self._escalar(s, "veículo saiu, mas fechamento bloqueado (%s). "
                          "PORTÃO ABERTO." % motivo, True, "critico")
            return [TEXTO["fechamento_bloqueado"]]
        bloqueio = self._bloqueio_fisico(s)
        if bloqueio:
            return bloqueio
        pode, motivo_lim = self.limitador.pode(agora, s.pulsos)
        if not pode:
            s.estado = "escalado"
            self._escalar(s, motivo_lim + "; PORTÃO ABERTO", True, "critico")
            return [TEXTO["fechamento_bloqueado"]]
        if self.m.modo_execucao() != "autonomo":
            s.estado = "escalado"
            self._escalar(s, "MODO SIMULADO: fecharia o portão agora. "
                          "PORTÃO ABERTO.", True, "critico")
            return [TEXTO["fechamento_bloqueado"]]
        return self._pulsar(s, "fechar", [TEXTO["vou_fechar"]])

    def _concluir(self, s, resumo):
        self._reg(s, "concluido", resumo)
        self.m.notificar_theo("[Botânico] Saída assistida concluída: %s (%s)"
                              % (s.reserva.nome if s.reserva else "?", resumo),
                              False)

    # ------------------------------------------------------------ tempo
    def tick(self):
        """Chamado a cada poucos segundos e a cada mudança do sensor.
        Retorna [(sessao_id, texto)] para entregar nos canais."""
        saida = []
        agora = self.m.agora()
        for s in list(self.sessoes.values()):
            if s.estado == "abrindo":
                saida += self._verificar_abertura(s, agora)
            elif s.estado == "fechando":
                saida += self._verificar_fechamento(s, agora)
            elif s.estado == "fechamento_agendado":
                diag = gate.diagnosticar(self.m.leitura_portao(), agora,
                                         self.cfg)
                if diag["situacao"] != "indefinido":
                    s.estado = "aguardando_veiculo"
                    msgs = self._tentar_fechar(s)
                    saida += [(s.id, t) for t in msgs]
                elif agora - s.t_aguardo > 2 * self.cfg["tempo_curso_segundos"]:
                    s.estado = "escalado"
                    self._escalar(s, "portão não estabilizou para fechar; "
                                  "PORTÃO ABERTO", True, "critico")
                    saida.append((s.id, TEXTO["fechamento_bloqueado"]))
            elif s.estado == "aguardando_veiculo" and s.t_aguardo:
                limite = config.HOSPEDE["aguardar_veiculo_minutos"] * 60
                if agora - s.t_aguardo > limite and not s.alerta_veiculo:
                    s.alerta_veiculo = True
                    self._escalar(s, "portão aberto há mais de %d min sem "
                                  "confirmação de saída do veículo" %
                                  config.HOSPEDE["aguardar_veiculo_minutos"],
                                  True, "alerta")
                    saida.append((s.id, TEXTO["aguardando_veiculo"]))
        return saida

    def _verificar_abertura(self, s, agora):
        leitura = self.m.leitura_portao()
        if leitura and leitura.estado == "open":
            s.estado = "aguardando_veiculo"
            s.t_aguardo = agora
            self._reg(s, "verificacao", "sensor confirmou portão abrindo")
            return [(s.id, TEXTO["abriu"])]
        if agora - s.t_comando < self.cfg["resposta_abertura_segundos"]:
            return []
        diag = gate.diagnosticar(leitura, agora, self.cfg)
        pode, _ = self.limitador.pode(agora, s.pulsos)
        if (diag["situacao"] == "fechado" and pode and
                s.repeticoes < self.cfg["max_repeticoes_abertura"] and
                not self.m.suspenso()):
            s.repeticoes += 1
            self._reg(s, "verificacao",
                      "sem resposta ao pulso; 1 nova tentativa permitida",
                      "alerta")
            self._pulsar(s, "abrir", [])
            return []
        s.estado = "escalado"
        self._escalar(s, "abertura não confirmada pelo sensor após %d "
                      "comando(s)" % s.pulsos, True, "critico")
        return [(s.id, TEXTO["falha_abrir"])]

    def _verificar_fechamento(self, s, agora):
        leitura = self.m.leitura_portao()
        if leitura and leitura.estado == "closed" and \
                leitura.segundos_estavel(agora) >= self.cfg["estavel_segundos"]:
            s.estado = "concluido"
            self._concluir(s, "fechamento confirmado pelo sensor")
            return [(s.id, TEXTO["fechou"])]
        if agora - s.t_comando < self.cfg["resposta_fechamento_segundos"]:
            return []
        s.estado = "escalado"
        self._escalar(s, "fechamento NÃO confirmado; não repito o comando. "
                      "PORTÃO POSSIVELMENTE ABERTO.", True, "critico")
        return [(s.id, TEXTO["falha_fechar"])]

    # ------------------------------------------------------------ regras N2
    def _late_checkout(self, s, texto):
        r = s.reserva
        if r is None:
            return ["Para ver o horário de saída preciso confirmar sua "
                    "reserva. Qual é o código de acesso?"]
        m = re.search(r"(\d{1,2})\s*(?:h|:|horas)\s*(\d{2})?", texto)
        if not m:
            return ["O check-out padrão é até 11h. Até que horas você "
                    "gostaria de ficar?"]
        hora = int(m.group(1))
        minuto = int(m.group(2) or 0)
        limite = config.REGRAS_NIVEL_2["late_checkout_max_hora"]
        livre = self.m.quarto_livre_no_dia(r.quarto, r.checkout.date())
        regra_ok = (hora < limite or (hora == limite and minuto == 0)) and livre
        ok, motivo, _ = policy.avaliar("alterar_horario_saida",
                                       {"suspenso": self.m.suspenso(),
                                        "regra_ok": regra_ok})
        if ok:
            nova = r.checkout.replace(hour=hora, minute=minuto)
            r.credencial_expira = nova
            self.m.definir_expiracao(r, nova)
            self._reg(s, "regra_n2", "saída alterada para %02d:%02d (regra "
                      "pré-aprovada)" % (hora, minuto))
            self.m.notificar_theo("[Botânico] %s: saída ajustada para %02d:%02d"
                                  " pela regra de late checkout." %
                                  (r.nome, hora, minuto), False)
            return ["Combinado: seu horário de saída foi ajustado para "
                    "%02d:%02d e seus acessos continuam ativos até lá." %
                    (hora, minuto)]
        self._escalar(s, "pedido de late checkout até %02d:%02d fora da regra "
                      "(%s)" % (hora, minuto, motivo), False)
        return ["Esse horário precisa ser confirmado pelo Theo. Já registrei "
                "o pedido e ele responde assim que possível."]

    def _extensao(self, s):
        r = s.reserva
        if r is None:
            return [TEXTO["pede_codigo"]]
        livre = self.m.quarto_livre_no_dia(r.quarto, r.checkout.date())
        valor = self.m.diaria(r.quarto)
        self._escalar(s, "interesse em extensão (quarto livre=%s)" % livre,
                      False)
        if not livre:
            return ["Infelizmente o quarto já está reservado para depois da "
                    "sua saída. Avisei o Theo caso surja alguma alternativa."]
        txt = "O quarto está livre para mais uma noite."
        if valor:
            txt += " A diária cadastrada é de R$ %.0f." % valor
        txt += (" A extensão é feita pela própria plataforma da sua reserva; "
                "avisei o Theo para enviar a proposta.")
        return [txt]
