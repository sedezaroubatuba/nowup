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
    from fastapi import Request
    from fastapi.responses import RedirectResponse

    @g['app'].post('/painel/pedidos/{order_id}/pix-combinado')
    def release_agreed_pix(request: Request, order_id: int):
        owner=g['require_user'](request,'professional')
        conn=g['db']()
        try:
            conn.execute('BEGIN IMMEDIATE')
            lock=' FOR UPDATE' if getattr(conn,'dialect','sqlite')=='postgres' else ''
            order=conn.execute('''SELECT o.*,p.business_type,p.pix_key,p.pix_key_type,
                p.pix_receiver_name,p.pix_receiver_city FROM orders o
                JOIN professionals p ON p.id=o.professional_id
                WHERE o.id=? AND p.user_id=?'''+lock,(order_id,owner['id'])).fetchone()
            if not order:raise HTTPException(404,'Pedido não encontrado')
            order=dict(order)
            if order['business_type']!='fashion':raise HTTPException(409,'Esta opção é para pedidos de moda.')
            if order['status'] not in ('confirmed','preparing','ready','out_for_delivery'):
                raise HTTPException(409,'Confirme o pedido e aguarde a aprovação de qualquer alteração antes de liberar o Pix.')
            if order['payment_method'] not in ('on_delivery','pix'):
                raise HTTPException(409,'Este pedido já tem outra forma de pagamento definida.')
            if not g['pix_payment'](order,order['total_cents'],'NU'+str(order_id)):
                raise HTTPException(409,'Complete a chave Pix, o nome do recebedor e a cidade nas configurações de pagamento da loja.')
            if order['payment_method']!='pix':
                conn.execute("UPDATE orders SET payment_method='pix',change_for_cents=0,updated_at=? WHERE id=?",(g['now_iso'](),order_id))
            conn.commit()
            return RedirectResponse('/pedido/'+order['tracking_token'],303)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    g['templates'].env.globals['fashion_editor385']=editor
    from nowup_fashion387 import install as install387
    install387(g)
    from nowup_fashion_demo385 import install as demo_install
    demo_install(g)
    @g['app'].on_event('startup')
    def setup():
        with g['db']() as c:
            g['ensure_column'](c,'products','fashion_photos385',"TEXT NOT NULL DEFAULT '[]'")
            g['ensure_column'](c,'products','fashion_details387',"TEXT NOT NULL DEFAULT '{}'")
            c.execute("INSERT OR IGNORE INTO categories(name,slug,icon,sort_order,active) VALUES('Moda e acessórios','moda-e-acessorios','👗',80,1)")
        c.close()
        from nowup_fashion_demo385 import initialize
        initialize(g)
        from nowup_fashion387 import seed_demo
        seed_demo(g)
        from nowup_fashion_stock389 import seed_colors
        seed_colors(g)

