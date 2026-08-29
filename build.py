from pathlib import Path
import json, html, re, shutil

ROOT = Path(__file__).parent
DIST = ROOT / 'dist'
CONTENT = ROOT / 'content'
SITE = json.loads((CONTENT/'site.json').read_text(encoding='utf-8'))


def load_collection(name):
    folder = CONTENT/name
    if not folder.exists():
        return []
    items=[]
    for p in sorted(folder.glob('*.json')):
        data=json.loads(p.read_text(encoding='utf-8'))
        data['_source']=p.name
        items.append(data)
    return items

ROOMS=load_collection('hospedagens')
PROJECTS=load_collection('projetos')
DIYS=load_collection('diy')
PRODUCTS=load_collection('produtos')


def esc(value=''):
    return html.escape(str(value or ''), quote=True)

def slug(value):
    value=str(value or '').lower().strip()
    value=re.sub(r'[^a-z0-9áàâãéêíóôõúç-]+','-',value)
    trans=str.maketrans('áàâãéêíóôõúç','aaaaeeiooouc')
    return value.translate(trans).strip('-') or 'item'

def path_for(kind, item):
    return f'/{kind}/{slug(item.get("slug") or item.get("title"))}/'

def status_label(status):
    return {'published':'Publicado','coming_soon':'Em breve','development':'Em desenvolvimento','hidden':'Oculto'}.get(status,status or '')

def visible(items):
    return [x for x in items if x.get('status') not in ('hidden','draft')]

def media(src, alt='', class_name='media'):
    if src:
        return f'<img class="{class_name}" src="{esc(src)}" alt="{esc(alt)}" loading="lazy" decoding="async">'
    return f'<div class="placeholder {class_name}" role="img" aria-label="Foto pendente"><span>FOTO REAL</span><small>Adicionar pelo painel</small></div>'

def nav():
    links=[('Hospedagem','/hospedagem/'),('Casa Digital','/tecnologia/'),('Projetos','/projetos/'),('DIY','/diy/'),('Loja','/loja/'),('Sobre','/sobre/')]
    brand=(media(SITE.get('logo'),'Casa Botânica do Futuro','brand-logo') if SITE.get('logo') else '<span class="brand-mark">CB</span>')
    return '<header class="site-header"><a class="brand" href="/" aria-label="Casa Botânica do Futuro — início">'+brand+'<span><strong>Casa Botânica</strong><small>do Futuro</small></span></a><button class="menu-toggle" aria-expanded="false" aria-controls="main-nav">Menu</button><nav id="main-nav" class="main-nav" aria-label="Navegação principal">'+''.join(f'<a href="{u}">{t}</a>' for t,u in links)+'<a class="nav-cta" href="/contato/">Contato</a></nav></header>'

def footer():
    social=''.join(f'<a href="{esc(v)}" rel="me noopener" target="_blank">{esc(k.title())}</a>' for k,v in SITE.get('social',{}).items() if v)
    return f'<footer class="site-footer"><div><strong>Casa Botânica do Futuro</strong><p>{esc(SITE.get("signature","Criando o futuro, naturalmente."))}</p></div><div class="footer-links"><a href="/guia/">Guia do hóspede</a><a href="/contato/">Contato</a>{social}</div><small>© Casa Botânica do Futuro · {esc(SITE.get("location_general","Goiânia, Goiás"))}</small></footer>'

def seo(title, description, path='/', image=''):
    base=(SITE.get('site_url') or '').rstrip('/')
    url=f'{base}{path}' if base else path
    image_url=(f'{base}{image}' if image and image.startswith('/') and base else image)
    return f'<title>{esc(title)}</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{esc(url)}"><meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(url)}">{f"<meta property=\"og:image\" content=\"{esc(image_url)}\">" if image_url else ""}<meta name="twitter:card" content="summary_large_image">'

def page(title, description, body, path='/', image='', schema=None):
    schema_tag=f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>' if schema else ''
    return f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#364536">{seo(title,description,path,image)}<link rel="stylesheet" href="/css/style.css">{schema_tag}</head><body>{nav()}<main>{body}</main>{footer()}<script src="/js/script.js" defer></script></body></html>'

def section_head(kicker,title,text=''):
    return f'<div class="section-head"><span>{esc(kicker)}</span><h2>{esc(title)}</h2>{f"<p>{esc(text)}</p>" if text else ""}</div>'

