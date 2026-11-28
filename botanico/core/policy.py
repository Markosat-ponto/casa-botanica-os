"""Matriz de permissões do Botânico.

Determinística e independente da IA. Mensagens de hóspedes nunca alteram
estas regras: o texto do hóspede só pode PEDIR uma ação do catálogo; quem
decide se ela pode acontecer é `avaliar()`.
"""

LIVRE = 1        # pode executar sem autorização individual
REGRA = 2        # só se as regras pré-aprovadas forem atendidas
THEO = 3         # sempre exige autorização do Theo

CATALOGO = {
    # nível 1
    "responder": LIVRE,
    "consultar_reserva": LIVRE,
    "orientar": LIVRE,
    "diagnosticar": LIVRE,
    "controlar_dispositivo_quarto": LIVRE,
    "recuperar_acesso": LIVRE,
    "protocolo_saida": LIVRE,      # ainda sujeito ao modo de execução física
    "registrar": LIVRE,
    "informar_valores": LIVRE,
    "emergencia": LIVRE,
    # nível 2
    "conceder_acesso_temporario": REGRA,
    "alterar_horario_saida": REGRA,
    "extensao_hospedagem": REGRA,
    "reiniciar_equipamento_nao_critico": REGRA,
    "acesso_excepcional": REGRA,
    # nível 3
    "cancelar_reserva": THEO,
    "desconto": THEO,
    "reembolso": THEO,
    "alterar_preco": THEO,
    "pagamento": THEO,
    "alterar_regras": THEO,
    "alterar_seguranca": THEO,
    "excluir_registro": THEO,
    "acesso_administrativo": THEO,
    "desativar_protecao": THEO,
}

# Ações que mexem em algo físico e param quando a suspensão está ativa.
FISICAS = {"protocolo_saida", "controlar_dispositivo_quarto",
           "reiniciar_equipamento_nao_critico", "conceder_acesso_temporario",
           "acesso_excepcional"}

# Ações que nunca são bloqueadas (nem pela suspensão).
SEMPRE_PERMITIDAS = {"emergencia", "responder", "orientar", "registrar"}


def avaliar(acao, contexto):
    """Retorna (permitido: bool, motivo: str, precisa_theo: bool).

    contexto: dict com
      suspenso (bool)          -> chave de suspensão imediata do painel admin
      regra_ok (bool)          -> resultado da checagem de regra nível 2
      origem_admin (bool)      -> pedido veio de canal autenticado do Theo
    """
    nivel = CATALOGO.get(acao)
    if nivel is None:
        return False, "ação fora do catálogo", False
    if acao in SEMPRE_PERMITIDAS:
        return True, "sempre permitida", False
    if contexto.get("suspenso") and (acao in FISICAS or nivel >= REGRA):
        return False, "ações autônomas suspensas pelo anfitrião", True
    if nivel == LIVRE:
        return True, "nível 1", False
    if nivel == REGRA:
        if contexto.get("regra_ok"):
            return True, "regra pré-aprovada atendida", False
        return False, "regra pré-aprovada não atendida", True
    # nível 3: nem o canal do hóspede nem a IA conseguem liberar.
    if contexto.get("origem_admin"):
        return True, "autorizado pelo anfitrião", False
    return False, "exige autorização do anfitrião", True


# ------------------------------------------------------------------ coanfitrião
# O Botânico é coanfitrião 24 h: quando o Theo está atendendo, ele recua;
# quando o Theo não responde, ele assume. Urgências nunca esperam.
URGENTES = ("emergencia", "saida_portao", "fechar_portao", "veiculo_saiu",
            "confirmar_sim", "confirmar_nao", "codigo_acesso")

ESPERA_THEO_MIN = 4          # minutos esperando o Theo antes de responder
THEO_ASSUME_HORAS = 2        # "deixa comigo" silencia o Botânico por 2 h

COMANDOS_THEO_ASSUMIR = ("deixa comigo", "ja vi", "já vi", "eu respondo",
                         "eu resolvo", "to vendo", "tô vendo", "estou vendo",
                         "pode deixar", "botanico para", "botânico para")
COMANDOS_THEO_DEVOLVER = ("botanico assume", "botânico assume", "assume",
                          "pode responder", "responde voce", "responde você")


def precisa_esperar_theo(intencao, canal):
    """Mensagem comum de hóspede no WhatsApp espera o Theo alguns minutos;
    urgências e canais do quarto (painel/portal) são atendidos na hora."""
    if canal != "whatsapp":
        return False
    return intencao not in URGENTES


def comando_do_theo(texto):
    """'assumir' | 'devolver' | None a partir de uma mensagem do Theo."""
    import unicodedata
    t = unicodedata.normalize("NFKD", str(texto or "").lower())
    t = " ".join("".join([c for c in t if not unicodedata.combining(c)]).split())
    for c in COMANDOS_THEO_DEVOLVER:
        c2 = "".join([x for x in unicodedata.normalize("NFKD", c)
                      if not unicodedata.combining(x)])
        if c2 in t:
            return "devolver"
    for c in COMANDOS_THEO_ASSUMIR:
        c2 = "".join([x for x in unicodedata.normalize("NFKD", c)
                      if not unicodedata.combining(x)])
        if c2 in t:
            return "assumir"
    return None
