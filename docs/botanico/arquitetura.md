# Arquitetura

## Princípio

```
Canal (painel / site / WhatsApp)
        │  evento botanico_mensagem {canal, remetente, texto}
        ▼
 Identidade ──► Intenção ──► Política ──► Protocolo ──► Intertravamento ──► Comando
 (guests)      (local; LLM     (policy)    (agent)        (gate)            (script HA
                opcional,                                                    já existente)
                saída validada)                                │
                                                               ▼
                                                     Verificação pelo sensor
                                                     (tick a cada 2 s / mudança)
        ▲                                                      │
        └──────── resposta (evento botanico_resposta) ◄────────┘
                  + auditoria (JSONL, segredos mascarados)
```

- **O modelo de IA nunca executa nada.** Ele só (a) responde perguntas livres
  sem acesso a dispositivos e (b) opcionalmente classifica intenção, com
  saída limitada a uma lista fechada.
- **Execução física** passa por intertravamentos determinísticos e pelos
  scripts de portão que já existem no HA (preserva notificações e histórico).
- **Sem IA, o essencial continua:** classificador local, protocolos e
  intertravamentos rodam sem internet nem modelo. Sem LLM, perguntas livres
  viram "registrei e avisei o Theo".

## Onde roda — decisão

| Opção | Custo | 24 h | Sem internet | Decisão |
|---|---|---|---|---|
| **pyscript dentro do HA** (já instalado) | zero | sim (HA já é 24 h) | regras locais seguem | **escolhida** |
| Servidor/VPS próprio | mensal | depende | não alcança a casa | descartada |
| Add-on dedicado | zero | sim | sim | possível evolução se o pyscript limitar |
| Conversa aberta no Claude/ChatGPT | — | não | não | descartada |

Motivos: reaproveita o HA que já roda 24 h com reinício automático, os
helpers, scripts e integrações existentes; zero serviço novo.
O núcleo é Python puro e testável fora do HA (simulador), e é interpretado
pelo pyscript na casa (`/config/pyscript/modules/botanico`), para poder
chamar serviços do HA.

**Persistência:** auditoria em `/config/botanico/auditoria.jsonl`; snapshot
do hóspede (código só em hash) em `/config/botanico/hospede_atual.json`, que
sobrevive ao encerramento de acesso no check-out. Sessões de conversa ficam
em memória (reinício do HA zera conversas em andamento — limitação aceita
na v1).

**Custo de IA:** classificação local é grátis. LLM só para pergunta livre e
para análise de câmera **sob demanda** (uma imagem por fechamento, nunca
fluxo contínuo). Modelo do agente atual: econômico. Contagem de chamadas
fica na auditoria (`tipo: llm`, `tipo: camera`).

## Componentes pedidos × situação

| Componente | Onde | Situação |
|---|---|---|
| Motor de IA | agente de conversa existente no HA, **sem ferramentas** | reaproveitado (ver pendências) |
| Base de conhecimento | `botanico/knowledge/` + prompt do agente | v1 escrita |
| Integração HA | `ha/pyscript/botanico_app.py` | escrita, não instalada |
| Reservas | calendário Airbnb já sincronizado no HA + snapshot | escrita, não instalada |
| Identidade/permissões | `guests.py`, `policy.py` | testado |
| Regras/segurança | `gate.py` | testado |
| Memória de atendimento | `Sessao` em `agent.py` | testado (memória volátil) |
| Visão sob demanda | `analisar_camera()` via ai_task | escrita, não instalada |
| Auditoria | `audit.py` | testado |
| Fila | eventos HA + `mode: queued` | via HA |
| Monitoramento | helper `botanico_status` + painel admin | pacote pronto |
| Falhas/recuperação | limites, escalonamento, modo seguro após restart | testado / pacote |

## Canais

**1. Painel do quarto (prioridade).** Já existe caixa de mensagem no painel.
Integração: a automação atual passa a disparar `botanico_mensagem` com
`canal=painel, remetente=oliva`. Requisito crítico: o painel **não pode
sumir no check-out** — precisa de um "modo suporte" (chat ativo, controles
desligados). Hoje o encerramento de acesso desliga o painel inteiro; é a
causa raiz do caso real.

**2. Site oficial.** O site é estático (GitHub Pages) e não tem servidor.
Chat no site exige uma ponte até o HA. Caminho econômico: webhook do HA via
Nabu Casa para entrada + resposta por polling. Precisa de proteção contra
abuso (limite por IP/sessão, validação por código da reserva). Fase 5.

**3. WhatsApp.** Já existe integração no HA. Verificar se é API oficial
(WhatsApp Business Platform/Cloud API) ou ponte não oficial — ponte não
oficial pode resultar em bloqueio do número. Recomendação: canal de suporte
via WhatsApp só sobre API oficial.

**4. Airbnb.** Não há API pública de mensagens para anfitriões individuais;
acesso via API é restrito a parceiros de software aprovados (PMS/channel
managers). Alternativas compatíveis com as regras: (a) usar um PMS parceiro
oficial (pago — exige decisão do Theo); (b) mensagens programadas do próprio
Airbnb enviando, no check-in, o link do canal de suporte do Botânico (painel/
WhatsApp/site) e as instruções de saída; (c) ler notificações de mensagens
que já chegam ao HA apenas para **alertar** o Theo. Descartado: automação do
site/app do Airbnb ou compartilhamento de login (risco à conta). *Informação
de políticas a reconfirmar antes de contratar qualquer coisa.*

**5. Administração.** Painel Lovelace novo, só para administradores (YAML em
`ha/pacote_botanico.yaml`), com chave de suspensão, modo, status e linha do
tempo; relatório "enquanto eu dormia" gerado por `audit.relatorio()`.