def card(item,kind):
    title=item.get('title','Sem título'); summary=item.get('summary') or item.get('description',''); path=path_for(kind,item)
    return f'<article class="card">{media(item.get("cover"),title,"card-image")}<div class="card-body"><div class="eyebrow">{esc(status_label(item.get("status")))}</div><h3><a href="{path}">{esc(title)}</a></h3><p>{esc(summary)}</p><a class="text-link" href="{path}">Ver detalhes <span aria-hidden="true">→</span></a></div></article>'

def render_home():
    olive=next((x for x in ROOMS if slug(x.get('slug') or x.get('title'))=='quarto-oliva'), ROOMS[0] if ROOMS else None)
    projects=visible(PROJECTS)[:3]
    body=f'<section class="hero"><div class="hero-content"><span class="kicker">Natureza · Design · Tecnologia · Criação · Hospitalidade</span><h1>Casa Botânica <em>do Futuro.</em></h1><p>{esc(SITE.get("home_intro","Uma casa viva em Goiânia, transformada todos os dias por curiosidade, plantas, tecnologia e criação com as próprias mãos."))}</p><div class="actions"><a class="button" href="/hospedagem/">Conheça a hospedagem</a><a class="button button-ghost" href="/sobre/">Descubra a história</a></div></div><div class="hero-visual">{media(SITE.get("hero_image"),"Casa Botânica do Futuro","hero-image")}<div class="hero-note"><strong>Criando o futuro, naturalmente.</strong><span>Uma casa em constante transformação.</span></div></div></section>'
    if olive:
        body+=f'<section class="split feature">{media(olive.get("cover"),olive.get("title"),"feature-image")}<div>{section_head("Hospedagem",olive.get("title","Quarto Oliva"),olive.get("summary",""))}<ul class="feature-list">{"".join(f"<li>{esc(x)}</li>" for x in olive.get("highlights",[])[:5])}</ul><a class="button" href="{path_for("hospedagem",olive)}">Conhecer o quarto</a></div></section>'
    body+=f'<section class="pillars"><div>{section_head("O universo","Uma casa onde as ideias viram espaço.","A tecnologia facilita. As plantas fazem parte. O design tem intenção. E muita coisa nasce do reaproveitamento e da vontade de descobrir como fazer.")}</div><div class="pillar-grid"><a href="/tecnologia/"><span>01</span><h3>Casa Digital</h3><p>Automação residencial e Home Assistant como parte real da experiência.</p></a><a href="/projetos/"><span>02</span><h3>Projetos</h3><p>Transformações, móveis, jardins, iluminação e experimentação.</p></a><a href="/diy/"><span>03</span><h3>Ateliê Botânico</h3><p>Tutoriais e processos para construir, reaproveitar e aprender fazendo.</p></a></div></section>'
    body+=f'<section class="editorial-band"><div><span class="kicker">Nenhuma casa se transforma sozinha.</span><h2>Por trás de cada mudança, existe alguém curioso o bastante para tentar.</h2><p>A Casa Botânica é consequência das ideias, testes, acertos, improvisos e descobertas de Theodoro — alguém que aprende enquanto faz e transforma a própria casa nesse processo.</p><a class="text-link light" href="/sobre/">Conheça quem está por trás →</a></div>{media(SITE.get("theodoro_image"),"Theodoro trabalhando em um projeto da Casa Botânica","editorial-image")}</section>'
    if projects:
        body+=f'<section class="section">{section_head("Projetos recentes","A casa continua mudando.","Cada intervenção vira parte da história e pode alimentar a próxima ideia.")}<div class="card-grid">{"".join(card(x,"projetos") for x in projects)}</div><a class="button button-ghost dark" href="/projetos/">Ver todos os projetos</a></section>'
    body+='<section class="cta-band"><span>Casa Botânica do Futuro</span><h2>Hospedagem, criação e tecnologia no mesmo endereço criativo.</h2><div class="actions"><a class="button light-button" href="/hospedagem/">Explorar hospedagem</a><a class="text-link light" href="/contato/">Falar com a Casa Botânica →</a></div></section>'
    return page('Casa Botânica do Futuro — Natureza, design e tecnologia',SITE.get('seo_description','Casa Botânica do Futuro em Goiânia.'),body,'/',SITE.get('hero_image',''))

