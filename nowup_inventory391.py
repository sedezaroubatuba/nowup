"""Transactional fashion stock. All callers hold one store lock until commit.

Legacy total/size balances remain shared across colors (never multiplied).
New variant balances are exact size/color pairs. Expired holds are excluded at
read time, so correctness does not depend on a scheduler or browser cleanup.
"""
import json,re,secrets,time
from collections import Counter
from fastapi import Form,HTTPException,Request
from fastapi.responses import JSONResponse

TTL=600

def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS fashion_inventory391 (
      product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
      size TEXT NOT NULL,color TEXT NOT NULL,on_hand INTEGER NOT NULL CHECK(on_hand>=0),
      source_qty INTEGER NOT NULL,PRIMARY KEY(product_id,size,color))''')
    c.execute('''CREATE TABLE IF NOT EXISTS fashion_holds391 (
      owner TEXT NOT NULL,customer_id INTEGER NOT NULL,professional_id INTEGER NOT NULL,
      product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
      size TEXT NOT NULL,color TEXT NOT NULL,quantity INTEGER NOT NULL CHECK(quantity>0),
      expires_at DOUBLE PRECISION NOT NULL,order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
      state TEXT NOT NULL DEFAULT 'held',PRIMARY KEY(owner,product_id,size,color))''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_fashion_holds391 ON fashion_holds391(product_id,expires_at,state)')
    c.execute('''CREATE TABLE IF NOT EXISTS fashion_order_items391 (
      item_id INTEGER PRIMARY KEY REFERENCES order_items(id) ON DELETE CASCADE,
      size TEXT NOT NULL,color TEXT NOT NULL)''')


def lock_store(c,pid):
    if getattr(c,'dialect','sqlite')=='postgres':
        c._begin()
        c.execute('SELECT pg_advisory_xact_lock(?)',(-391000000000000000-int(pid),))


def data(product):
    return json.loads(product.get('fashion_details387') or '{}').get('stock',{'mode':'none'})


def definitions(stock):
    mode=stock.get('mode','none')
    if mode=='total':return {('',''):int(stock['total'])}
    if mode=='sizes':return {(s,''):int(n) for s,n in stock['sizes'].items()}
    if mode=='variants':return {(v['size'],v['color']):int(v['quantity']) for v in stock['variants']}
    return {}


def ensure(c,product):
    """Initialize or apply an explicit merchant balance edit; never replenish on reads."""
    defs=definitions(data(product));pid=product['id']
    for (size,color),n in sorted(defs.items()):
        c.execute('INSERT INTO fashion_inventory391(product_id,size,color,on_hand,source_qty) VALUES(?,?,?,?,?) ON CONFLICT(product_id,size,color) DO NOTHING',(pid,size,color,n,n))
        suffix=' FOR UPDATE' if getattr(c,'dialect','sqlite')=='postgres' else ''
        row=c.execute('SELECT * FROM fashion_inventory391 WHERE product_id=? AND size=? AND color=?'+suffix,(pid,size,color)).fetchone()
    return defs


def configure(c,product_id,stock):
    """An explicit merchant edit sets physical balances, never a catalogue read."""
    defs=definitions(stock)
    active=c.execute("SELECT size,color,SUM(quantity) AS held FROM fashion_holds391 WHERE product_id=? AND state='held' AND expires_at>? GROUP BY size,color",(product_id,time.time())).fetchall()
    for row in active:
        if (row['size'],row['color']) not in defs or defs[(row['size'],row['color'])]<row['held']:
            raise HTTPException(409,'Existem reservas ativas. O saldo não pode ficar abaixo do reservado nem mudar de controle agora.')
    for (size,color),quantity in sorted(defs.items()):
        c.execute('INSERT INTO fashion_inventory391(product_id,size,color,on_hand,source_qty) VALUES(?,?,?,?,?) ON CONFLICT(product_id,size,color) DO UPDATE SET on_hand=excluded.on_hand,source_qty=excluded.source_qty',(product_id,size,color,quantity,quantity))


def pool_key(product,raw):
    stock=data(product);mode=stock.get('mode','none')
    groups=raw.get('groups',{})
    size=(groups.get('fashionSize385') or [''])[0];color=(groups.get('fashionColor385') or [''])[0]
    if mode=='none':return None
    return (product['id'],size if mode in ('sizes','variants') else '',color if mode=='variants' else '')


def demand(c,clean):
    wanted=Counter()
    for product,qty,notes,options,price in clean:
        # Server validation already checked all options. Recover raw selections
        # from the request snapshot stored temporarily by the caller instead.
        raw=product.get('_selection391',{})
        defs=ensure(c,product);key=pool_key(product,raw)
        if key:
            if key[1:] not in defs:raise HTTPException(409,'Variação esgotada ou indisponível.')
            wanted[key]+=qty
    return wanted


