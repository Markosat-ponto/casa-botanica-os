"""Registro de ações e ocorrências (somente acréscimo) + relatório.

Nunca grava códigos, senhas ou tokens: `redigir()` mascara sequências
numéricas longas e padrões de segredo antes de qualquer gravação.
"""

import json
import re
from datetime import datetime

_PADROES = [
    (re.compile(r"\b\d{4,}\b"), "[número]"),
    (re.compile(r"(?i)(senha|token|password|bearer|api[_-]?key)\s*[:=]?\s*\S+"),
     r"\1 [oculto]"),
    (re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),
     "[token]"),
]


def redigir(texto):
    t = str(texto)
    for padrao, troca in _PADROES:
        t = padrao.sub(troca, t)
    return t


class Auditoria:
    def __init__(self, caminho=None):
        self.caminho = caminho
        self.eventos = []

    def registrar(self, agora, tipo, atendimento, resumo, nivel="info",
                  dados=None):
        ev = {
            "ts": agora if isinstance(agora, str) else
            datetime.fromtimestamp(agora).isoformat(timespec="seconds"),
            "tipo": tipo,
            "atendimento": atendimento,
            "nivel": nivel,            # info | alerta | critico | pendente_theo
            "resumo": redigir(resumo),
        }
        if dados:
            ev["dados"] = dict([(k, redigir(v)) for k, v in dados.items()])
        self.eventos.append(ev)
        if self.caminho:
            with open(self.caminho, "a", encoding="utf-8") as f:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        return ev


def relatorio(eventos, desde_iso=""):
    """Resumo em Markdown do que aconteceu (ex.: enquanto o Theo dormia)."""
    evs = [e for e in eventos if e["ts"] >= desde_iso]
    if not evs:
        return "Nada registrado no período."
    pend = [e for e in evs if e["nivel"] == "pendente_theo"]
    crit = [e for e in evs if e["nivel"] in ("critico", "alerta")]
    linhas = ["# Relatório do Botânico", ""]
    linhas.append("- Eventos: %d | Alertas: %d | Pendentes para o Theo: %d"
                  % (len(evs), len(crit), len(pend)))
    if pend:
        linhas += ["", "## Precisa de você"]
        linhas += ["- %s — %s" % (e["ts"][11:16], e["resumo"]) for e in pend]
    if crit:
        linhas += ["", "## Alertas"]
        linhas += ["- %s — %s" % (e["ts"][11:16], e["resumo"]) for e in crit]
    linhas += ["", "## Linha do tempo"]
    linhas += ["- %s [%s] %s" % (e["ts"][11:16], e["tipo"], e["resumo"])
               for e in evs]
    return "\n".join(linhas)
