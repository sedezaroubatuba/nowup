"""Optional merchant sales ledger, isolated from customer orders."""
from contextlib import contextmanager
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal, InvalidOperation
from collections import defaultdict
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit
import json, secrets, inspect
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.routing import APIRoute
from fastapi.exceptions import RequestValidationError

class SalesRoute(APIRoute):
    def get_route_handler(self):
        original=super().get_route_handler()
        async def handler(request):
            try: return await original(request)
            except RequestValidationError:
                response=render(request,'manual_error107.html',message='Confira os campos informados e tente novamente.')
                response.status_code=400
                return response
            except HTTPException as exc:
                if exc.status_code==401: return RedirectResponse('/entrar',303)
                response=render(request,'manual_error107.html',message=exc.detail)
                response.status_code=exc.status_code
                return response
        return handler

router=APIRouter(route_class=SalesRoute)
TZ=ZoneInfo('America/Sao_Paulo')
METHODS={'cash':'Dinheiro','pix':'Pix','credit':'Cartão de crédito','debit':'Cartão de débito'}

def configure(db,auth,templates,context):
    global _db,_auth,_templates,_context
    _db,_auth,_templates,_context=db,auth,templates,context

@contextmanager
def connection():
    c=_db()
    try:
        with c: yield c
    finally: c.close()

