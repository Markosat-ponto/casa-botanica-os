# Decisões, limitações e pendências

## Decisões técnicas

1. **Rodar dentro do HA via pyscript**, sem servidor novo (custo zero, 24 h).
2. **IA não executa:** comandos só por intertravamento determinístico.
3. **Sensor manda, não "último comando":** o protocolo decide pela leitura do
   sensor; o script de alternância por último comando não é usado.
4. **Fechamento autônomo bloqueado sem fotocélula validada.**
5. **Câmera só bloqueia.** Imagem só sob demanda, nunca fluxo contínuo.
6. **Saída ≠ credencial:** janela de suporte de saída após a expiração.
7. **Começa em modo sombra** e volta para ele após cada reinício.
8. **Repositório público:** diagnóstico de segurança fica fora dele.

## Limitações conhecidas

- Sessões de conversa ficam em memória (reinício zera conversas em curso).
- Há limitações de permissão do lado do HA que afetam o painel do hóspede;
  detalhes e mitigação no relatório privado (fora do repositório).
- Integração do portão depende de internet (nuvem). Alternativa sem custo a
  avaliar: controle local do módulo Tuya.
- Sensor só na posição fechada: não distingue "totalmente aberto" de
  "parado no meio" — por isso a espera de curso completo antes de fechar.
- Classificador local é por palavras-chave; frases muito diferentes caem em
  "pergunta livre" (seguro, mas menos útil). Evolução: classificação por LLM
  com saída validada.

## Equipamentos necessários

| Item | Para quê | Bloqueia |
|---|---|---|
| **Fotocélula** (par emissor/receptor ligado à central do motor) | reversão automática com obstáculo | fechamento autônomo |
| **Botão físico de saída** na garagem, ligado direto à central do motor | saída sem internet, sem IA, sem anfitrião | nada (mas é a garantia final de saída) |
| (opcional) Segundo sensor magnético na posição aberta | saber "totalmente aberto" | nada |

Antes de comprar: verificar se a central do motor já tem entrada de
fotocélula (a maioria tem) e se já existe uma instalada e não ligada.

## Depende do Theo

- [x] Etapa A instalada em modo simulado (27/11/2026).
- [x] Correção do agente de conversa do hóspede (aplicada em 27/11/2026).
- [ ] Novo agente do hóspede (Botânico v2) com identidade do mascote.
- [x] Canal pós check-out: painel em modo suporte até 18h + WhatsApp
      (27/11/2026).
- [ ] Airbnb: sem API de mensagens. Hoje o Botânico só lê o e-mail de aviso
      e repassa ao Theo. Decidir: mensagem programada no Airbnb indicando o
      WhatsApp/painel do Botânico (o Theo configura no app) e/ou o Botânico
      puxar a conversa para o WhatsApp quando o hóspede escrever no Airbnb.
- [ ] Verificar (passivo) se mensagens que o Theo envia a terceiros entram
      na automação de comandos do WhatsApp (opção "self messages" ligada).
- [ ] Telefone do hóspede precisa estar em `input_text.hospede_telefone_whatsapp`
      enquanto o acesso estiver ativo, para o WhatsApp reconhecê-lo.
- [ ] Cronometrar o portão junto com o agente (Etapa C).
- [ ] Decidir fotocélula e botão físico.
- [ ] Ajustar regra de late checkout (padrão 13h) e diárias no HA (hoje R$ 0).
- [ ] Decidir sobre PMS parceiro do Airbnb (custo) ou ficar com mensagens
      programadas + canal próprio.
- [ ] Confirmar se a integração de WhatsApp é a API oficial.

## Próximas fases (para o próximo agente)

1. Etapa A no HA (após aprovação).
2. Integrar a caixa de mensagem do painel ao evento `botanico_mensagem`.
3. Classificador LLM com saída validada (`intents.validar_saida_llm`).
4. Chat do site (webhook Nabu Casa + polling, com limite de abuso).
5. Relatório matinal automático (`audit.relatorio`) no celular do Theo.
