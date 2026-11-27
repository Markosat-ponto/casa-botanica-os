# Changelog — Botânico

## 2026-11-27 — mascote e agente do hóspede v2 (preparado)

- Mascote oficial em `botanico/assets/mascote/` (avatar redondo, quadrado,
  corpo inteiro transparente); artefato de brilho removido.
- Identidade/personalidade em `botanico/knowledge/persona.md`.
- Novo prompt do agente do hóspede em `botanico/ha/prompt_hospede_v2.md`
  (não aplicado; dados privados entram só no HA).

## 2026-11-27 — alterações no HA autorizadas pelo Theo

- Agente de conversa do hóspede: removido o acesso a dispositivos (Assist).
  Prompt e modelo intactos. Backup de edição salvo no HA antes da mudança.
  O agente atual será substituído pela versão nova (Botânico v2 + mascote).
- Novo: contador `counter.botanico_hospede_mensagens_recebidas_no_painel` e
  automação "Botânico Hóspede — registrar uso do chat do painel" (só
  registra pergunta e resposta no Diário de bordo; não controla nada).

## 2026-11-27 — v0.1 (simulação)

- Diagnóstico da infraestrutura (somente leitura no HA; nada alterado).
- Núcleo determinístico: política, intertravamentos do portão, identidade
  com janela de suporte de saída, classificador local, auditoria com
  redação de segredos, protocolo de saída assistida com verificação.
- Simulador do hardware real e 28 cenários da Fase 7 (todos aprovados).
- Adaptador pyscript e pacote HA escritos — **não instalados**.
- Documentação em `docs/botanico/`.
- Nenhuma alteração em produção (HA ou site).
