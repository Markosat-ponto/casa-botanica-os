"""Simulador da Casa Botânica para testar o Botânico sem tocar no portão real.

Reproduz o hardware confirmado:
- motor de botão único: pulso -> abre / para / fecha / para (alternado)
- reed só na posição fechada (estado open = qualquer posição não fechada)
- integração Tuya em nuvem (internet fora -> unavailable, comando falha)
- pulsos "perdidos" (bug do módulo que não pulsa com comando repetido)
- fotocélula opcional; sem ela, fechar sobre obstáculo = COLISÃO
"""

from datetime import datetime, timedelta

from botanico.core import gate


class PortaoFisico:
    def __init__(self, curso=25.0, fotocelula=False):
        self.curso = curso
        self.pos = 0.0               # 0 fechado, 1 aberto
        self.mov = "parado"          # parado | abrindo | fechando
        self.ultima_dir = "fechando"
        self.fotocelula = fotocelula
        self.obstaculo = False
        self.colisao = False
        self.pulsos_recebidos = 0
        self.perder_proximos = 0

    def pulso(self):
        if self.perder_proximos > 0:
            self.perder_proximos -= 1
            return
        self.pulsos_recebidos += 1
        if self.mov != "parado":
            self.mov = "parado"
        elif self.pos <= 0.0:
            self.mov = self.ultima_dir = "abrindo"
        elif self.pos >= 1.0:
            self.mov = self.ultima_dir = "fechando"
        else:
            self.mov = "fechando" if self.ultima_dir == "abrindo" else "abrindo"
            self.ultima_dir = self.mov

    def passo(self, dt):
        if self.mov == "abrindo":
            self.pos = min(1.0, self.pos + dt / self.curso)
            if self.pos >= 1.0:
                self.mov = "parado"
        elif self.mov == "fechando":
            if self.obstaculo and self.pos < 0.5:
                if self.fotocelula:
                    self.mov = self.ultima_dir = "abrindo"
                    return
                self.colisao = True
                self.mov = "parado"
                return
            self.pos = max(0.0, self.pos - dt / self.curso)
            if self.pos <= 0.0:
                self.mov = "parado"

    def reed(self):
        return "closed" if self.pos <= 0.0 else "open"


class MundoSimulado:
    def __init__(self, inicio, modo="autonomo", fotocelula=False):
        self.t0 = inicio
        self.seg = 0.0
        self.portao = PortaoFisico(fotocelula=fotocelula)
        self.estado_sensor = "closed"
        self.desde = -3600.0
        self.trocas = []
        self.online = True
        self.ruido = False
        self.camera = "livre"
        self.cachorros_soltos = False
        self.fuga = False
        self._suspenso = False
        self.modo = modo
        self.notificacoes = []
        self.llm_ok = True
        self.ocupado = set()         # datas com reserva
        self.expiracoes = []

    # ---- interface do mundo
    def agora(self):
        return self.seg

    def agora_dt(self):
        return self.t0 + timedelta(seconds=self.seg)

    def leitura_portao(self):
        if not self.online:
            return gate.LeituraPortao("unavailable", self.desde)
        trocas = len([t for t in self.trocas if self.seg - t < 60])
        if self.ruido:
            trocas = 12
        return gate.LeituraPortao(self.estado_sensor, self.desde, trocas)

    def pulso_portao(self, motivo):
        if not self.online:
            return False
        self.portao.pulso()
        return True

    def analisar_camera(self):
        return self.camera

    def notificar_theo(self, texto, urgente):
        self.notificacoes.append((urgente, texto))

    def suspenso(self):
        return self._suspenso

    def modo_execucao(self):
        return self.modo

    def quarto_livre_no_dia(self, quarto, data):
        return data not in self.ocupado

    def diaria(self, quarto):
        return 250.0

    def responder_llm(self, texto, reserva):
        if not self.llm_ok:
            raise RuntimeError("sem internet")
        return "(resposta do assistente sobre: %s)" % texto

    def definir_expiracao(self, reserva, quando):
        self.expiracoes.append((reserva.id, quando))

    # ---- controle da simulação
    def avancar(self, segundos, bot=None):
        """Avança o relógio de 1 em 1 s, movendo o portão e chamando tick."""
        respostas = []
        for _ in range(int(segundos)):
            self.seg += 1
            self.portao.passo(1.0)
            novo = self.portao.reed()
            if novo != self.estado_sensor:
                self.estado_sensor = novo
                self.desde = self.seg
                self.trocas.append(self.seg)
            if self.portao.pos > 0 and self.cachorros_soltos:
                self.fuga = True
            if bot:
                respostas += bot.tick()
        return respostas


def reserva_exemplo(cadastro, inicio, saida_hora=8):
    """Hóspede do caso real: check-out com saída informada às 8h."""
    from botanico.core import guests
    hoje = inicio.replace(hour=0, minute=0, second=0, microsecond=0)
    r = guests.Reserva(
        id="R1", nome="Ana Souza", quarto="oliva",
        checkin=hoje - timedelta(days=2) + timedelta(hours=14),
        checkout=hoje + timedelta(hours=11),
        telefone="+55 62 99999-1234",
        codigo_hash=guests.hash_codigo("482913", cadastro.sal),
        credencial_expira=hoje + timedelta(hours=saida_hora),
    )
    cadastro.adicionar(r)
    return r


def novo_cenario(hora=10, minuto=15, modo="autonomo", fotocelula=True):
    from botanico.core import agent, config, guests
    inicio = datetime(2026, 11, 28, hora, minuto)
    mundo = MundoSimulado(inicio, modo=modo, fotocelula=fotocelula)
    cad = guests.Cadastro(sal="teste")
    reserva_exemplo(cad, inicio)
    cfg = dict(config.PORTAO)
    cfg["fotocelula_instalada_e_validada"] = fotocelula
    bot = agent.Botanico(mundo, cad, cfg_portao=cfg)
    return mundo, bot
