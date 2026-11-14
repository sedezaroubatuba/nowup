"""Authenticated order receipt, shared by merchant, customer and printing."""
import json
import re
from urllib.parse import quote
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

CONFIRMED={'confirmed','preparing','ready','out_for_delivery','completed'}
PAYMENTS={'pix':'Pix','cash':'Dinheiro','credit':'Cartão de crédito na entrega/retirada','debit':'Cartão de débito na entrega/retirada','on_delivery':'Combinar com a loja'}

def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS order_payment_checks401(
      order_id INTEGER PRIMARY KEY, checked_by INTEGER NOT NULL,
      amount_cents INTEGER NOT NULL, checked_at TEXT NOT NULL)''')

def money(value):return 'R$ '+format(value/100,'.2f').replace('.',',')

def payment_checked(c,o):
    r=c.execute('SELECT amount_cents FROM order_payment_checks401 WHERE order_id=?',(o['id'],)).fetchone()
    return bool(r and r['amount_cents']==o['total_cents'] and o['payment_method']=='pix')

def receipt(c,o,labels):
    paid=payment_checked(c,o) and o['status'] not in {'cancelled','rejected'}
    lines=[o['display_name'], 'PEDIDO '+str(o['order_code'] or o['id']),
           'Situação: '+labels.get(o['status'],o['status']), '',
           'Cliente: '+o['customer_name'], 'Telefone: '+o['customer_phone'],
           ('Entrega: '+o['address']+(' — '+o['neighborhood'] if o['neighborhood'] else '')) if o['fulfillment_type']=='delivery' else 'Retirada no local']
    if o['fulfillment_type']!='delivery' and o['address']:lines.append('Endereço informado: '+o['address'])
    if o['address_reference']:lines.append('Referência: '+o['address_reference'])
    lines+=['','ITENS']
    for row in c.execute('SELECT * FROM order_items WHERE order_id=? ORDER BY id',(o['id'],)):
        i=dict(row);lines.append(f"{i['quantity']} × {i['product_name']} — {money(i['quantity']*i['unit_price_cents'])}")
        for op in c.execute('SELECT option_name FROM order_item_options WHERE order_item_id=? ORDER BY id',(i['id'],)):
            lines.append('  + '+op['option_name']+' (incluído no valor do item)')
        try:pack=json.loads(i.get('combo_pack305') or '{}')
        except (ValueError,TypeError):pack={}
        if isinstance(pack,dict) and pack.get('items'):
            for unit in range(i['quantity']):
                lines.append('  Combo '+str(unit+1)+' — composição incluída:')
                for child in pack['items']:
                    lines.append(f"    {child.get('quantity',1)} × {child.get('name','')}")
                for child in pack.get('units364',[]):
                    lines.append(f"    {child.get('name','')} {child.get('position','')}: {child.get('notes') or 'Completo'}")
                    for op in child.get('options',[]):
                        lines.append('      + '+op.get('name','')+' — '+money(op.get('price_cents',0))+' (já incluído)')
                for key in ('details365','notice316','note'):
                    if pack.get(key):lines.append('    '+str(pack[key]))
        elif i.get('notes'):lines.append('  Observações: '+i['notes'])
    lines+=['','Subtotal: '+money(o['subtotal_cents']),'Entrega: '+money(o['delivery_fee_cents']),
            'TOTAL: '+money(o['total_cents']),'Forma de pagamento: '+PAYMENTS.get(o['payment_method'],'Combinar com a loja')]
    if o['payment_method']=='pix':
        lines.append('Pix recebido e conferido pelo lojista. Nada a cobrar na entrega.' if paid else 'Recebimento do Pix a conferir pelo lojista.')
    elif o['payment_method'] in ('credit','debit'):
        lines+=['Pagamento na entrega ou retirada.', 'LEVAR MAQUININHA' if o['fulfillment_type']=='delivery' else 'Preparar maquininha na retirada.']
    elif o['payment_method']=='cash':
        lines.append('Pagamento na entrega ou retirada.')
        lines.append('Troco para: '+money(o['change_for_cents'])+' — Troco: '+money(max(0,o['change_for_cents']-o['total_cents'])) if o['change_for_cents'] else 'Sem troco.')
    if o['notes']:lines.append('Observações: '+o['notes'])
    if o['status'] in {'cancelled','rejected'}:lines.append('PEDIDO ENCERRADO. Se houve pagamento, combine a devolução com a loja.')
    lines+=['','Resumo do pedido — não é documento fiscal.']
    return '\n'.join(lines)

def install(g):
    app=g['app'];db=g['db'];auth=g['require_user']
    def startup():
        with db() as c:initialize(c);c.commit()
    app.router.add_event_handler('startup',startup)
    def checked(oid):
        with db() as c:
            o=c.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
            return payment_checked(c,o) if o else False
    g['templates'].env.globals['payment_checked401']=checked
    @app.get('/pedidos/{order_id}/notinha')
    def show(request:Request,order_id:int,slug:str=""):
        if slug:g['nowup_storeaccounts345'].request_store(g,request)
        u=g['current_user'](request)
        if not u:raise HTTPException(403,'Entre na conta responsável pelo pedido')
        with db() as c:
            o=c.execute('SELECT o.*,p.display_name,p.slug,p.user_id AS owner_id FROM orders o JOIN professionals p ON p.id=o.professional_id WHERE o.id=?',(order_id,)).fetchone()
            if not o or (slug and o['slug']!=slug) or u['id'] not in (o['owner_id'],o['customer_id']):raise HTTPException(404,'Pedido não encontrado')
            merchant=u['id']==o['owner_id'];confirmed=o['status'] in CONFIRMED
            text=receipt(c,o,g['ORDER_STATUS_LABELS'])
            phone=re.sub(r'\D','',o['customer_phone'] or '')
            if len(phone) in (10,11):phone='55'+phone
            whatsapp='https://wa.me/'+phone+'?text='+quote(text,safe='') if merchant and confirmed and re.fullmatch(r'55\d{10,11}',phone) else ''
            return g['templates'].TemplateResponse('order_receipt401.html',g['context'](request,order=o,receipt_text401=text,merchant401=merchant,confirmed401=confirmed,whatsapp401=whatsapp,payment_checked=payment_checked(c,o)),headers={'Cache-Control':'private, no-store','Referrer-Policy':'no-referrer','X-Robots-Tag':'noindex, nofollow'})
    app.add_api_route('/p/{slug}/pedidos/{order_id}/notinha',show,methods=['GET'],include_in_schema=False)
    @app.post('/painel/pedidos/{order_id}/conferir-pix')
    def check(request:Request,order_id:int):
        u=auth(request,'professional')
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            o=c.execute('SELECT o.* FROM orders o JOIN professionals p ON p.id=o.professional_id WHERE o.id=? AND p.user_id=?'+(' FOR UPDATE OF o' if getattr(c,'dialect','sqlite')=='postgres' else ''),(order_id,u['id'])).fetchone()
            if not o:raise HTTPException(404,'Pedido não encontrado')
            if o['payment_method']!='pix' or o['status'] not in (CONFIRMED|{'new','awaiting_payment'}):raise HTTPException(409,'Confirme um pedido Pix antes de registrar o recebimento')
            if o['order_origin']=='external' and o['status'] in ('new','awaiting_payment','confirmed'):
                c.execute('UPDATE orders SET status=? WHERE id=?',('preparing',order_id))
                c.execute('INSERT INTO order_status_history(order_id,status,created_at) VALUES(?,?,?)',(order_id,'preparing',g['now_iso']()))
            elif o['status']=='awaiting_payment':
                c.execute('UPDATE orders SET status=? WHERE id=?',('new',order_id))
                c.execute('INSERT INTO order_status_history(order_id,status,created_at) VALUES(?,?,?)',(order_id,'new',g['now_iso']()))
            c.execute('INSERT INTO order_payment_checks401(order_id,checked_by,amount_cents,checked_at) VALUES(?,?,?,?) ON CONFLICT(order_id) DO UPDATE SET checked_by=excluded.checked_by,amount_cents=excluded.amount_cents,checked_at=excluded.checked_at',(order_id,u['id'],o['total_cents'],g['now_iso']()))
            c.execute('UPDATE orders SET updated_at=? WHERE id=?',(g['now_iso'](),order_id));c.commit()
        if 'application/json' in request.headers.get('accept',''):
            return JSONResponse({'id':order_id,'payment_confirmed':True},headers={'Cache-Control':'private, no-store'})
        return RedirectResponse('/pedidos/'+str(order_id)+'/notinha',303)
