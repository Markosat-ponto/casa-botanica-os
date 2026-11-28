# Changelog — Botânico

## 2026-11-27 — integração com o portal do hóspede (botanico-ui)

- O portal novo (pyscript no HA, login próprio do hóspede) passa a ser a
  fonte de acessos; o painel antigo do HA não é mais usado.
- O Theo desativou o usuário antigo do hóspede no HA (Configurações →
  Pessoas → Usuários; reversível pelo mesmo botão "Ativo").
- Botânico v2: canal `portal` (sessão logada = verificado), escuta o evento
  `botanico_acesso_hospede` (gerado/encerrado/expirado, sem segredos) e
  valida códigos de acesso perguntando ao serviço
  `pyscript.oliva_validar_codigo` (resposta só válido/inválido). Sem o
  serviço, todo código é inválido. 38 testes aprovados.
- Lado do portal (evento, serviço, modo ajuda após encerrar, envio seguro
  de credenciais): tarefa 036 do canal, com o Codex.
- Reload do Botânico passa a ser só do arquivo dele
  (`pyscript.reload` com `global_ctx: file.botanico_v2`), para não
  recarregar o portal do hóspede junto.

## 2026-11-27 — identidade: telefone não prova quem é o hóspede

- O telefone cadastrado numa reserva pode ser de outra pessoa.
- Pedidos sensíveis fora do painel (saída/portão, horário de saída,
  extensão) agora exigem o código da reserva do Airbnb ou o código de
  acesso. Perguntas gerais não exigem.
- Número fora do cadastro que envia um código de reserva válido passa a ser
  reconhecido naquela estadia; sem código, não recebe resposta.
- Cadastro da reserva vem do calendário (datas + código em hash).
- Códigos de reserva mascarados nos registros. 35 testes aprovados.

## 2026-11-27 — canais: painel em modo suporte + WhatsApp (aprovado pelo Theo)

- `input_boolean.hospede_modo_suporte_pos_check_out` (novo).
- `script.hospede_encerrar_acesso`: deixou de trocar a senha e derrubar
  sessões; agora liga o modo suporte. Backup de edição no HA.
- `script.hospede_encerrar_suporte` (novo): desliga modo suporte, troca senha
  do visitante, derruba sessões. Automação "Hóspede — encerrar modo suporte
  (18h ou 5 h após o check-out)"; acesso de novo hóspede só desliga o modo.
- Painel do hóspede: no modo suporte aparecem só o aviso "Precisa de ajuda?"
  e o chat. Mensagens do chat no modo suporte vão para o Botânico v2
  (automação do painel alterada; backup no HA).
- WhatsApp: automação "Botânico v2 — WhatsApp de hóspede para o Botânico".
  Responde em texto, do número do Theo, só para o telefone da reserva
  atual/janela de saída. Ignora o Theo, grupos, mídia e eco das próprias
  respostas. Teste com número fictício: ignorado (sem envio).
- BOTÂNICO — Central: modo suporte e botão "Encerrar suporte agora".

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
