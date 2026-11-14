"""Server-timed wait and atomic customer-selected WhatsApp handoff."""
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

TZ = ZoneInfo('America/Sao_Paulo')

def greeting(now=None):
    hour = (now or datetime.now(TZ)).astimezone(TZ).hour
    return 'bom dia' if 5 <= hour < 12 else 'boa tarde' if 12 <= hour < 18 else 'boa noite'

def dynamic_greeting(text, now=None):
    return re.sub(r'\b(?:bom dia|boa tarde|boa noite)\b', greeting(now), text, flags=re.I)

def deadline(order):
    order = dict(order)
    created = datetime.fromisoformat(order['created_at'])
    if created.tzinfo is None: created = created.replace(tzinfo=timezone.utc)
    start = order.get('accept_after380')
    if start:
        start = datetime.fromisoformat(start)
        if start.tzinfo is None: start = start.replace(tzinfo=timezone.utc)
        created = max(created, start)
    return created + timedelta(seconds=60)

def endpoint(order):
    order = dict(order)
    return ('/p/' + quote(order['slug'], safe='') if order.get('order_origin') == 'external' else '') + '/pedido/' + order['tracking_token'] + '/espera434'

def install(g):
    app = g['app']
    g['ORDER_STATUS_LABELS']['whatsapp_finalized'] = 'Em atendimento pelo WhatsApp'
    g['templates'].env.globals.update(wait_deadline434=lambda o: deadline(o).isoformat(), wait_endpoint434=endpoint)

    def owned(request, c, token='', slug='', order_id=0):
        if slug:
            g['nowup_storeaccounts345'].request_store(g, request)
        user = g['current_user'](request)
        if not user: raise HTTPException(401, 'Entre na sua conta para continuar.')
        lock = ' FOR UPDATE OF o' if getattr(c, 'dialect', 'sqlite') == 'postgres' else ''
        order = c.execute('SELECT o.*,p.slug,p.user_id AS owner434,p.whatsapp FROM orders o JOIN professionals p ON p.id=o.professional_id WHERE ' + ('o.id=?' if order_id else 'o.tracking_token=?') + lock, (order_id or token,)).fetchone()
        if not order or (slug and order['slug'] != slug) or user['id'] not in (order['customer_id'], order['owner434']):
            raise HTTPException(404, 'Pedido não encontrado.')
        return order, user

    def response(c, order):
        number = order['whatsapp'] or ''
        row = c.execute('SELECT whatsapp FROM store_menu257 WHERE professional_id=?', (order['professional_id'],)).fetchone()
        if order['order_origin'] == 'external' and row and row['whatsapp']: number = row['whatsapp']
        number = re.sub(r'\D', '', number)
        if len(number) in (10, 11): number = '55' + number
        available = bool(re.fullmatch(r'55\d{10,11}', number))
        paid = g['nowup_notinha401'].payment_checked(c, order)
        now = datetime.now(timezone.utc)
        payload = dict(status=order['status'], server_now=now.isoformat(), deadline=deadline(order).isoformat(), available=available and not paid, eligible=available and not paid and order['status']=='new' and now>=deadline(order))
        if order['status']=='whatsapp_finalized':
            from nowup_notinha401 import receipt
            message = 'Olá, ' + greeting() + '! Quero finalizar pelo WhatsApp o mesmo pedido ' + order['order_code'] + '.\n\n' + receipt(c, dict(order, display_name=c.execute('SELECT display_name FROM professionals WHERE id=?',(order['professional_id'],)).fetchone()[0]), g['ORDER_STATUS_LABELS']) + '\n\nEste pedido será finalizado pelo WhatsApp. Aceite e pagamento bloqueados no NowUp.'
            if available: payload['whatsapp_url'] = 'https://wa.me/' + number + '?text=' + quote(message, safe='')
        return JSONResponse(payload, headers={'Cache-Control':'private, no-store'})

    def state(request: Request, token: str='', slug: str='', order_id: int=0):
        with g['db']() as c:
            order, _ = owned(request, c, token, slug, order_id)
            return response(c, order)

    def handoff(request: Request, token: str, slug: str=''):
        origin = request.headers.get('origin', '').rstrip('/')
        if not origin or origin != str(request.base_url).rstrip('/'):
            raise HTTPException(403, 'Origem inválida.')
        with g['db']() as c:
            c.execute('BEGIN IMMEDIATE')
            order, user = owned(request, c, token, slug)
            if user['id'] != order['customer_id']: raise HTTPException(403, 'Somente o cliente pode escolher WhatsApp.')
            if order['status']=='whatsapp_finalized': return response(c, order)
            eligibility = response(c, order)
            import json
            if not json.loads(eligibility.body)['eligible']:
                raise HTTPException(409, 'O pedido foi atualizado ou ainda está no prazo de aceite. Confira o status.')
            stamp = g['now_iso']()
            changed = c.execute("UPDATE orders SET status='whatsapp_finalized',whatsapp_opened=1,updated_at=? WHERE id=? AND status='new'", (stamp, order['id'])).rowcount
            if changed != 1: raise HTTPException(409, 'O pedido foi atualizado. Confira o status.')
            c.execute('INSERT INTO order_status_history(order_id,status,created_at) VALUES(?,?,?)',(order['id'],'whatsapp_finalized',stamp))
            c.execute('DELETE FROM push_jobs WHERE order_id=?',(order['id'],))
            c.execute('INSERT INTO notifications(user_id,title,message,link,created_at) VALUES(?,?,?,?,?)',(order['owner434'],'Atendimento pelo WhatsApp',order['order_code']+' — cliente escolheu finalizar pelo WhatsApp. Pedido bloqueado no NowUp.','/painel?abrir_pedido='+str(order['id']),stamp))
            c.commit()
            order, _ = owned(request, c, token, slug)
            return response(c, order)

    for prefix in ('', '/p/{slug}'):
        app.add_api_route(prefix+'/pedido/{token}/espera434', state, methods=['GET'])
        app.add_api_route(prefix+'/pedido/{token}/espera434', handoff, methods=['POST'])
    app.add_api_route('/painel/pedidos/{order_id}/espera434', state, methods=['GET'])
