"""Identidade e autorização de hóspedes.

Princípio do caso real: a SAÍDA de um hóspede validado nunca depende da
validade da credencial de controle. Credencial expira -> some o controle
de dispositivos, mas continua a janela de suporte de saída.
"""

import hashlib
import hmac
from datetime import timedelta

from botanico.core import config


def hash_codigo(codigo, sal):
    return hashlib.sha256((sal + ":" + str(codigo).strip()).encode()).hexdigest()


def _so_digitos(txt):
    return "".join([c for c in str(txt or "") if c.isdigit()])


class Reserva:
    def __init__(self, id, nome, quarto, checkin, checkout, telefone="",
                 codigo_hash="", credencial_expira=None, saida_informada=None):
        self.id = id
        self.nome = nome
        self.quarto = quarto
        self.checkin = checkin            # datetime
        self.checkout = checkout          # datetime
        self.telefone = _so_digitos(telefone)
        self.codigo_hash = codigo_hash
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

    def por_codigo(self, sessao_id, codigo, agora, cfg=None):
        cfg = cfg or config.HOSPEDE
        n = self.tentativas.get(sessao_id, 0)
        if n >= cfg["max_tentativas_codigo"]:
            return None, "bloqueado"
        h = hash_codigo(codigo, self.sal)
        for r in self.ativas_ou_em_suporte(agora):
            if r.codigo_hash and hmac.compare_digest(r.codigo_hash, h):
                self.tentativas.pop(sessao_id, None)
                return r, "ok"
        self.tentativas[sessao_id] = n + 1
        return None, "invalido"


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
