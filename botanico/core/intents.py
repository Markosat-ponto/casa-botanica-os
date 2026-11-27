"""Interpretação de mensagens.

1º classificador local por palavras-chave (grátis, funciona sem internet).
2º (opcional) classificador LLM, cuja saída é VALIDADA contra a lista
fechada INTENCOES: qualquer coisa fora dela vira "pergunta_livre".
O texto do hóspede nunca é tratado como instrução de sistema.
"""

import re
import unicodedata

INTENCOES = (
    "emergencia",
    "saida_portao",        # quer sair / abrir portão / tirar o carro
    "fechar_portao",
    "confirmar_sim",
    "confirmar_nao",
    "veiculo_saiu",
    "codigo_acesso",       # mensagem parece um código numérico
    "late_checkout",
    "extensao",
    "financeiro",          # desconto, reembolso, cancelamento, pagamento
    "falar_com_theo",
    "pergunta_livre",
)

EMERGENCIA = ("incendio", "fogo", "fumaca", "socorro", "desmaio", "desmaiou",
              "sangue", "sangrando", "infarto", "assalto", "ladrao", "arma",
              "vazamento de gas", "cheiro de gas", "choque eletrico",
              "nao respira", "emergencia", "ambulancia")
SAIDA = ("sair", "saida", "abrir o portao", "abre o portao", "abrir portao",
         "abre portao", "abrir a garagem", "tirar o carro", "retirar o carro",
         "tirar meu carro", "nao consigo abrir", "portao nao abre",
         "preso", "presa", "trancado", "trancada")
FECHAR = ("fechar o portao", "fecha o portao", "fechar portao",
          "fecha portao")
VEICULO_SAIU = ("ja sai", "ja saiu", "carro saiu", "carro ja saiu", "sai com o carro",
                "estou fora", "to fora", "tô fora", "ja estou na rua",
                "pode fechar", "saiu completamente", "ja tirei")
SIM = ("sim", "estao", "estão", "ok", "pode", "confirmo", "isso", "certo",
       "claro", "positivo", "ja estao", "tudo certo", "s")
NAO = ("nao", "não", "ainda nao", "espera", "aguarda", "negativo", "n")
LATE = ("late checkout", "sair mais tarde", "ficar ate", "ficar mais",
        "sair depois", "horario de saida")
EXTENSAO = ("mais uma diaria", "mais uma noite", "estender", "prorrogar",
            "extensao", "ficar mais um dia")
FINANCEIRO = ("desconto", "reembolso", "estorno", "cancelar a reserva",
              "cancelamento", "devolver o dinheiro", "pagamento", "pagar")
THEO = ("falar com o theo", "chama o theo", "chamar o theo", "anfitriao",
        "falar com alguem", "humano")


def normalizar(texto):
    t = unicodedata.normalize("NFKD", str(texto or "").lower())
    t = "".join([c for c in t if not unicodedata.combining(c)])
    return " ".join(t.replace("?", " ").replace("!", " ").replace(",", " ")
                    .replace(".", " ").split())


def _tem(t, termos):
    palavras = set(t.split())
    for termo in termos:
        termo_n = normalizar(termo)
        if " " in termo_n:
            if termo_n in t:
                return True
        elif termo_n in palavras:
            return True
    return False


def classificar_local(texto):
    t = normalizar(texto)
    if not t:
        return "pergunta_livre"
    if _tem(t, EMERGENCIA):
        return "emergencia"
    if re.search(r"\bhm[a-z0-9]{6,10}\b", t):
        return "codigo_acesso"
    so_digitos = t.replace(" ", "")
    if so_digitos.isdigit() and 4 <= len(so_digitos) <= 12:
        return "codigo_acesso"
    if _tem(t, FINANCEIRO):
        return "financeiro"
    if _tem(t, VEICULO_SAIU):
        return "veiculo_saiu"
    if _tem(t, FECHAR):
        return "fechar_portao"
    if _tem(t, SAIDA) or ("portao" in t and ("abr" in t or "sair" in t)):
        return "saida_portao"
    if _tem(t, EXTENSAO):
        return "extensao"
    if _tem(t, LATE):
        return "late_checkout"
    if _tem(t, THEO):
        return "falar_com_theo"
    # respostas curtas de confirmação
    if len(t.split()) <= 4:
        if _tem(t, NAO):
            return "confirmar_nao"
        if _tem(t, SIM):
            return "confirmar_sim"
    return "pergunta_livre"


def validar_saida_llm(valor):
    """Aceita só uma intenção da lista fechada."""
    v = normalizar(valor).replace(" ", "_")
    return v if v in INTENCOES else "pergunta_livre"
