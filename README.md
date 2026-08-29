# Casa Botânica do Futuro

Site oficial gerado como HTML estático, com conteúdo administrável pelo Pages CMS e publicação automática via GitHub Pages.

## COMO EDITAR MEU SITE

### Entrar no painel
1. Acesse `https://app.pagescms.org`.
2. Entre com a conta GitHub que administra este repositório.
3. Na primeira vez, autorize o Pages CMS para o repositório `casa-botanica-os`.
4. Abra `Markosat-ponto/casa-botanica-os` e a branch `main`.

### Trocar uma foto
1. Abra a área de mídia/fotos.
2. Envie a fotografia real.
3. Abra a hospedagem, projeto, tutorial ou produto desejado.
4. Escolha a foto no campo correspondente.
5. Salve. O site é republicado automaticamente.

### Editar o Quarto Oliva
1. Abra **Hospedagens**.
2. Entre em **Quarto Oliva**.
3. Altere textos, fotos, diferenciais ou recursos de tecnologia.
4. Salve.

### Ativar o Quarto Terracota
1. Abra **Hospedagens > Quarto Terracota**.
2. Troque o status de **Em breve** para **Publicado** somente quando o quarto estiver realmente disponível.
3. Adicione fotografias reais.
4. Salve.

### Adicionar um projeto
1. Abra **Projetos**.
2. Clique em **Novo**.
3. Preencha título, categoria, resumo, fotos, materiais, processo e resultado.
4. Escolha o status.
5. Salve.

### Adicionar um DIY
1. Abra **DIY / Ateliê Botânico**.
2. Clique em **Novo**.
3. Preencha materiais, ferramentas e passos.
4. Salve.

### Adicionar um produto
1. Abra **Loja / Produtos**.
2. Clique em **Novo**.
3. Informe somente dados reais: nome, fotos, preço se houver, disponibilidade, dimensões e materiais.
4. Use **Em desenvolvimento** ou **Em breve** quando ainda não estiver à venda.
5. Salve.

### Alterar links e informações gerais
1. Abra **Configurações do site**.
2. Preencha Airbnb, WhatsApp, Instagram, TikTok, YouTube, e-mail, URL oficial e imagens principais.
3. Salve.

### Regra de segurança
Nunca publique senhas, tokens, IPs privados, endpoints do Home Assistant, códigos de acesso ou credenciais de hóspedes. A rota `/guia/` permanece pública e sem informações sensíveis até existir autenticação apropriada.

## Publicação
O fluxo técnico é automático: Pages CMS salva no GitHub → GitHub Actions executa `build.py` → testes básicos rodam → GitHub Pages publica a pasta `dist`.

O proprietário não precisa executar terminal, editar HTML/CSS/JavaScript/JSON/YAML ou rodar build manualmente para atualizar conteúdo.
