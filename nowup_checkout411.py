"""Optional merchant POS and named tables, backed by the existing sales ledger."""
import secrets
import json
from nowup_kitchen413 import metadata,needs_choices,compose
from urllib.parse import quote
import unicodedata
from datetime import datetime,date
from fastapi import Request,Form,HTTPException,APIRouter
from fastapi.responses import JSONResponse,RedirectResponse
import nowup_sales107 as ledger
from nowup_combos303 import current_price


def normalized(value):return ' '.join(unicodedata.normalize('NFKC',value).casefold().split())


def install(g):
    router=APIRouter(route_class=ledger.SalesRoute)
    def startup():
        with ledger.connection() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS checkout_tables411(
                id INTEGER PRIMARY KEY,professional_id INTEGER NOT NULL REFERENCES professionals(id),
                name TEXT NOT NULL,name_key TEXT NOT NULL,current_sale INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,UNIQUE(professional_id,name_key));
                CREATE TABLE IF NOT EXISTS checkout_sales411(
                sale_id INTEGER PRIMARY KEY REFERENCES manual_sales107(id),
                table_id INTEGER NOT NULL DEFAULT 0,service TEXT NOT NULL CHECK(service IN ('counter','pickup','delivery')));
                CREATE INDEX IF NOT EXISTS checkout_table_sales411 ON checkout_sales411(table_id,sale_id);''')
            g['ensure_column'](c,'checkout_sales411','customer_name413',"TEXT NOT NULL DEFAULT ''")
            c.execute('CREATE TABLE IF NOT EXISTS checkout_item_details413(item_id INTEGER PRIMARY KEY REFERENCES manual_items107(id) ON DELETE CASCADE,snapshot TEXT NOT NULL)')
    g['app'].router.add_event_handler('startup',startup)
    def begin(c):c.execute('BEGIN' if getattr(c,'dialect','sqlite')=='postgres' else 'BEGIN IMMEDIATE')
    def lock(c):return ' FOR UPDATE' if getattr(c,'dialect','sqlite')=='postgres' else ''
    def mapped(c,pid,sid):
        sale=ledger.owned(c,pid,sid)
        if not c.execute('SELECT sale_id FROM checkout_sales411 WHERE sale_id=?',(sid,)).fetchone():raise HTTPException(404,'Venda não encontrada neste checkout.')
        return sale
    def state(c,pid,sid):
        s=mapped(c,pid,sid);s['paid']=ledger.paid(c,sid);s['remaining']=s['total_cents']-s['paid']
        s['items']=[dict(r) for r in c.execute('SELECT i.*,pr.image_filename FROM manual_items107 i LEFT JOIN products pr ON pr.id=i.product_id AND pr.professional_id=? WHERE i.sale_id=? ORDER BY i.id',(pid,sid))]
        for item in s['items']:item['image_url']='/uploads/'+quote(item['image_filename'],safe='') if item['image_filename'] else ''
        s['payments']=[dict(r) for r in c.execute('SELECT * FROM manual_payments107 WHERE sale_id=? ORDER BY id',(sid,))]
        info=c.execute('SELECT table_id,customer_name413 FROM checkout_sales411 WHERE sale_id=?',(sid,)).fetchone()
        s['table_id']=info['table_id'];s['customer_name413']=info['customer_name413']
        return s
    def go(sid=0,tab='counter'):return RedirectResponse('/painel/checkout?tab='+tab+('&sale='+str(sid) if sid else ''),303)
    def new_sale(c,pid,uid,label,service,token,tid=0):
        old=c.execute('SELECT id FROM manual_sales107 WHERE professional_id=? AND creation_token=?',(pid,token)).fetchone()
        if old:
            mapped(c,pid,old['id']);return old['id']
        now=ledger.stamp();sid=c.execute('INSERT INTO manual_sales107(professional_id,label,channel,created_at,updated_at,creation_token) VALUES(?,?,?,?,?,?)',(pid,label,'delivery' if service=='delivery' else 'presential',now,now,token)).lastrowid
        c.execute('INSERT INTO checkout_sales411(sale_id,table_id,service) VALUES(?,?,?)',(sid,tid,service));ledger.history(c,sid,uid,'abrir','Mesa' if tid else service)
        return sid
    def report(c,pid,day):
        totals={'delivery':0,'pickup':0,'counter':0};methods={};rows=[]
        for s in c.execute("SELECT s.*,x.service,x.table_id FROM manual_sales107 s LEFT JOIN checkout_sales411 x ON x.sale_id=s.id WHERE s.professional_id=? AND s.status='completed'",(pid,)):
            if ledger.local_day(s['closed_at'])!=day:continue
            kind=s['service'] or ('delivery' if s['channel']=='delivery' else 'counter');totals[kind]+=s['total_cents'];rows.append(dict(code='CX-'+str(s['id']),origin='Mesa' if s['table_id'] else 'Caixa manual',label=s['label'],kind=kind,cents=s['total_cents']))
            for p in c.execute('SELECT method,cents FROM manual_payments107 WHERE sale_id=?',(s['id'],)):methods[p['method']]=methods.get(p['method'],0)+p['cents']
        for o in c.execute("SELECT o.*,COALESCE((SELECT MAX(created_at) FROM order_status_history WHERE order_id=o.id AND status='completed'),o.updated_at,o.created_at) sold_at FROM orders o WHERE professional_id=? AND status='completed'",(pid,)):
            if ledger.local_day(o['sold_at'])!=day:continue
            kind='delivery' if o['fulfillment_type']=='delivery' else 'pickup';totals[kind]+=o['total_cents'];methods[o['payment_method']]=methods.get(o['payment_method'],0)+o['total_cents'];rows.append(dict(code=o['order_code'] or str(o['id']),origin='Link' if o['order_origin']=='external' else 'Vitrine',label='',kind=kind,cents=o['total_cents']))
        return dict(totals=totals,total=sum(totals.values()),methods=methods,rows=rows)
    g['checkout_report411']=report

    @router.get('/painel/checkout')
    def page(request:Request,tab:str='counter',sale:int=0,day:str=''):
        if tab not in ('counter','tables','closed','summary'):tab='counter'
        try:chosen=date.fromisoformat(day) if day else datetime.now(ledger.TZ).date()
        except ValueError:raise HTTPException(400,'Data inválida.')
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request)
            current=state(c,p['id'],sale) if sale else None
            tables=[dict(r) for r in c.execute('''SELECT t.*,s.status,s.total_cents FROM checkout_tables411 t
                LEFT JOIN manual_sales107 s ON s.id=t.current_sale WHERE t.professional_id=? ORDER BY t.id''',(p['id'],))] if tab=='tables' else []
            accounts=[dict(r) for r in c.execute("SELECT s.*,x.table_id FROM manual_sales107 s JOIN checkout_sales411 x ON x.sale_id=s.id WHERE s.professional_id=? AND "+("x.table_id>0 AND s.status<>'open'" if tab=='closed' else "x.table_id=0 AND s.status='open'")+" ORDER BY s.id DESC LIMIT 100",(p['id'],))] if tab in ('counter','closed') else []
            summary=report(c,p['id'],chosen) if tab=='summary' else None
        return g['templates'].TemplateResponse('checkout411.html',g['context'](request,pro=p,checkout411=current,tables411=tables,accounts411=accounts,tab411=tab,summary411=summary,day411=chosen.isoformat(),token411=secrets.token_urlsafe(24),methods411=ledger.METHODS,cardapio_panel408=True),headers={'Cache-Control':'private, no-store'})

    @router.post('/painel/checkout/mesas')
    def create_table(request:Request,name:str=Form(...)):
        ledger.check_origin(request);clean=' '.join(name.split())
        if not clean or len(clean)>80:raise HTTPException(400,'Informe um nome de mesa de até 80 caracteres.')
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);begin(c)
            c.execute('INSERT OR IGNORE INTO checkout_tables411(professional_id,name,name_key,created_at) VALUES(?,?,?,?)',(p['id'],clean,normalized(clean),ledger.stamp()))
        return go(tab='tables')

    @router.post('/painel/checkout/mesas/{tid}/abrir')
    def open_table(request:Request,tid:int):
        ledger.check_origin(request)
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);begin(c)
            t=c.execute('SELECT * FROM checkout_tables411 WHERE id=? AND professional_id=?'+lock(c),(tid,p['id'])).fetchone()
            if not t:raise HTTPException(404,'Mesa não encontrada.')
            old=c.execute("SELECT id FROM manual_sales107 WHERE id=? AND professional_id=? AND status='open'",(t['current_sale'],p['id'])).fetchone()
            if old:sid=old['id']
            else:
                sid=new_sale(c,p['id'],u['id'],t['name'],'counter',secrets.token_urlsafe(24),tid)
                c.execute('UPDATE checkout_tables411 SET current_sale=? WHERE id=?',(sid,tid))
        return go(sid,'tables')

    @router.post('/painel/checkout/abrir')
    def open_counter(request:Request,token:str=Form(...),service:str=Form('counter'),customer_name:str=Form('')):
        ledger.check_origin(request)
        if service not in ('counter','pickup','delivery') or not 16<=len(token)<=100:raise HTTPException(400,'Confira a origem da venda.')
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);begin(c)
            # Serialize retries of the same creation token on Postgres too.
            c.execute('SELECT id FROM professionals WHERE id=?'+lock(c),(p['id'],)).fetchone()
            sid=new_sale(c,p['id'],u['id'],{'counter':'Venda no balcão','pickup':'Retirada manual','delivery':'Entrega manual'}[service],service,token)
            if customer_name.strip():c.execute('UPDATE checkout_sales411 SET customer_name413=? WHERE sale_id=?',(customer_name.strip()[:120],sid))
        return go(sid)

    @router.get('/painel/checkout/catalogo')
    def catalog(request:Request,q:str=''):
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);query=q.strip()[:120]
            rows=c.execute('''SELECT pr.* FROM products pr WHERE professional_id=? AND available=1
                AND (CAST(id AS TEXT)=? OR lower(name) LIKE lower(?))
                AND NOT EXISTS(SELECT 1 FROM product_categories pc WHERE pc.professional_id=pr.professional_id AND lower(pc.name)=lower(pr.category) AND pc.active=0)
                ORDER BY CASE WHEN CAST(id AS TEXT)=? THEN 0 ELSE 1 END,name LIMIT 50''',(p['id'],query,'%'+query+'%',query)).fetchall()
            products=[dict(id=r['id'],name=r['name'],price_cents=current_price(r),weight=bool(r['sold_by_weight370']),image_url='/uploads/'+quote(r['image_filename'],safe='') if r['image_filename'] else '',configurable=needs_choices(c,p['id'],r)) for r in rows]
        return JSONResponse({'products':products},headers={'Cache-Control':'private, no-store'})

    @router.get('/painel/checkout/produtos/{product_id}/opcoes')
    def options(request:Request,product_id:int):
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request)
            product=c.execute('SELECT * FROM products WHERE id=? AND professional_id=? AND available=1',(product_id,p['id'])).fetchone()
            if not product:raise HTTPException(404,'Produto não encontrado.')
            result=metadata(c,p['id'],product)
        return JSONResponse(result,headers={'Cache-Control':'private, no-store'})

    @router.get('/painel/checkout/vendas/{sid}')
    def snapshot(request:Request,sid:int):
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);data=state(c,p['id'],sid)
        return JSONResponse(data,headers={'Cache-Control':'private, no-store'})

    @router.post('/painel/checkout/vendas/{sid}/alterar')
    def change(request:Request,sid:int,version:int=Form(...),action:str=Form(...),product_id:int=Form(0),quantity:int=Form(1),weight_grams:int=Form(0),item_id:int=Form(0),payment_id:int=Form(0),method:str=Form(''),amount:str=Form(''),notes:str=Form(''),reason:str=Form(''),refund:str=Form(''),customer_name:str=Form(''),selections_json:str=Form('')):
        ledger.check_origin(request)
        if action not in ('item','remove_item','payment','remove_payment','close','cancel','customer'):raise HTTPException(400,'Ação inválida.')
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);mapped(c,p['id'],sid)
        if action=='customer':
            clean=' '.join(customer_name.split())
            if not clean or len(clean)>120:raise HTTPException(400,'Informe o nome do cliente, de até 120 caracteres.')
            with ledger.connection() as c:
                u,p=ledger.merchant(c,request);begin(c);s=ledger.owned(c,p['id'],sid,True)
                if s['status']!='open' or s['version']!=version:raise HTTPException(409,'Conta atualizada. Confira antes de salvar o cliente.')
                c.execute('UPDATE checkout_sales411 SET customer_name413=? WHERE sale_id=?',(clean,sid))
                c.execute('UPDATE manual_sales107 SET version=version+1,updated_at=? WHERE id=?',(ledger.stamp(),sid));ledger.history(c,sid,u['id'],'customer','Cliente atualizado')
        elif action=='item':
            with ledger.connection() as c:
                u,p=ledger.merchant(c,request);begin(c);s=ledger.owned(c,p['id'],sid,True)
                if s['status']!='open' or s['version']!=version:raise HTTPException(409,'Conta atualizada. Confira os valores antes de lançar novamente.')
                product=c.execute('SELECT * FROM products WHERE id=? AND professional_id=? AND available=1',(product_id,p['id'])).fetchone()
                if not product:raise HTTPException(400,'Escolha um produto disponível da sua loja.')
                if c.execute('SELECT 1 FROM product_categories WHERE professional_id=? AND lower(name)=lower(?) AND active=0',(p['id'],product['category'])).fetchone():raise HTTPException(400,'Categoria indisponível.')
                if product['sold_by_weight370']:
                    if not 1<=weight_grams<=99900000:raise HTTPException(400,'Informe o peso em gramas.')
                    cents=(current_price(product)*weight_grams+999)//1000
                    c.execute('INSERT INTO manual_items107(sale_id,product_id,product_name,category,quantity,unit_price_cents,notes) VALUES(?,?,?,?,1,?,?)',(sid,product_id,product['name']+' — '+str(weight_grams)+' g',product['category'],cents,notes.strip()[:500]));ledger.recalc(c,sid)
                elif needs_choices(c,p['id'],product):
                    info=c.execute('SELECT table_id,customer_name413 FROM checkout_sales411 WHERE sale_id=?',(sid,)).fetchone()
                    if not info['table_id'] and not info['customer_name413']:raise HTTPException(400,'Informe o nome do cliente para a comanda da cozinha.')
                    try:
                        if len(selections_json)>262144:raise ValueError()
                        selections=json.loads(selections_json)
                        if not isinstance(selections,list) or not 1<=quantity<=99 or len(selections)!=quantity:raise ValueError()
                    except (ValueError,TypeError):raise HTTPException(400,'Confira as escolhas de cada unidade do produto.')
                    for raw in selections:
                        cents,details,snapshot=compose(g,c,p['id'],product,raw)
                        item=c.execute('INSERT INTO manual_items107(sale_id,product_id,product_name,category,quantity,unit_price_cents,notes) VALUES(?,?,?,?,1,?,?)',(sid,product_id,product['name'],product['category'],cents,details)).lastrowid
                        c.execute('INSERT INTO checkout_item_details413(item_id,snapshot) VALUES(?,?)',(item,snapshot))
                    ledger.recalc(c,sid)
                else:ledger.add_item(c,p['id'],sid,product_id,quantity,notes)
                c.execute('UPDATE manual_sales107 SET version=version+1,updated_at=? WHERE id=?',(ledger.stamp(),sid));ledger.history(c,sid,u['id'],'item','Código '+str(product_id)+', quantidade '+str(weight_grams or quantity))
        else:
            ledger.mutate(request,sid,version,action,product_id=0,quantity=1,item_id=item_id,payment_id=payment_id,method=method,amount=amount,label='',notes='',reason=reason,refund=refund)
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);result=state(c,p['id'],sid)
        if 'application/json' in request.headers.get('accept',''):return JSONResponse(result,headers={'Cache-Control':'no-store'})
        return go(sid,'tables' if result['table_id'] else 'counter')

    @router.get('/painel/checkout/vendas/{sid}/imprimir')
    def receipt(request:Request,sid:int,cozinha:int=0):
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);s=state(c,p['id'],sid)
        return g['templates'].TemplateResponse('checkout_receipt411.html',g['context'](request,pro=p,checkout411=s,methods411=ledger.METHODS,kitchen413=bool(cozinha),cardapio_panel408=True),headers={'Cache-Control':'private, no-store'})
    g['app'].include_router(router)