def replace(c,owner,uid,pid,wanted,order_id=None,deadline=None):
    now=time.time();deadline=deadline or now+TTL
    c.execute("DELETE FROM fashion_holds391 WHERE professional_id=? AND order_id IS NULL AND state='held' AND expires_at<=?",(pid,now))
    # Sorted row locks plus the store lock protect read/check/write as one unit.
    for (product,size,color),qty in sorted(wanted.items()):
        suffix=' FOR UPDATE' if getattr(c,'dialect','sqlite')=='postgres' else ''
        row=c.execute('SELECT on_hand FROM fashion_inventory391 WHERE product_id=? AND size=? AND color=?'+suffix,(product,size,color)).fetchone()
        other=c.execute("SELECT COALESCE(SUM(quantity),0) FROM fashion_holds391 WHERE product_id=? AND size=? AND color=? AND owner<>? AND state='held' AND expires_at>?",(product,size,color,owner,now)).fetchone()[0]
        if not row or qty>row[0]-other:raise HTTPException(409,'Esgotado: outra pessoa reservou esta variação. Atualize a quantidade ou escolha outra peça.')
    c.execute("DELETE FROM fashion_holds391 WHERE owner=? AND state='held'",(owner,))
    for (product,size,color),qty in sorted(wanted.items()):
        c.execute("INSERT INTO fashion_holds391(owner,customer_id,professional_id,product_id,size,color,quantity,expires_at,order_id,state) VALUES(?,?,?,?,?,?,?,?,?,'held')",(owner,uid,pid,product,size,color,qty,deadline,order_id))
    return deadline


def attach(c,p,uid,basket,clean,oid):
    if p.get('business_type')!='fashion':return
    lock_store(c,p['id']);wanted=demand(c,clean)
    if not wanted:return
    owner='order:'+str(oid)
    if basket:
        cartowner=cart_owner(uid,p['id'],basket)
        existing={ (r['product_id'],r['size'],r['color']):r for r in c.execute("SELECT * FROM fashion_holds391 WHERE owner=? AND state='held' AND expires_at>?",(cartowner,time.time())).fetchall() }
        if {k:r['quantity'] for k,r in existing.items()}!=dict(wanted):raise HTTPException(409,'Sua reserva expirou ou o carrinho mudou. Atualize a reserva antes de enviar.')
        c.execute('UPDATE fashion_holds391 SET owner=?,order_id=? WHERE owner=?',(owner,oid,cartowner))
    else:
        # Older clients still get an atomic checkout hold; they cannot oversell.
        replace(c,owner,uid,p['id'],wanted,oid)


def snapshot(c,item_id,product):
    if '_selection391' not in product:return
    raw=product['_selection391'].get('groups',{})
    c.execute('INSERT INTO fashion_order_items391(item_id,size,color) VALUES(?,?,?)',(item_id,(raw.get('fashionSize385') or [''])[0],(raw.get('fashionColor385') or [''])[0]))


def write_balances(c,product_ids):
    for pid in sorted(product_ids):
        product=c.execute('SELECT fashion_details387 FROM products WHERE id=?',(pid,)).fetchone()
        if not product:continue
        detail=json.loads(product[0] or '{}');stock=detail.get('stock',{})
        rows=c.execute('SELECT * FROM fashion_inventory391 WHERE product_id=?',(pid,)).fetchall()
        for r in rows:
            if stock.get('mode')=='total' and not r['size'] and not r['color']:stock['total']=r['on_hand']
            elif stock.get('mode')=='sizes' and not r['color'] and r['size'] in stock['sizes']:stock['sizes'][r['size']]=r['on_hand']
            elif stock.get('mode')=='variants':
                for v in stock['variants']:
                    if (v['size'],v['color'])==(r['size'],r['color']):v['quantity']=r['on_hand']
        c.execute('UPDATE products SET fashion_details387=? WHERE id=?',(json.dumps(detail,ensure_ascii=False),pid))
        c.execute('UPDATE fashion_inventory391 SET source_qty=on_hand WHERE product_id=?',(pid,))


