"""Optional cost control. Missing costs use an explicit 50% estimate when enabled."""
from decimal import Decimal,InvalidOperation
from fastapi import Request,Form,HTTPException
from fastapi.responses import RedirectResponse,JSONResponse
import nowup_sales107 as ledger


def cents(raw):
    try:
        value=Decimal(str(raw).strip().replace(',','.'))
        if not value.is_finite() or value<0 or value>1000000 or value.as_tuple().exponent < -2:raise ValueError()
        return int(value*100)
    except (InvalidOperation,ValueError,TypeError):raise HTTPException(400,'Informe o custo com até duas casas decimais. Não deixe em branco.')


def status(c,pid):
    row=c.execute('SELECT enabled FROM cost_settings413 WHERE professional_id=?',(pid,)).fetchone()
    total=c.execute('SELECT COUNT(*) FROM products WHERE professional_id=?',(pid,)).fetchone()[0]
    missing=c.execute('''SELECT COUNT(*) FROM products p WHERE p.professional_id=? AND
        NOT EXISTS(SELECT 1 FROM product_costs413 pc WHERE pc.product_id=p.id AND pc.professional_id=p.professional_id)''',(pid,)).fetchone()[0]
    enabled=bool(row and row['enabled'])
    return dict(enabled=enabled,total=total,missing=missing,complete=enabled and missing==0)


def effective_cost(c,pid,product_id):
    """Keep estimates distinct from actual costs; use the current selling price."""
    row=c.execute('SELECT p.*,pc.cost_cents FROM products p LEFT JOIN product_costs413 pc ON pc.product_id=p.id AND pc.professional_id=p.professional_id WHERE p.id=? AND p.professional_id=?',(product_id,pid)).fetchone()
    if not row:raise HTTPException(404,'Produto não encontrado.')
    setting=c.execute('SELECT enabled FROM cost_settings413 WHERE professional_id=?',(pid,)).fetchone()
    if not setting or not setting['enabled']:return dict(cents=None,estimated=False)
    from nowup_combos303 import current_price
    return dict(cents=row['cost_cents'] if row['cost_cents'] is not None else (current_price(row)+1)//2,estimated=row['cost_cents'] is None)


def prepare(c,pid,raw):
    # Share the store lock with activation to keep create/edit and activation atomic.
    c.execute('BEGIN IMMEDIATE')
    if getattr(c,'dialect','sqlite')=='postgres':c.execute('SELECT id FROM professionals WHERE id=? FOR UPDATE',(pid,)).fetchone()
    row=c.execute('SELECT enabled FROM cost_settings413 WHERE professional_id=?',(pid,)).fetchone()
    active=bool(row and row['enabled'])
    if raw=='__keep413':return None
    return (cents(raw) if str(raw).strip() else -1) if active else None


def save(c,pid,product_id,value):
    if value is None:return
    if value==-1:
        c.execute('DELETE FROM product_costs413 WHERE product_id=? AND professional_id=?',(product_id,pid));return
    c.execute('INSERT INTO product_costs413(product_id,professional_id,cost_cents,updated_at) VALUES(?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET cost_cents=excluded.cost_cents,updated_at=excluded.updated_at',(product_id,pid,value,ledger.stamp()))


def initialize(c):
    c.executescript('CREATE TABLE IF NOT EXISTS cost_settings413(professional_id INTEGER PRIMARY KEY REFERENCES professionals(id),enabled INTEGER NOT NULL DEFAULT 0);\n            CREATE TABLE IF NOT EXISTS product_costs413(product_id INTEGER PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,professional_id INTEGER NOT NULL REFERENCES professionals(id),cost_cents INTEGER NOT NULL CHECK(cost_cents>=0),updated_at TEXT NOT NULL);')


def install(g):
    def startup():
        with ledger.connection() as c:initialize(c)
    g['app'].router.add_event_handler('startup',startup)
    @g['app'].get('/painel/custos/config')
    def config(request:Request):
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);data=status(c,p['id'])
            data['costs']={str(r['product_id']):r['cost_cents'] for r in c.execute('SELECT product_id,cost_cents FROM product_costs413 WHERE professional_id=?',(p['id'],))} if data['enabled'] else {}
        return JSONResponse(data,headers={'Cache-Control':'private, no-store'})
    @g['app'].get('/painel/custos')
    def page(request:Request,page:int=1):
        page=max(1,page)
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);data=status(c,p['id'])
            products=c.execute('SELECT p.id,p.name,p.sold_by_weight370,p.price_cents,p.promo_price_cents,pc.cost_cents FROM products p LEFT JOIN product_costs413 pc ON pc.product_id=p.id AND pc.professional_id=p.professional_id WHERE p.professional_id=? ORDER BY p.id LIMIT 100 OFFSET ?',(p['id'],(page-1)*100)).fetchall()
            from nowup_combos303 import current_price
            products=[dict(r,estimate_cents=(current_price(r)+1)//2) for r in products]
        return g['templates'].TemplateResponse('costs413.html',g['context'](request,pro=p,costs413=data,cost_products413=products,cost_page413=page,cardapio_panel408=True),headers={'Cache-Control':'private, no-store'})
    @g['app'].post('/painel/custos/salvar')
    async def batch(request:Request):
        ledger.check_origin(request);form=await request.form()
        values={int(key[5:]):cents(value) if str(value).strip() else -1 for key,value in form.items() if key.startswith('cost_') and key[5:].isdigit()}
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);c.execute('BEGIN IMMEDIATE')
            for pid,value in values.items():
                if not c.execute('SELECT id FROM products WHERE id=? AND professional_id=?',(pid,p['id'])).fetchone():raise HTTPException(404,'Produto não encontrado.')
                save(c,p['id'],pid,value)
        return RedirectResponse('/painel/custos?ok=salvo',303)
    @g['app'].post('/painel/custos/ativar')
    def activate(request:Request):
        ledger.check_origin(request)
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);c.execute('BEGIN IMMEDIATE')
            if getattr(c,'dialect','sqlite')=='postgres':c.execute('SELECT id FROM professionals WHERE id=? FOR UPDATE',(p['id'],)).fetchone()
            data=status(c,p['id'])
            c.execute('INSERT INTO cost_settings413(professional_id,enabled) VALUES(?,1) ON CONFLICT(professional_id) DO UPDATE SET enabled=1',(p['id'],))
        return RedirectResponse('/painel/custos?ok=ativo',303)
    @g['app'].post('/painel/custos/desativar')
    def deactivate(request:Request):
        ledger.check_origin(request)
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);c.execute('BEGIN IMMEDIATE')
            if getattr(c,'dialect','sqlite')=='postgres':c.execute('SELECT id FROM professionals WHERE id=? FOR UPDATE',(p['id'],)).fetchone()
            c.execute('UPDATE cost_settings413 SET enabled=0 WHERE professional_id=?',(p['id'],))
        return RedirectResponse('/painel/custos?ok=desativado',303)
