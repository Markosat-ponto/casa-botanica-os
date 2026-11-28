"""Camada determinística de segurança do portão.

Fatos de hardware (confirmados em 27/11/2026):
- Módulo Tuya "mini módulo pulso para garagem c/ sensor", integração nuvem.
- Um único reed magnético na posição FECHADA. Estados possíveis no HA:
  closed, open (= qualquer coisa que não seja totalmente fechado),
  unavailable/unknown (nuvem Tuya ou internet fora).
- open_cover e close_cover enviam o MESMO tipo de pulso; quem decide a
  direção é a central do motor. Portanto direção só é previsível a partir
  de um estado conhecido e parado:
    closed (estável)            -> pulso ABRE
    open estável > curso total  -> provavelmente aberto e parado -> pulso FECHA
    open recente / oscilando    -> pode estar em movimento -> NÃO pulsar
- Nenhuma fotocélula visível ao HA.

Nada aqui depende de IA. A câmera só pode bloquear.
"""

import botanico.core.config as config

DISPONIVEIS = ("open", "closed")


class LeituraPortao:
    def __init__(self, estado, desde, trocas_ultimo_minuto=0):
        self.estado = estado                  # str do HA
        self.desde = desde                    # epoch s da última troca
        self.trocas_ultimo_minuto = trocas_ultimo_minuto

    def segundos_estavel(self, agora):
        return max(0, agora - self.desde)


def diagnosticar(leitura, agora, cfg=None):
    """Classifica a leitura do sensor. Retorna dict com:
    situacao: fechado | aberto_parado | indefinido | indisponivel | contraditorio
    detalhe: texto curto para registro
    """
    cfg = cfg or config.PORTAO
    if leitura is None or leitura.estado not in DISPONIVEIS:
        return {"situacao": "indisponivel",
                "detalhe": "sensor/integração indisponível (%s)" %
                           (leitura.estado if leitura else "sem leitura")}
    if leitura.trocas_ultimo_minuto > cfg["max_trocas_por_minuto"]:
        return {"situacao": "contraditorio",
                "detalhe": "sensor oscilando (%d trocas/min)" %
                           leitura.trocas_ultimo_minuto}
    estavel = leitura.segundos_estavel(agora)
    if leitura.estado == "closed":
        if estavel >= cfg["estavel_segundos"]:
            return {"situacao": "fechado", "detalhe": "fechado e estável"}
        return {"situacao": "indefinido", "detalhe": "fechou há pouco"}
    # open
    if estavel >= cfg["tempo_curso_segundos"] + cfg["estavel_segundos"]:
        return {"situacao": "aberto_parado",
                "detalhe": "aberto há %ds (parado)" % estavel}
    return {"situacao": "indefinido",
            "detalhe": "aberto há %ds, pode estar em movimento" % estavel}


class LimitadorPulsos:
    """Impede comandos repetidos sem critério."""

    def __init__(self, cfg=None):
        self.cfg = cfg or config.PORTAO
        self.historico = []          # epochs dos pulsos (global)

    def pode(self, agora, pulsos_no_atendimento):
        recentes = [t for t in self.historico if agora - t < 3600]
        self.historico = recentes
        if pulsos_no_atendimento >= self.cfg["max_pulsos_por_atendimento"]:
            return False, "limite de comandos deste atendimento atingido"
        if len(recentes) >= self.cfg["max_pulsos_por_hora"]:
            return False, "limite de comandos por hora atingido"
        return True, ""

    def registrar(self, agora):
        self.historico.append(agora)


def checar_abertura(leitura, agora, animais_confirmados, modo, suspenso,
                    cfg=None):
    """Intertravamento para ABRIR. Retorna (ok, motivo)."""
    cfg = cfg or config.PORTAO
    if suspenso:
        return False, "ações autônomas suspensas"
    if not animais_confirmados:
        return False, "animais não confirmados no cercado"
    d = diagnosticar(leitura, agora, cfg)
    if d["situacao"] == "fechado":
        return True, d["detalhe"]
    if d["situacao"] == "aberto_parado":
        return False, "portão já consta aberto; não envio pulso (fecharia)"
    return False, d["detalhe"]


def checar_fechamento(leitura, agora, veiculo_confirmado, camera, modo,
                      suspenso, cfg=None):
    """Intertravamento para FECHAR. Retorna (ok, motivo).

    camera: None (sem análise) | "livre" | "obstaculo" | "indisponivel"
    """
    cfg = cfg or config.PORTAO
    if suspenso:
        return False, "ações autônomas suspensas"
    if not cfg["fotocelula_instalada_e_validada"]:
        return False, ("fechamento autônomo bloqueado: falta fotocélula "
                       "instalada e validada")
    if not veiculo_confirmado:
        return False, "saída do veículo não confirmada pelo hóspede"
    if camera == "obstaculo":
        return False, "câmera indica pessoa/animal/veículo/obstáculo na área"
    d = diagnosticar(leitura, agora, cfg)
    if d["situacao"] == "aberto_parado":
        return True, d["detalhe"]
    if d["situacao"] == "fechado":
        return False, "portão já está fechado"
    return False, d["detalhe"]
