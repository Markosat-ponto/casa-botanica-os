from pathlib import Path
from html.parser import HTMLParser
import sys
ROOT=Path(__file__).parents[1]
DIST=ROOT/'dist'
errors=[]
class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.hrefs=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=='a' and d.get('href'): self.hrefs.append(d['href'])
for f in DIST.rglob('*.html'):
    text=f.read_text(encoding='utf-8')
    p=Parser(); p.feed(text)
    if '<title>' not in text: errors.append(f'{f}: sem title')
    if f.name!='404.html' and '<h1' not in text: errors.append(f'{f}: sem h1')
    for href in p.hrefs:
        if href.startswith('/') and not href.startswith('//'):
            clean=href.split('#')[0].split('?')[0]
            if clean in ('','/'): target=DIST/'index.html'
            elif clean.endswith('/'): target=DIST/clean.strip('/')/'index.html'
            else: target=DIST/clean.strip('/')
            if not target.exists(): errors.append(f'{f}: link interno quebrado {href}')
if errors:
    print('\n'.join(errors)); sys.exit(1)
print('Verificação concluída: links internos e estrutura HTML básicos OK.')