def collection_page(kind,title,intro,items):
    vis=visible(items)
    body=f'<section class="page-hero"><div class="section-head"><span>{esc(kind.upper())}</span><h1>{esc(title)}</h1><p>{esc(intro)}</p></div></section><section class="section"><div class="card-grid">'
    body += ''.join(card(x,kind) for x in vis) if vis else '<div class="empty-state"><h3>Conteúdo em preparação</h3><p>Novos itens poderão ser publicados pelo painel administrativo.</p></div>'
    body+='</div></section>'
    return page(f'{title} — Casa Botânica do Futuro',intro,body,f'/{kind}/')

def room_page(item):
    path=path_for('hospedagem',item); title=item.get('title','Hospedagem'); desc=item.get('summary',''); reserve=SITE.get('links',{}).get('airbnb','') if item.get('status')=='published' else ''
    body=f'<section class="detail-hero"><div><span class="status">{esc(status_label(item.get("status")))}</span><h1>{esc(title)}</h1><p>{esc(desc)}</p><div class="actions">{f"<a class=\"button\" href=\"{esc(reserve)}\" target=\"_blank\" rel=\"noopener\">Ver reserva</a>" if reserve else "<span class=\"availability-note\">Disponibilidade configurável pelo painel.</span>"}</div></div>{media(item.get("cover"),title,"detail-cover")}</section><section class="section prose"><h2>{esc(item.get("concept_title","A experiência"))}</h2><p>{esc(item.get("description",""))}</p></section>'
    if item.get('highlights'):
        body+=f'<section class="section"><div class="fact-grid">{"".join(f"<div><span>•</span><p>{esc(x)}</p></div>" for x in item["highlights"])}</div></section>'
    if item.get('gallery'):
        body+=f'<section class="section">{section_head("Galeria","Veja o ambiente")}<div class="gallery">{"".join(media(x,title,"gallery-image") for x in item["gallery"])}</div></section>'
    body+=f'<section class="section split text-split"><div>{section_head("Tecnologia","Conforto conectado","A tecnologia aparece para facilitar a experiência, nunca para complicá-la.")}</div><ul class="feature-list">{"".join(f"<li>{esc(x)}</li>" for x in item.get("technology",[]))}</ul></section>'
    schema={'@context':'https://schema.org','@type':'LodgingBusiness','name':title,'description':desc,'address':{'@type':'PostalAddress','addressLocality':'Goiânia','addressRegion':'GO','addressCountry':'BR'}}
    return page(f'{title} — Casa Botânica do Futuro',desc,body,path,item.get('cover',''),schema)

def project_page(item):
    path=path_for('projetos',item); title=item.get('title','Projeto'); desc=item.get('summary',''); sections=[]
    for heading,key in [('O ponto de partida','problem'),('A ideia','idea'),('Processo','process'),('Resultado','result')]:
        val=item.get(key)
        if not val: continue
        if isinstance(val,list): sections.append(f'<section><h2>{heading}</h2><ol>{"".join(f"<li>{esc(x)}</li>" for x in val)}</ol></section>')
        else: sections.append(f'<section><h2>{heading}</h2><p>{esc(val)}</p></section>')
    body=f'<section class="detail-hero"><div><span class="status">{esc(status_label(item.get("status")))}</span><h1>{esc(title)}</h1><p>{esc(desc)}</p></div>{media(item.get("cover"),title,"detail-cover")}</section><section class="section"><div class="article-layout"><article class="article">{"".join(sections)}'
    if item.get('materials'): body+=f'<section><h2>Materiais</h2><ul>{"".join(f"<li>{esc(x)}</li>" for x in item["materials"])}</ul></section>'
    if item.get('tools'): body+=f'<section><h2>Ferramentas</h2><ul>{"".join(f"<li>{esc(x)}</li>" for x in item["tools"])}</ul></section>'
    body+='</article></div></section>'
    return page(f'{title} — Projetos | Casa Botânica do Futuro',desc,body,path,item.get('cover',''))

