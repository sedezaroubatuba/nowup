"""Separate merchant order lists while retaining one owner account."""
from datetime import datetime
from fastapi import Request, HTTPException


def request_category(c, user_id, plan, category_id):
    p=c.execute('SELECT id FROM professionals WHERE user_id=?',(user_id,)).fetchone()
    if not p: raise HTTPException(404,'Loja não encontrada')
    if category_id and not c.execute('SELECT id FROM categories WHERE id=? AND active=1',(category_id,)).fetchone():
        raise HTTPException(400,'Escolha uma categoria ativa da Vitrine.')
    c.execute('UPDATE professionals SET plan_category408=? WHERE id=?',(category_id if plan in ('ambos','completo') else 0,p['id']))


def approve_category(c, pid):
    p=c.execute('SELECT plan_category408,plan_requested FROM professionals WHERE id=?',(pid,)).fetchone()
    if not p or not p['plan_category408'] or p['plan_requested'] not in ('ambos','completo'):return
    cid=p['plan_category408']
    if not c.execute('SELECT id FROM categories WHERE id=? AND active=1',(cid,)).fetchone():
        raise HTTPException(400,'A categoria solicitada está inativa. Peça uma nova solicitação à loja.')
    c.execute('DELETE FROM professional_categories WHERE professional_id=?',(pid,))
    c.execute('INSERT INTO professional_categories(professional_id,category_id) VALUES(?,?)',(pid,cid))
    c.execute('UPDATE professionals SET plan_category408=0 WHERE id=?',(pid,))


def install(g):
    def initialize():
        with g['db']() as c:
            g['ensure_column'](c,'professionals','plan_category408','INTEGER NOT NULL DEFAULT 0')
    g['app'].router.add_event_handler('startup',initialize)
    def categories():
        with g['db']() as c:return c.execute('SELECT id,name FROM categories WHERE active=1 ORDER BY sort_order,name').fetchall()
    g['templates'].env.globals['channel_categories408']=categories
    from nowup_plans339 import offers409
    g['templates'].env.globals['offers409']=offers409
    def receipt_text(order):
        with g['db']() as c:return g['nowup_notinha401'].receipt(c,order,g['ORDER_STATUS_LABELS'])
    g['templates'].env.globals['receipt_text408']=receipt_text
    def requested_category(pid):
        with g['db']() as c:
            r=c.execute('SELECT cat.name FROM professionals p JOIN categories cat ON cat.id=p.plan_category408 WHERE p.id=?',(pid,)).fetchone()
            return r['name'] if r else ''
    g['templates'].env.globals['requested_category408']=requested_category

    @g['app'].get('/painel/cardapio/pedidos')
    def menu_orders(request: Request, fragment: int=0):
        user=g['require_user'](request,'professional')
        with g['db']() as c:
            pro=c.execute('SELECT * FROM professionals WHERE user_id=?',(user['id'],)).fetchone()
            if not pro:raise HTTPException(404,'Loja não encontrada')
            lower,upper=g['order_day_bounds'](datetime.now(g['SAO_PAULO_TZ']).date())
            board=g['nowup_merchant228'].board(c,pro['id'],lower,upper,g['SAO_PAULO_TZ'],channel='cardapio')
            checks={r['order_id']:r['amount_cents'] for r in c.execute('SELECT p.order_id,p.amount_cents FROM order_payment_checks401 p JOIN orders o ON o.id=p.order_id WHERE o.professional_id=?',(pro['id'],))}
            for stage in board['stages']:
                for order in stage['orders']:
                    order['payment_checked418']=order['payment_method']=='pix' and order['status'] in g['nowup_notinha401'].CONFIRMED and checks.get(order['id'])==order['total_cents']
        template='menu_orders_fragment408.html' if fragment else 'menu_orders408.html'
        return g['templates'].TemplateResponse(template,g['context'](request,pro=pro,kanban=board,
            status_labels=g['ORDER_STATUS_LABELS'],cardapio_panel408=True),headers={'Cache-Control':'private, no-store'})
