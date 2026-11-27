# Protocolos e permissões

## Níveis de autonomia (`botanico/core/policy.py`)

| Nível | Ações | Quem libera |
|---|---|---|
| 1 — livre | responder, consultar reserva, orientar, diagnosticar, controlar dispositivos do quarto (lista fechada), recuperar acesso, protocolo de saída, registrar, informar valores, emergência | o próprio Botânico |
| 2 — regra | acesso temporário, alterar horário de saída, extensão, reiniciar equipamento não crítico, acesso excepcional | regra pré-aprovada em `config.REGRAS_NIVEL_2` |
| 3 — Theo | cancelar, desconto, reembolso, preço, pagamento, regras, segurança, excluir registro, acesso admin, desativar proteção | só canal autenticado do Theo |

- **Suspensão imediata** (`input_boolean.botanico_suspender_acoes_autonomas`): para
  ações físicas e de nível 2. Respostas, orientação, registro e emergência
  continuam. Estado desconhecido do helper = tratado como suspenso.
- **Emergência:** responde na hora com SAMU 192, Bombeiros 193, Polícia 190 e
  avisa o Theo com prioridade, independente de suspensão ou IA.
- **Mensagens maliciosas:** o texto do hóspede só *pede* ações do catálogo.
  Alegar ser o Theo, pedir para "ignorar regras" etc. não muda nada e gera
  registro de segurança.
- **Regra de late checkout (nível 2, valor inicial — Theo ajusta):** até 13h,
  se o quarto não tiver check-in no mesmo dia. Fora disso, vai para o Theo.
- **Extensão:** só informa disponibilidade e diária cadastrada (nunca R$ 0);
  reserva e pagamento acontecem na plataforma.

## Fatos de hardware que definem o protocolo

- Módulo de pulso: abrir e fechar mandam o mesmo pulso; **a direção é decidida
  pela central do motor** (abre → para → fecha → para).
- Um único sensor magnético na posição **fechada**: `closed` ou "não fechado".
- Integração em nuvem: sem internet, sem comando nem leitura.

Consequência: direção só é previsível a partir de estado conhecido e parado.

| Leitura do sensor | Interpretação | Pulso permitido |
|---|---|---|
| `closed` estável ≥ 5 s | fechado | abrir |
| `open` estável ≥ curso + 5 s | aberto e parado | fechar (se fotocélula validada) |
| `open` recente | pode estar em movimento | **nenhum** |
| oscilando (> 4 trocas/min) | contraditório | **nenhum** |
| `unavailable`/`unknown` | sem leitura | **nenhum** |

## Intertravamentos (`botanico/core/gate.py`)

**Abrir:** sensor disponível, fechado e estável · animais confirmados no
cercado · não suspenso · limite de comandos (3 por atendimento, 6 por hora)
· modo autônomo aprovado.
Sem resposta do sensor em 15 s: **uma** repetição, só se continuar fechado e
estável; depois escala.

**Fechar:** fotocélula instalada **e validada** · hóspede confirmou que o
veículo saiu · câmera não indica obstáculo (câmera só bloqueia) · portão
aberto e parado · não suspenso · limite de comandos.
Sem confirmação de fechado em 45 s: **nunca repete** (pulso poderia reabrir
ou parar sobre algo) e escala com prioridade.

## Protocolo de saída assistida (caso real)

1. Recebe a mensagem e identifica a reserva (painel = quarto; WhatsApp =
   telefone; site = código). Desconhecido → pede código (3 tentativas).
2. Confere se está na **janela de saída**: do check-in até 6 h após o fim da
   credencial (mínimo até 18h do dia). A saída não depende da credencial.
3. Se a credencial expirou, explica o motivo com o horário.
4. Pede confirmação de que os cachorros estão no cercado.
5. Lê o sensor e aplica o intertravamento de abertura.
6. Envia um pulso e verifica a abertura pelo sensor.
7. Orienta a retirada e pede confirmação de saída completa do veículo.
8. Se o portão ainda está terminando o curso, espera parar.
9. Análise de câmera sob demanda (complementar).
10. Intertravamento de fechamento → pulso → verifica `closed` estável.
11. Informa a conclusão, registra e avisa o Theo (sem urgência).

Saídas de falha: sempre informa o hóspede com honestidade, nunca afirma o que
não verificou, e avisa o Theo com prioridade quando o portão pode ter
ficado aberto. Sem confirmação do veículo em 15 min: alerta.

**Hoje (sem fotocélula):** o Botânico pode abrir, mas **não fecha sozinho**;
avisa o Theo com prioridade que o portão ficou aberto.

## Modos de execução física

| Modo | Comportamento |
|---|---|
| `simulado` (padrão, e após qualquer reinício) | decide tudo, **não comanda**; avisa o Theo "abriria agora, libere manualmente" — permite auditar as decisões antes de liberar |
| `autonomo` | comanda de verdade — só após Fase 7 validada na casa e aprovação do Theo |

Qualquer mudança de modo, suspensão ou fotocélula gera aviso imediato ao Theo.