def initialize():
    with connection() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS manual_sales107(
          id INTEGER PRIMARY KEY, professional_id INTEGER NOT NULL REFERENCES professionals(id),
          label TEXT NOT NULL, channel TEXT NOT NULL CHECK(channel IN ('presential','delivery')),
          status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','completed','cancelled')),
          total_cents INTEGER NOT NULL DEFAULT 0 CHECK(total_cents>=0), version INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL, closed_at TEXT,
          cancel_reason TEXT NOT NULL DEFAULT '', refund_recorded INTEGER NOT NULL DEFAULT 0,
          creation_token TEXT NOT NULL, UNIQUE(professional_id,creation_token));
        CREATE TABLE IF NOT EXISTS manual_items107(
          id INTEGER PRIMARY KEY, sale_id INTEGER NOT NULL REFERENCES manual_sales107(id),
          product_id INTEGER, product_name TEXT NOT NULL, category TEXT NOT NULL,
          quantity INTEGER NOT NULL CHECK(quantity>0), unit_price_cents INTEGER NOT NULL CHECK(unit_price_cents>=0),
          notes TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS manual_payments107(
          id INTEGER PRIMARY KEY, sale_id INTEGER NOT NULL REFERENCES manual_sales107(id),
          method TEXT NOT NULL CHECK(method IN ('cash','pix','credit','debit')),
          cents INTEGER NOT NULL CHECK(cents>0), created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS manual_history107(
          id INTEGER PRIMARY KEY, sale_id INTEGER NOT NULL REFERENCES manual_sales107(id),
          actor_id INTEGER NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS manual_sales107_store ON manual_sales107(professional_id,status,closed_at);
        CREATE INDEX IF NOT EXISTS manual_items107_sale ON manual_items107(sale_id);
        CREATE INDEX IF NOT EXISTS manual_payments107_sale ON manual_payments107(sale_id);
        ''')

def stamp(): return datetime.now(timezone.utc).isoformat()

def money(raw):
    try:
        value=Decimal(str(raw).strip().replace(',','.'))
        if not value.is_finite() or value<=0 or value>Decimal('1000000') or value.as_tuple().exponent < -2: raise ValueError()
        return int(value*100)
    except (InvalidOperation,ValueError,TypeError): raise HTTPException(400,'Informe um valor positivo com até duas casas decimais.')

def merchant(c,request):
    u=_auth(request,'professional')
    p=c.execute('SELECT * FROM professionals WHERE user_id=?',(u['id'],)).fetchone()
    if not p or p['blocked']: raise HTTPException(403,'Loja indisponível.')
    return u,p

def check_origin(request):
    origin=request.headers.get('origin')
    if origin:
        try:
            source=urlsplit(origin)
            target=urlsplit(str(request.url))
            def authority(parsed):
                port=parsed.port
                default=443 if parsed.scheme=='https' else 80
                return ((parsed.hostname or '').lower(),None if port in (None,default) else port)
            # Render terminates HTTPS before forwarding HTTP to the application.
            # Match the public Host, permitting HTTPS with an internal HTTP scheme.
            valid=(source.scheme in ('http','https') and bool(source.hostname)
                and not source.username and not source.password
                and source.path in ('','/') and not source.query and not source.fragment
                and authority(source)==authority(target)
                and (source.scheme==target.scheme or source.scheme=='https' and target.scheme=='http'))
        except ValueError:
            valid=False
        if not valid: raise HTTPException(403,'Origem inválida.')
    if request.headers.get('sec-fetch-site')=='cross-site': raise HTTPException(403,'Origem inválida.')

def owned(c,pid,sid):
    row=c.execute('SELECT * FROM manual_sales107 WHERE id=? AND professional_id=?',(sid,pid)).fetchone()
    if not row: raise HTTPException(404,'Venda não encontrada.')
    return dict(row)

def paid(c,sid): return c.execute('SELECT COALESCE(SUM(cents),0) FROM manual_payments107 WHERE sale_id=?',(sid,)).fetchone()[0]

def recalc(c,sid):
    total=c.execute('SELECT COALESCE(SUM(quantity*unit_price_cents),0) FROM manual_items107 WHERE sale_id=?',(sid,)).fetchone()[0]
    if total>100000000: raise HTTPException(400,'Valor da conta acima do limite.')
    if total<paid(c,sid): raise HTTPException(400,'Retire ou corrija os pagamentos antes de reduzir o total da conta.')
    c.execute('UPDATE manual_sales107 SET total_cents=? WHERE id=?',(total,sid))

def add_item(c,pid,sid,product_id,quantity,notes):
    if quantity<1 or quantity>999: raise HTTPException(400,'Quantidade deve estar entre 1 e 999.')
    p=c.execute('SELECT * FROM products WHERE id=? AND professional_id=? AND available=1',(product_id,pid)).fetchone()
    if not p: raise HTTPException(400,'Produto não disponível no cadastro da sua loja.')
    c.execute('INSERT INTO manual_items107(sale_id,product_id,product_name,category,quantity,unit_price_cents,notes) VALUES(?,?,?,?,?,?,?)',
      (sid,p['id'],p['name'],p['category'] or 'Sem categoria',quantity,p['price_cents'],notes.strip()[:500]))
    recalc(c,sid)

def history(c,sid,uid,action,detail):
    c.execute('INSERT INTO manual_history107(sale_id,actor_id,action,detail,created_at) VALUES(?,?,?,?,?)',(sid,uid,action,detail,stamp()))

def render(request,name,**data):
    args=dict(name=name,context=_context(request,**data,methods=METHODS))
    if 'request' in inspect.signature(_templates.TemplateResponse).parameters: args['request']=request
    r=_templates.TemplateResponse(**args);r.headers['Cache-Control']='no-store';return r

@router.get('/painel/vendas-manuais')
def page(request:Request,sale:int=0):
    with connection() as c:
        u,p=merchant(c,request)
        row=owned(c,p['id'],sale) if sale else None
    tab='whatsapp' if row and row['channel']=='delivery' else 'comandas'
    return RedirectResponse(f'/painel?conta={sale}#{tab}',303)

def panel_data(request,sale=0):
    with connection() as c:
        u,p=merchant(c,request)
        rows=[dict(x) for x in c.execute('SELECT s.*,COALESCE((SELECT SUM(cents) FROM manual_payments107 WHERE sale_id=s.id),0) paid,COALESCE((SELECT SUM(quantity) FROM manual_items107 WHERE sale_id=s.id),0) item_count FROM manual_sales107 s WHERE professional_id=? ORDER BY (status=\'open\') DESC,id DESC LIMIT 200',(p['id'],))]
        current=owned(c,p['id'],sale) if sale else None
        items=payments=events=[]
        if current:
            items=[dict(x) for x in c.execute('SELECT * FROM manual_items107 WHERE sale_id=? ORDER BY id',(sale,))]
            payments=[dict(x) for x in c.execute('SELECT * FROM manual_payments107 WHERE sale_id=? ORDER BY id',(sale,))]
            events=[dict(x) for x in c.execute('SELECT * FROM manual_history107 WHERE sale_id=? ORDER BY id DESC LIMIT 100',(sale,))]
            current['paid']=sum(x['cents'] for x in payments);current['remaining']=current['total_cents']-current['paid']
        products=[dict(x) for x in c.execute('SELECT id,name,price_cents FROM products WHERE professional_id=? AND available=1 ORDER BY name',(p['id'],))]
    return dict(sales=rows,sale=current,items=items,payments=payments,events=events,products=products,token=secrets.token_urlsafe(24),methods=METHODS)

def go(sid,channel):
    return RedirectResponse(f'/painel?conta={sid}#'+('whatsapp' if channel=='delivery' else 'comandas'),303)

@router.post('/painel/vendas-manuais/abrir')
def create(request:Request,label:str=Form(...),channel:str=Form(...),token:str=Form(...)):
    check_origin(request)
    if channel not in ('presential','delivery') or not label.strip() or len(label)>120 or not 16<=len(token)<=100: raise HTTPException(400,'Informe identificação e origem válidas.')
    with connection() as c:
        u,p=merchant(c,request);c.execute('BEGIN IMMEDIATE')
        old=c.execute('SELECT id FROM manual_sales107 WHERE professional_id=? AND creation_token=?',(p['id'],token)).fetchone()
        if old: sid=old['id']
        else:
            now=stamp();sid=c.execute('INSERT INTO manual_sales107(professional_id,label,channel,created_at,updated_at,creation_token) VALUES(?,?,?,?,?,?)',(p['id'],label.strip(),channel,now,now,token)).lastrowid
            history(c,sid,u['id'],'abrir',channel)
    return go(sid,channel)

@router.post('/painel/vendas-manuais/{sid}/alterar')
def mutate(request:Request,sid:int,version:int=Form(...),action:str=Form(...),product_id:int=Form(0),quantity:int=Form(1),item_id:int=Form(0),payment_id:int=Form(0),method:str=Form(''),amount:str=Form(''),label:str=Form(''),notes:str=Form(''),reason:str=Form(''),refund:str=Form('')):
    check_origin(request)
    with connection() as c:
        u,p=merchant(c,request);c.execute('BEGIN IMMEDIATE');s=owned(c,p['id'],sid)
        if s['status']=='cancelled' or (s['status']=='completed' and action!='cancel'): raise HTTPException(409,'Esta conta já foi fechada ou cancelada.')
        if version!=s['version']: raise HTTPException(409,'A conta foi atualizada. Volte à conta e confira os valores antes de tentar novamente.')
        detail=''
        if action=='item': add_item(c,p['id'],sid,product_id,quantity,notes);detail=f'Produto {product_id}, quantidade {quantity}'
        elif action=='remove_item':
            if c.execute('DELETE FROM manual_items107 WHERE id=? AND sale_id=?',(item_id,sid)).rowcount!=1: raise HTTPException(404,'Item não encontrado.')
            recalc(c,sid);detail=f'Item {item_id}'
        elif action=='label':
            if not label.strip() or len(label)>120: raise HTTPException(400,'Identificação inválida.')
            c.execute('UPDATE manual_sales107 SET label=? WHERE id=?',(label.strip(),sid));detail='Identificação alterada'
        elif action=='payment':
            cents=money(amount)
            if method not in METHODS: raise HTTPException(400,'Forma de pagamento inválida.')
            if cents>s['total_cents']-paid(c,sid): raise HTTPException(400,'Pagamento maior que o saldo. Em dinheiro, registre apenas o valor aplicado à conta, descontando o troco.')
            c.execute('INSERT INTO manual_payments107(sale_id,method,cents,created_at) VALUES(?,?,?,?)',(sid,method,cents,stamp()));detail=f'{METHODS[method]}: {cents} centavos'
        elif action=='remove_payment':
            if not reason.strip(): raise HTTPException(400,'Informe o motivo da correção do pagamento.')
            payment=c.execute('SELECT * FROM manual_payments107 WHERE id=? AND sale_id=?',(payment_id,sid)).fetchone()
            if not payment: raise HTTPException(404,'Pagamento não encontrado.')
            detail=f'Pagamento {payment_id}, {payment["method"]}, {payment["cents"]} centavos: {reason.strip()[:500]}'
            c.execute('DELETE FROM manual_payments107 WHERE id=? AND sale_id=?',(payment_id,sid))
        elif action=='close':
            if s['total_cents']<=0 or paid(c,sid)!=s['total_cents']: raise HTTPException(400,'Adicione produtos e registre o pagamento total antes de fechar.')
            c.execute("UPDATE manual_sales107 SET status='completed',closed_at=? WHERE id=?",(stamp(),sid));detail='Conta quitada'
        elif action=='cancel':
            if not reason.strip(): raise HTTPException(400,'Informe o motivo do cancelamento.')
            if paid(c,sid)>0 and refund!='1': raise HTTPException(400,'Confirme que o valor recebido foi devolvido antes de cancelar.')
            c.execute("UPDATE manual_sales107 SET status='cancelled',cancel_reason=?,refund_recorded=?,closed_at=? WHERE id=?",(reason.strip()[:500],int(paid(c,sid)>0),stamp(),sid));detail=reason.strip()[:500]
        else: raise HTTPException(400,'Ação inválida.')
        c.execute('UPDATE manual_sales107 SET version=version+1,updated_at=? WHERE id=?',(stamp(),sid));history(c,sid,u['id'],action,detail)
    return go(sid,s['channel'])

@router.post('/painel/vendas-manuais/{sid}/finalizar')
def finalize(request:Request,sid:int,version:int=Form(...),payments_json:str=Form('[]')):
    check_origin(request)
    try:
        records=json.loads(payments_json)
        if not isinstance(records,list) or len(records)>20: raise ValueError()
        parts=[]
        for part in records:
            if not isinstance(part,dict) or part.get('method') not in METHODS: raise ValueError()
            parts.append((part['method'],money(part.get('amount'))))
    except (ValueError,TypeError): raise HTTPException(400,'Confira as formas e valores do pagamento.')
    with connection() as c:
        u,p=merchant(c,request);c.execute('BEGIN IMMEDIATE');sale=owned(c,p['id'],sid)
        if sale['status']!='open' or sale['version']!=version: raise HTTPException(409,'Conta atualizada. Confira os valores antes de finalizar novamente.')
        if sale['total_cents']<=0 or paid(c,sid)+sum(value for _,value in parts)!=sale['total_cents']: raise HTTPException(400,'A soma dos pagamentos deve ser igual ao total da conta.')
        for method,value in parts:
            c.execute('INSERT INTO manual_payments107(sale_id,method,cents,created_at) VALUES(?,?,?,?)',(sid,method,value,stamp()))
            history(c,sid,u['id'],'payment',f'{METHODS[method]}: {value} centavos')
        c.execute("UPDATE manual_sales107 SET status='completed',version=version+1,closed_at=?,updated_at=? WHERE id=?",(stamp(),stamp(),sid))
        history(c,sid,u['id'],'close','Conta quitada')
    return go(sid,sale['channel'])

def period(params):
    today=datetime.now(TZ).date()
    try: start=date.fromisoformat(params.get('inicio') or today.replace(day=1).isoformat());end=date.fromisoformat(params.get('fim') or today.isoformat())
    except ValueError: raise HTTPException(400,'Datas inválidas.')
    if start>end or (end-start).days>366: raise HTTPException(400,'Escolha um período de até 367 dias.')
    return start,end

def local_day(raw):
    dt=datetime.fromisoformat(raw.replace('Z','+00:00'))
    if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ).date()

def admin_delivery_rows(c,start,end,filters=None):
    """Only manual delivery; never return labels, buyer names or presential records."""
    filters=filters or {};rows=[]
    for r in c.execute("SELECT s.*,p.display_name,p.city,p.neighborhood store_neighborhood FROM manual_sales107 s JOIN professionals p ON p.id=s.professional_id WHERE s.channel='delivery' AND p.is_demo=0"):
        if not start<=local_day(r['closed_at'] or r['created_at'])<=end: continue
        status={'open':'confirmed','completed':'completed','cancelled':'cancelled'}[r['status']]
        if any(filters.get(k) and str(r[col])!=str(filters[k]) for k,col in [('loja','professional_id'),('cidade','city'),('bairro','store_neighborhood')]): continue
        if filters.get('status') and filters['status']!=status: continue
        if filters.get('categoria') and not c.execute('SELECT 1 FROM professional_categories WHERE professional_id=? AND category_id=?',(r['professional_id'],filters['categoria'])).fetchone(): continue
        pays=[dict(x) for x in c.execute('SELECT method,cents FROM manual_payments107 WHERE sale_id=?',(r['id'],))]
        if filters.get('pagamento') and not any(p['method']==filters['pagamento'] for p in pays): continue
        rows.append(dict(id=-r['id'],professional_id=r['professional_id'],display_name=r['display_name'],city=r['city'],store_neighborhood=r['store_neighborhood'],
          customer_id=None,customer_name='',order_code=f'MD-{r["id"]:06d}',status=status,total_cents=r['total_cents'],
          payment_method=pays[0]['method'] if len(pays)==1 else 'dividido' if pays else 'Não registrado',
          created_at=r['closed_at'] or r['created_at'],updated_at=r['updated_at'],sold_at=r['closed_at'] or r['created_at'],
          order_origin='manual_delivery',cancellation_reason='Cancelamento registrado pelo lojista' if status=='cancelled' else '',manual_payments=pays))
    return rows

def admin_delivery_items(c,rows):
    result=[]
    for r in rows:
        if r['id']>=0 or r['status']!='completed': continue
        for i in c.execute('SELECT product_id,product_name,category,quantity,unit_price_cents FROM manual_items107 WHERE sale_id=?',(-r['id'],)):
            result.append(dict(order_id=r['id'],product_id=i['product_id'],product_name=i['product_name'],quantity=i['quantity'],unit_price_cents=i['unit_price_cents'],current_category=i['category']))
    return result

def sales_summary(c,pid,start,end,channel='all'):
    if channel not in ('all','presential','delivery'): raise HTTPException(400,'Origem inválida.')
    sales=[];payments=defaultdict(int);products=defaultdict(lambda:dict(quantity=0,cents=0));daily=defaultdict(int)
    if channel!='presential':
        for o in c.execute("SELECT o.*,COALESCE((SELECT MAX(created_at) FROM order_status_history WHERE order_id=o.id AND status='completed'),o.updated_at,o.created_at) sold_at FROM orders o WHERE professional_id=? AND status='completed'",(pid,)):
            if not start<=local_day(o['sold_at'])<=end: continue
            sales.append(dict(kind='NowUp',total=o['total_cents'],day=local_day(o['sold_at']).isoformat()))
            payments[o['payment_method']]+=o['total_cents']
            for i in c.execute('SELECT * FROM order_items WHERE order_id=?',(o['id'],)):
                key=i['product_name'];products[key]['quantity']+=i['quantity'];products[key]['cents']+=i['quantity']*i['unit_price_cents']
    for s in c.execute("SELECT * FROM manual_sales107 WHERE professional_id=? AND status='completed'",(pid,)):
        if channel!='all' and s['channel']!=channel: continue
        if not start<=local_day(s['closed_at'])<=end: continue
        sales.append(dict(kind='Presencial' if s['channel']=='presential' else 'Delivery manual',total=s['total_cents'],day=local_day(s['closed_at']).isoformat()))
        for pay in c.execute('SELECT * FROM manual_payments107 WHERE sale_id=?',(s['id'],)): payments[pay['method']]+=pay['cents']
        for i in c.execute('SELECT * FROM manual_items107 WHERE sale_id=?',(s['id'],)):
            products[i['product_name']]['quantity']+=i['quantity'];products[i['product_name']]['cents']+=i['quantity']*i['unit_price_cents']
    origins=defaultdict(lambda:dict(count=0,cents=0))
    for s in sales: daily[s['day']]+=s['total'];origins[s['kind']]['count']+=1;origins[s['kind']]['cents']+=s['total']
    total=sum(s['total'] for s in sales)
    clause='' if channel=='all' else ' AND channel=?';args=[pid]+([] if channel=='all' else [channel])
    opened=c.execute("SELECT COUNT(*),COALESCE(SUM(total_cents),0) FROM manual_sales107 WHERE professional_id=? AND status='open'"+clause,args).fetchone()
    return dict(cents=total,count=len(sales),ticket=round(total/len(sales)) if sales else 0,payments=dict(payments),products=sorted([dict(name=k,**v) for k,v in products.items()],key=lambda x:-x['quantity']),daily=sorted(daily.items()),origins=dict(origins),open_count=opened[0],open_cents=opened[1])

@router.get('/painel/vendas-manuais/relatorios')
def reports(request:Request):
    start,end=period(request.query_params);channel=request.query_params.get('origem','all')
    with connection() as c:
        u,p=merchant(c,request);report=sales_summary(c,p['id'],start,end,channel)
    return render(request,'manual_reports107.html',report=report,start=start.isoformat(),end=end.isoformat(),channel=channel)
