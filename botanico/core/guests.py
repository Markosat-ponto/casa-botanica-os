"""Identidade e autorização de hóspedes.

Princípio do caso real: a SAÍDA de um hóspede validado nunca depende da
validade da credencial de controle. Credencial expira -> some o controle
de dispositivos, mas continua a janela de suporte de saída.
"""

import hashlib
import hmac
from datetime import timedelta

import botanico.core.config as config


def hash_codigo(codigo, sal):
    return hashlib.sha256((sal + ":" + str(codigo).strip()).encode()).hexdigest()


def _so_digitos(txt):
    return "".join([c for c in str(txt or "") if c.isdigit()])


class Reserva:
    def __init__(self, id, nome, quarto, checkin, checkout, telefone="",
                 codigo_hash="", credencial_expira=None, saida_informada=None,
                 codigo_reserva_hash=""):
        self.id = id
        self.nome = nome
        self.quarto = quarto
        self.checkin = checkin            # datetime
        self.checkout = checkout          # datetime
        self.telefone = _so_digitos(telefone)
        self.codigo_hash = codigo_hash
        # Código da reserva do Airbnb (HM...), em hash. Só quem fez a reserva
        # vê no app; é a prova de identidade fora do painel.
        self.codigo_reserva_hash = codigo_reserva_hash
        self.credencial_expira = credencial_expira or checkout
        self.saida_informada = saida_informada

    def primeiro_nome(self):
        return (self.nome or "").split(" ")[0]

    def credencial_ativa(self, agora):
        return self.checkin <= agora < self.credencial_expira

    def suporte_saida_ate(self, cfg=None):
        cfg = cfg or config.HOSPEDE
        a = self.credencial_expira + timedelta(
            hours=cfg["suporte_horas_apos_expiracao"])
        minimo = self.credencial_expira.replace(
            hour=cfg["suporte_minimo_ate_hora"], minute=0, second=0,
            microsecond=0)
        return max(a, minimo)

    def pode_pedir_saida(self, agora):
        return self.checkin <= agora < self.suporte_saida_ate()


class Cadastro:
    """Fonte de reservas. Em produção é alimentado pelo calendário Airbnb +
    helpers do painel; aqui é uma lista em memória."""

    def __init__(self, sal):
        self.sal = sal
        self.reservas = []
        self.tentativas = {}

    def adicionar(self, reserva):
        self.reservas.append(reserva)

    def ativas_ou_em_suporte(self, agora):
        return [r for r in self.reservas if r.pode_pedir_saida(agora)]

    def por_telefone(self, telefone, agora):
        tel = _so_digitos(telefone)
        if len(tel) < 8:
            return None
        for r in self.ativas_ou_em_suporte(agora):
            if r.telefone and r.telefone[-8:] == tel[-8:]:
                return r
        return None

    def por_quarto(self, quarto, agora):
        """Painel físico do quarto: o dispositivo já é o fator de identidade."""
        for r in self.ativas_ou_em_suporte(agora):
            if r.quarto == quarto:
                return r
        return None

    def por_codigo(self, sessao_id, texto, agora, cfg=None):
        """Valida o código de ACESSO (dígitos) ou o código da RESERVA (HM...).
        Retorna (reserva|None, "ok"|"invalido"|"bloqueado")."""
        cfg = cfg or config.HOSPEDE
        n = self.tentativas.get(sessao_id, 0)
        if n >= cfg["max_tentativas_codigo"]:
            return None, "bloqueado"
        cod_reserva = extrair_codigo_reserva(texto)
        digitos = _so_digitos(texto)
        h_res = hash_codigo(cod_reserva, self.sal) if cod_reserva else ""
        h_acc = hash_codigo(digitos, self.sal) if len(digitos) >= 4 else ""
        for r in self.ativas_ou_em_suporte(agora):
            if h_res and r.codigo_reserva_hash and hmac.compare_digest(
                    r.codigo_reserva_hash, h_res):
                self.tentativas.pop(sessao_id, None)
                return r, "ok"
            if h_acc and r.codigo_hash and hmac.compare_digest(
                    r.codigo_hash, h_acc):
                self.tentativas.pop(sessao_id, None)
                return r, "ok"
        self.tentativas[sessao_id] = n + 1
        return None, "invalido"


def extrair_codigo_reserva(texto):
    """Código de reserva do Airbnb: 'HM' + 8 letras/números (aceita 6 a 10)."""
    import re
    m = re.search(r"\b(HM[A-Z0-9]{6,10})\b", str(texto or "").upper())
    return m.group(1) if m else ""


def parece_codigo(texto):
    return bool(extrair_codigo_reserva(texto)) or len(_so_digitos(texto)) >= 4


# Canais onde o próprio canal já prova a identidade (dispositivo logado no
# quarto). Telefone NÃO prova: o número do Airbnb pode ser de outra pessoa.
CANAIS_VERIFICADOS = ("painel",)


def identificar(cadastro, canal, remetente, agora):
    """Identificação automática pelo canal. Retorna Reserva ou None.

    canal: painel (remetente = quarto) | whatsapp (remetente = telefone)
           | site (sem identificação automática: pede código)
    """
    if canal == "painel":
        return cadastro.por_quarto(remetente, agora)
    if canal == "whatsapp":
        return cadastro.por_telefone(remetente, agora)
    return None
