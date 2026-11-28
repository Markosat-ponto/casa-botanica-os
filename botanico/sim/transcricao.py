"""Gera a conversa simulada do caso real, para leitura humana.

    python -m botanico.sim.transcricao
"""

from botanico.core import audit
from botanico.sim.simulator import novo_cenario

CANAL = ("whatsapp", "5562999991234")


def roteiro(fotocelula):
    m, bot = novo_cenario(fotocelula=fotocelula)
    linhas = []

    def h(txt):
        linhas.append("**Hóspede (%s):** %s" % (m.agora_dt().strftime("%H:%M:%S"), txt))
        for r in bot.receber(CANAL[0], CANAL[1], txt):
            linhas.append("**Botânico:** %s" % r)

    def esperar(seg):
        for _ in range(seg):
            for _, r in m.avancar(1, bot):
                linhas.append("**Botânico (%s):** %s" % (
                    m.agora_dt().strftime("%H:%M:%S"), r))

    h("Não consigo abrir o portão para sair.")
    h("Sim, estão.")
    esperar(40)
    h("Pronto, o carro já saiu.")
    esperar(60)
    linhas.append("")
    linhas.append("_Portão: posição=%.0f%%, colisão=%s, pulsos=%d. "
                  "Notificações ao Theo: %d._" % (
                      m.portao.pos * 100, m.portao.colisao,
                      m.portao.pulsos_recebidos, len(m.notificacoes)))
    return "\n\n".join(linhas), bot


if __name__ == "__main__":
    for foto, titulo in ((True, "Com fotocélula validada (meta)"),
                         (False, "Hardware atual (sem fotocélula)")):
        texto, bot = roteiro(foto)
        print("## %s\n\n%s\n" % (titulo, texto))
        print(audit.relatorio(bot.log.eventos).replace("# ", "### ", 1))
        print()
