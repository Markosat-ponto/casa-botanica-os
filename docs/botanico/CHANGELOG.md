# Changelog — Botânico

## 2026-11-27 — lote instalado no HA (aprovado pelo Theo)

- Helpers: `input_select.botanico_modo_de_execucao_fisica` (inicia e volta
  para `simulado`), `input_boolean.botanico_suspender_acoes_autonomas`,
  `input_boolean.portao_fotocelula_instalada_e_validada_so_o_theo`,
  `input_text.botanico_ultimo_evento`.
- Automação "Botânico — avisar o Theo quando modo/segurança mudar".
- Painel admin novo `botanico-central` (só administradores).
- Painel do hóspede: avatar do chat trocado pelo mascote oficial (imagem via
  jsDelivr fixada no commit). Backup do painel salvo no HA antes.
  Conferido pelo Theo no painel: exibindo corretamente.
- Agente do hóspede: prompt v2 aplicado (identidade do mascote), sem acesso
  a dispositivos. Backup salvo no HA antes.
- Integração Downloader (pasta `/config/pyscript`) e pyscript com
  `allow_all_imports`. Núcleo em `/config/pyscript/modules/botanico/`,
  app em `/config/pyscript/botanico_v2.py`. Rodando em modo SIMULADO;
  teste silencioso por evento aprovado (sem LLM, sem notificação).
- NÃO feito: chat do painel após o check-out (inviável: o check-out troca a
  senha e derruba a sessão do hóspede). Ver pendências.

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
