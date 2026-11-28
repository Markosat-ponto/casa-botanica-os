# Projeto Botânico — Mordomo digital da Casa Botânica

> Ponto de entrada para o Theo e para qualquer agente (Claude, Codex, ChatGPT)
> que continue o projeto. Leia este arquivo antes de mexer em qualquer coisa.

**Status (28/11/2026):** instalado no HA em **modo simulado** (decide,
registra e avisa o Theo, mas não move o portão). Canais: WhatsApp (só
hóspedes; ações sensíveis exigem código), painel antigo em modo suporte e
portal do hóspede (Oliva/Terracota; chat do portal em construção pelo
Codex, tarefa 036). Operações físicas autônomas: **bloqueadas**.

## Mapa

| Documento | Conteúdo |
|---|---|
| [arquitetura.md](arquitetura.md) | Componentes, onde roda, por quê, canais (site, painel, WhatsApp, Airbnb) |
| [protocolos-e-permissoes.md](protocolos-e-permissoes.md) | Níveis de autonomia, intertravamentos do portão, protocolo de saída |
| [testes.md](testes.md) | Cenários da Fase 7 e resultados |
| [manutencao.md](manutencao.md) | Instalação, liberação gradual, recuperação, rollback |
| [pendencias-e-decisoes.md](pendencias-e-decisoes.md) | Decisões técnicas, limitações, o que depende do Theo, equipamentos |
| [CHANGELOG.md](CHANGELOG.md) | Registro de alterações |

Diagnóstico de segurança detalhado da casa: **fora do repositório** (repo é
público). Fica no Obsidian do Theo — nunca copie para cá.

## Código

```
botanico/
  core/        núcleo determinístico (sem dependências)
    config.py    limites de segurança (só o Theo altera)
    policy.py    matriz de permissões / suspensão imediata
    gate.py      leitura do sensor, intertravamentos, limitador de comandos
    guests.py    identidade do hóspede e janela de suporte de saída
    intents.py   classificador local + validação de saída de LLM
    audit.py     registro com redação de segredos + relatório "enquanto dormia"
    agent.py     orquestrador e protocolo de saída assistida
  sim/         simulador do hardware real + transcrição do caso real
  tests/       28 cenários (Fase 7)
  ha/          adaptador pyscript + pacote HA (NÃO instalados)
  knowledge/   base de conhecimento do hóspede
```

Comandos (a partir da raiz do repositório, Python 3.11+):

```bash
python -m unittest discover -s botanico/tests -t .   # testes
python -m botanico.sim.transcricao                   # conversa simulada
```

## Regras para quem continuar

1. Segurança física é determinística: a IA **interpreta e conversa**; quem
   decide comando físico é `gate.py` + `policy.py`. Não inverta isso.
2. Câmera **só bloqueia**, nunca autoriza.
3. Nunca usar comando de alternância quando a posição é desconhecida.
4. O Botânico não altera as próprias permissões nem `config.py`.
5. Nada de credenciais, endereço, telefones ou detalhes de vulnerabilidade
   neste repositório.
6. Mudanças no HA: em lote, com backup do que já existe, e com aprovação do
   Theo para qualquer coisa física ou de segurança.
