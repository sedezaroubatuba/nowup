"""Simple fashion catalogues share the existing WhatsApp order flow."""
import json
from fastapi import HTTPException

CATEGORIES=('Novidades','Roupas','Vestidos','Camisetas','Sapatos','Acessórios')
PRICE=3990

def is_fashion(pro):
    return bool(pro) and dict(pro).get('business_type')=='fashion'

def seed(conn,pid,stamp):
    for index,name in enumerate(CATEGORIES):
        conn.execute('INSERT OR IGNORE INTO product_categories(professional_id,name,sort_order,active,created_at) VALUES(?,?,?,?,?)',(pid,name,index,1,stamp))

def config(kind,sizes,colors):
    if kind not in ('none','letters','numbers'):raise HTTPException(400,'Escolha tamanhos por letras, numeração ou tamanho único.')
    def values(raw,label):
        items=[x.strip() for x in raw.replace(';',',').split(',') if x.strip()]
        if len(items)>30 or any(len(x)>40 for x in items) or len({x.casefold() for x in items})!=len(items):
            raise HTTPException(400,'Confira '+label+': até 30 opções diferentes, de até 40 caracteres.')
        return items
    groups=[]
    if kind!='none':
        options=values(sizes,'os tamanhos')
        if not options:raise HTTPException(400,'Informe os tamanhos disponíveis, separados por vírgula.')
        if kind=='letters' and any(not x.isalpha() for x in options):raise HTTPException(400,'Use letras para os tamanhos, como P, M, G, GG e XXG.')
        if kind=='numbers':
            import re
            if any(not re.fullmatch(r'\d{1,3}(?:[.,]\d)?',x) for x in options):raise HTTPException(400,'Use numeração, como 35, 36, 37 e 38.')
        groups.append(dict(id='fashionSize385',name='Tamanho (letras)' if kind=='letters' else 'Numeração',min=1,max=1,options=options))
    options=values(colors,'as cores')
    if options:groups.append(dict(id='fashionColor385',name='Cor',min=1,max=1,options=options))
    return dict(ingredients=[],groups=groups,free_enabled=False,free_count=0,utensils=False,notes=True)

def editor(raw):
    try:c=json.loads(raw or '{}')
    except (ValueError,TypeError):c={}
    groups={g.get('id'):g for g in c.get('groups',[])}
    size=groups.get('fashionSize385',{})
    return dict(kind=('numbers' if size.get('name')=='Numeração' else 'letters') if size else 'none',sizes=', '.join(size.get('options',[])),colors=', '.join(groups.get('fashionColor385',{}).get('options',[])))

def save_photos(g,conn,pid,uploads):
    uploads=[u for u in uploads if getattr(u,'filename',None)]
    if not uploads:return
    if len(uploads)>4:raise HTTPException(400,'Envie até 4 fotos adicionais, além da principal (5 no total).')
    images=[g['save_image'](u) for u in uploads]
    conn.execute('UPDATE products SET fashion_photos385=? WHERE id=?',(json.dumps(images),pid))

def install(g):
    g['templates'].env.globals['fashion_editor385']=editor
    from nowup_fashion_demo385 import install as demo_install
    demo_install(g)
    @g['app'].on_event('startup')
    def setup():
        with g['db']() as c:
            g['ensure_column'](c,'products','fashion_photos385',"TEXT NOT NULL DEFAULT '[]'")
            c.execute("INSERT OR IGNORE INTO categories(name,slug,icon,sort_order,active) VALUES('Moda e acessórios','moda-e-acessorios','👗',80,1)")
        c.close()
        from nowup_fashion_demo385 import initialize
        initialize(g)