def diy_page(item):
    path=path_for('diy',item); title=item.get('title','Tutorial'); desc=item.get('summary','')
    steps=''.join(f'<li><strong>{esc(step.get("title",f"Passo {i+1}"))}</strong><p>{esc(step.get("text",""))}</p></li>' for i,step in enumerate(item.get('steps',[])))
    body=f'<section class="detail-hero"><div><span class="status">{esc(status_label(item.get("status")))}</span><h1>{esc(title)}</h1><p>{esc(desc)}</p></div>{media(item.get("cover"),title,"detail-cover")}</section><section class="section"><div class="article-layout"><article class="article"><section><h2>Materiais</h2><ul>{"".join(f"<li>{esc(x)}</li>" for x in item.get("materials",[]))}</ul></section><section><h2>Ferramentas</h2><ul>{"".join(f"<li>{esc(x)}</li>" for x in item.get("tools",[]))}</ul></section><section><h2>Passo a passo</h2><ol class="steps">{steps}</ol></section></article></div></section>'
    return page(f'{title} — DIY | Casa Botânica do Futuro',desc,body,path,item.get('cover',''))

def product_page(item):
    path=path_for('loja',item); title=item.get('title','Produto'); desc=item.get('summary',''); contact=SITE.get('links',{}).get('whatsapp','') or SITE.get('contact_email','')
    cta=''
    if contact:
        href=contact if str(contact).startswith('http') else 'mailto:'+str(contact)
        cta=f'<a class="button" href="{esc(href)}">Tenho interesse</a>'
    body=f'<section class="detail-hero"><div><span class="status">{esc(status_label(item.get("status")))}</span><h1>{esc(title)}</h1><p>{esc(desc)}</p>{f"<p class=\"price\">{esc(item.get('price'))}</p>" if item.get("price") else ""}{cta}</div>{media(item.get("cover"),title,"detail-cover")}</section><section class="section prose"><h2>Detalhes</h2><p>{esc(item.get("description",""))}</p></section>'
    return page(f'{title} — Loja | Casa Botânica do Futuro',desc,body,path,item.get('cover',''))

def simple_pages():
    tech='<section class="page-hero"><div class="section-head"><span>CASA DIGITAL</span><h1>Tecnologia que trabalha nos bastidores.</h1><p>Automação residencial e Home Assistant fazem parte da experiência da Casa Botânica para simplificar iluminação, acesso, entretenimento, conforto e rotinas.</p></div></section><section class="section"><div class="pillar-grid"><div><span>01</span><h3>Casa conectada</h3><p>Integrações pensadas para reduzir atrito e deixar controles mais simples.</p></div><div><span>02</span><h3>Experiência do hóspede</h3><p>Painéis e automações podem apoiar acesso, iluminação e informações da estadia.</p></div><div><span>03</span><h3>Segurança por projeto</h3><p>Credenciais, endereços internos, tokens e sistemas administrativos nunca são publicados.</p></div></div></section>'
    about=f'<section class="page-hero"><div class="section-head"><span>SOBRE</span><h1>Uma casa em constante transformação.</h1><p>Mas nenhuma casa se transforma sozinha.</p></div></section><section class="editorial-band about-band"><div><span class="kicker">Theodoro → curiosidade → ideias → experimentação</span><h2>Primeiro vem a vontade de descobrir como fazer.</h2><p>Theodoro gosta de plantas, criação, tecnologia, automação, decoração, projetos manuais, reaproveitamento e de receber pessoas. Aprender enquanto faz é parte do processo.</p></div>{media(SITE.get("theodoro_image"),"Theodoro criando na Casa Botânica","editorial-image")}</section><section class="section prose"><h2>A Casa Botânica é a expressão física dessa curiosidade.</h2><p>Uma ideia vira teste. O teste muda um ambiente. O ambiente muda a experiência. Essa experiência produz novas ideias — e a casa muda de novo.</p></section>'
    links=SITE.get('links',{}); socials=SITE.get('social',{}); available=[('Hospedagem',links.get('airbnb')),('WhatsApp',links.get('whatsapp')),('Instagram',socials.get('instagram')),('TikTok',socials.get('tiktok')),('YouTube',socials.get('youtube'))]
    contact='<section class="page-hero"><div class="section-head"><span>CONTATO</span><h1>Fale com a Casa Botânica.</h1><p>Hospedagem, dúvidas, conteúdo, projetos e parcerias.</p></div></section><section class="section contact-grid">'+''.join(f'<a class="contact-card" href="{esc(u)}" target="_blank" rel="noopener"><strong>{esc(t)}</strong><span>Abrir canal →</span></a>' for t,u in available if u)+'</section>'
    if not any(u for _,u in available): contact+='<section class="section"><div class="empty-state"><h3>Canais ainda não configurados</h3><p>Adicione os links oficiais no painel administrativo.</p></div></section>'
    guide='<section class="page-hero"><div class="section-head"><span>GUIA DIGITAL</span><h1>Guia da Casa Botânica.</h1><p>Esta rota está preparada para receber informações do hóspede, mas dados sensíveis não ficam expostos na versão pública.</p></div></section><section class="section"><div class="safe-demo"><span>ÁREA PREPARADA</span><h2>Conteúdo exclusivo precisa de proteção.</h2><p>Wi-Fi, instruções privadas de acesso, códigos, credenciais e informações específicas de reservas devem entrar somente quando houver autenticação apropriada.</p></div></section>'
    return {'tecnologia/index.html':page('Casa Digital — Casa Botânica do Futuro','Automação residencial, Home Assistant e tecnologia aplicada à experiência da Casa Botânica.',tech,'/tecnologia/'),'sobre/index.html':page('Sobre — Casa Botânica do Futuro','A história de Theodoro e da transformação contínua da Casa Botânica do Futuro.',about,'/sobre/',SITE.get('theodoro_image','')),'contato/index.html':page('Contato — Casa Botânica do Futuro','Canais oficiais de contato da Casa Botânica do Futuro.',contact,'/contato/'),'guia/index.html':page('Guia Digital — Casa Botânica do Futuro','Área preparada para o guia digital do hóspede com arquitetura segura.',guide,'/guia/')}

