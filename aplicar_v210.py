"""Execute na raiz do projeto: python aplicar_v210.py"""
from pathlib import Path
import ast
root=Path(__file__).resolve().parent
app=root/'app.py';base=root/'templates'/'base.html'
if not app.exists() or not base.exists():raise SystemExit('Coloque os arquivos na raiz do projeto, junto de app.py e templates/base.html.')
addon="\n# NowUp V210 — banners da página inicial\nimport nowup_home210\nnowup_home210.configure(globals())\napp.include_router(nowup_home210.router)\n"
a=app.read_text();b=base.read_text()
if 'import nowup_home210' not in a:a+=addon
assets='<link rel="stylesheet" href="/static/home210.css?v=210"><script src="/static/home210.js?v=210" defer></script>'
if '/static/home210.js' not in b:
    if '</body>' not in b:raise SystemExit('Não foi encontrada a tag body. Nenhum arquivo foi alterado.')
    b=b.replace('</body>',assets+'</body>')
ast.parse(a)
for path,text in ((app,a),(base,b)):
    backup=path.with_name(path.name+'.antes-v210')
    if not backup.exists():backup.write_bytes(path.read_bytes())
    path.write_text(text)
print('V210 aplicada. Publique os arquivos atualizados no Render. ADM: /admin/banners-inicio')