def order_status(c,oid,status):
    o=c.execute('SELECT o.*,p.business_type FROM orders o JOIN professionals p ON p.id=o.professional_id WHERE o.id=?',(oid,)).fetchone()
    if not o or o['business_type']!='fashion':return
    lock_store(c,o['professional_id']);owner='order:'+str(oid)
    rows=c.execute('SELECT * FROM fashion_holds391 WHERE owner=?',(owner,)).fetchall()
    if status in ('cancelled','rejected'):
        for r in rows:
            if r['state']=='sold':c.execute('UPDATE fashion_inventory391 SET on_hand=on_hand+? WHERE product_id=? AND size=? AND color=?',(r['quantity'],r['product_id'],r['size'],r['color']))
        c.execute("UPDATE fashion_holds391 SET state='released' WHERE owner=? AND state IN ('sold','held')",(owner,))
        write_balances(c,{r['product_id'] for r in rows});return
    if status not in ('confirmed','preparing','ready','out_for_delivery','completed'):return
    if rows and all(r['state']=='sold' for r in rows):return
    wanted=Counter()
    for row in c.execute('''SELECT i.*,v.size,v.color,p.fashion_details387 FROM order_items i JOIN products p ON p.id=i.product_id LEFT JOIN fashion_order_items391 v ON v.item_id=i.id WHERE i.order_id=?''',(oid,)).fetchall():
        product=dict(row);product['id']=row['product_id'];defs=ensure(c,product)
        if not defs:continue
        if row['size'] is None:raise HTTPException(409,'Escolha tamanho e cor no pedido antes de confirmar esta peça.')
        key=pool_key(product,{'groups':{'fashionSize385':[row['size']],'fashionColor385':[row['color']]}})
        if key[1:] not in defs:raise HTTPException(409,'A variação do pedido não está disponível.')
        wanted[key]+=row['quantity']
    replace(c,owner,o['customer_id'],o['professional_id'],wanted,oid)
    for (pid,size,color),qty in sorted(wanted.items()):
        changed=c.execute('UPDATE fashion_inventory391 SET on_hand=on_hand-? WHERE product_id=? AND size=? AND color=? AND on_hand>=?',(qty,pid,size,color,qty)).rowcount
        if changed!=1:raise HTTPException(409,'Estoque insuficiente. Revise o pedido.')
    c.execute("UPDATE fashion_holds391 SET state='sold' WHERE owner=?",(owner,));write_balances(c,{k[0] for k in wanted})


def cart_owner(uid,pid,basket):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{16,128}',basket):raise HTTPException(400,'Identificador do carrinho inválido.')
    return f'cart:{uid}:{pid}:{basket}'


def available(c,pid,owner=''):
    result=[]
    for product in c.execute('SELECT * FROM products WHERE professional_id=? AND available=1 ORDER BY id',(pid,)).fetchall():
        product=dict(product);defs=ensure(c,product)
        rows=[]
        for (size,color),_ in defs.items():
            row=c.execute('SELECT on_hand FROM fashion_inventory391 WHERE product_id=? AND size=? AND color=?',(product['id'],size,color)).fetchone()
            other=c.execute("SELECT COALESCE(SUM(quantity),0) FROM fashion_holds391 WHERE product_id=? AND size=? AND color=? AND state='held' AND expires_at>? AND owner<>?",(product['id'],size,color,time.time(),owner)).fetchone()[0]
            rows.append({'size':size,'color':color,'available':max(0,row[0]-other)})
        result.append({'id':product['id'],'mode':data(product).get('mode','none'),'variants':rows})
    return result


def install(g):
    @g['app'].post('/p/{slug}/menu/estoque/reservar')
    def reserve(request:Request,slug:str,cart_json:str=Form(...),basket_key:str=Form(...)):
        from nowup_storeapp256 import store
        from nowup_storeapp257 import validate
        p=dict(store(g,slug))
        if p.get('business_type')!='fashion':raise HTTPException(404)
        u=g['require_user'](request,'customer');owner=cart_owner(u['id'],p['id'],basket_key)
        if p.get('is_demo'):return JSONResponse({'demo':True,'expires_at':0,'stock':[]})
        c=g['db']()
        try:
            c.execute('BEGIN IMMEDIATE');lock_store(c,p['id'])
            if cart_json.strip()=='[]':clean=[]
            else:clean=validate(g,c,p,cart_json,'pickup','on_delivery','','','',stock_only391=True)[0]
            deadline=replace(c,owner,u['id'],p['id'],demand(c,clean))
            stock=available(c,p['id'],owner);c.commit()
            return JSONResponse({'expires_at':deadline,'stock':stock},headers={'Cache-Control':'private, no-store'})
        finally:c.close()
    @g['app'].get('/p/{slug}/menu/estoque')
    def stock_view(request:Request,slug:str,basket_key:str=''):
        from nowup_storeapp256 import store
        p=dict(store(g,slug))
        if p.get('business_type')!='fashion':raise HTTPException(404)
        u=g['current_user'](request);owner=cart_owner(u['id'],p['id'],basket_key) if u and basket_key else ''
        c=g['db']()
        try:
            c.execute('BEGIN IMMEDIATE');lock_store(c,p['id']);stock=available(c,p['id'],owner);c.commit()
            return JSONResponse({'stock':stock},headers={'Cache-Control':'private, no-store'})
        finally:c.close()