def write(rel,text):
    target=DIST/rel; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(text,encoding='utf-8')

if DIST.exists(): shutil.rmtree(DIST)
DIST.mkdir()
write('index.html',render_home())
write('hospedagem/index.html',collection_page('hospedagem','Hospede-se dentro da experiência.','Ambientes autorais onde plantas, conforto e tecnologia fazem parte da estadia.',ROOMS))
write('projetos/index.html',collection_page('projetos','Projetos que transformam a casa.','Ambientes, jardins, marcenaria, iluminação, automação, decoração e reaproveitamento.',PROJECTS))
write('diy/index.html',collection_page('diy','Aprender fazendo.','Tutoriais do Ateliê Botânico: materiais, ferramentas, processos e descobertas.',DIYS))
write('loja/index.html',collection_page('loja','Peças autorais e experimentos.','Estrutura preparada para produtos da Casa Botânica, do desenvolvimento ao lançamento.',PRODUCTS))
for item in visible(ROOMS): write(path_for('hospedagem',item).lstrip('/')+'index.html',room_page(item))
for item in visible(PROJECTS): write(path_for('projetos',item).lstrip('/')+'index.html',project_page(item))
for item in visible(DIYS): write(path_for('diy',item).lstrip('/')+'index.html',diy_page(item))
for item in visible(PRODUCTS): write(path_for('loja',item).lstrip('/')+'index.html',product_page(item))
for rel,text in simple_pages().items(): write(rel,text)
write('404.html',page('Página não encontrada — Casa Botânica do Futuro','Página não encontrada.','<section class="page-hero"><div class="section-head"><span>404</span><h1>Essa página ainda não floresceu.</h1><p>Volte para a Casa Botânica e continue explorando.</p><a class="button" href="/">Ir para o início</a></div></section>','/404.html'))
for folder in ('css','js','media'):
    src=ROOT/folder
    if src.exists(): shutil.copytree(src,DIST/folder,dirs_exist_ok=True)
base=(SITE.get('site_url') or '').rstrip('/')
urls=['/','/hospedagem/','/tecnologia/','/projetos/','/diy/','/loja/','/sobre/','/contato/','/guia/']
urls += [path_for('hospedagem',x) for x in visible(ROOMS)] + [path_for('projetos',x) for x in visible(PROJECTS)] + [path_for('diy',x) for x in visible(DIYS)] + [path_for('loja',x) for x in visible(PRODUCTS)]
write('sitemap.xml','<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{esc(base+u if base else u)}</loc></url>' for u in urls)+'</urlset>')
write('robots.txt',f'User-agent: *\nAllow: /\nSitemap: {(base+"/sitemap.xml") if base else "/sitemap.xml"}\n')
print(f'Build concluído: {len(list(DIST.rglob("*.html")))} páginas HTML.')
