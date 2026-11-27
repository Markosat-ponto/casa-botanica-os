# Instalação, liberação gradual e recuperação

## Etapas de liberação (cada uma exige "ok" do Theo)

**Etapa A — sombra (sem risco físico).**
1. Backup: `ha_manage_backup(scope="edits", action="create")` de cada item
   alterado, além do backup automático diário do HA.
2. Criar os helpers do `ha/pacote_botanico.yaml` (modo inicia `simulado`).
3. Criar a automação de alerta de mudança de segurança.
4. Copiar `botanico/__init__.py` e `botanico/core/` para
   `/config/pyscript/modules/botanico/`; `botanico_app.py` para
   `/config/pyscript/apps/`; criar `/config/botanico/`.
5. Configurar pyscript `allow_all_imports: true`; trocar `_SAL` por um valor
   do `secrets.yaml`.
6. Teste silencioso: disparar evento `botanico_mensagem` pelas Ferramentas
   de desenvolvedor e ver resposta no evento `botanico_resposta` e o aviso
   "MODO SIMULADO" no celular do Theo. Nenhum portão se move.
7. Rodar 1–2 semanas em sombra lendo a auditoria.

**Etapa B — canal do painel com modo suporte.** Alterar o encerramento de
acesso para manter o chat do painel ativo após o check-out (controles
desligados). Mudança de comportamento para o hóspede: precisa de aprovação.

**Etapa C — medir o portão (presencial, com o Theo).** Cronometrar curso
completo e tempo de resposta do sensor; ajustar `config.PORTAO`.

**Etapa D — abertura autônoma.** Com o Theo presente e os cachorros
protegidos: 3 aberturas pelo protocolo em modo `autonomo`. Fechamento
continua bloqueado.

**Etapa E — fechamento autônomo.** Só após instalar fotocélula na central do
motor, testar reversão com obstáculo (caixa de papelão) e o Theo ligar
`input_boolean.portao_fotocelula_instalada_e_validada_so_o_theo`.

## Recuperação

| Situação | O que fazer |
|---|---|
| Comportamento estranho | ligar **SUSPENDER ações autônomas** no painel Botânico |
| Voltar tudo | desativar `botanico_app.py` (renomear para `.bak`) e recarregar pyscript; restaurar backups de edição |
| HA reiniciou | modo volta para `simulado` automaticamente; conversas em andamento se perdem (auditoria fica) |
| Sem internet | Botânico continua conversando no painel (rede local), mas não comanda portão (integração em nuvem); hóspede usa controle/chave; Theo é avisado quando a internet volta |
| Sensor do portão oscilando | protocolo bloqueia sozinho; verificar alinhamento do ímã |

## Como foi instalado / como atualizar (sem acesso a arquivos)

O HA baixa os arquivos do repositório público pela integração Downloader
(pasta base `/config/pyscript`), sempre com URL fixada em um commit:

```
downloader.download_file
  url: https://raw.githubusercontent.com/Markosat-ponto/casa-botanica-os/<SHA>/botanico/core/<arquivo>.py
  subdir: modules/botanico/core      (app: sem subdir, filename botanico_v2.py)
  overwrite: true
```

Depois: `pyscript.reload` e conferir o log (`Failed to load` = não carregou,
nada mais é afetado). Teste silencioso: evento `botanico_mensagem` com
`canal: teste`.

## Atualizar o núcleo

1. Alterar código no repositório e rodar os testes.
2. Copiar `botanico/core/` para o HA e recarregar o pyscript.
3. Registrar no `CHANGELOG.md`.
