"""Revisões de pedido com aprovação explícita e valores em centavos."""
import json
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

EARLY={'new','reviewing','revision_approved'}

def initialize(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS order_revisions(id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER NOT NULL,items_json TEXT NOT NULL,total_cents INTEGER NOT NULL,state TEXT NOT NULL DEFAULT 'pending',message TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL)''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_revision_order ON order_revisions(order_id,id)')

def build_items(conn,order,keep,quantities,additions):
    original=conn.execute('SELECT * FROM order_items WHERE order_id=? ORDER BY id',(order['id'],)).fetchall()
    valid={str(i['id']) for i in original}
    if not set(keep)<=valid: raise HTTPException(400,'Item inválido')
    result=[]
    for i in original:
        if str(i['id']) not in keep: continue
        qty=int(quantities.get(str(i['id']),i['quantity']))
        if not 1<=qty<=99: raise HTTPException(400,'Quantidade inválida')
        result.append(dict(i)|{'quantity':qty})
    for pid,qty in additions:
        if not pid: continue
        p=conn.execute('SELECT * FROM products WHERE id=? AND professional_id=? AND available=1',(int(pid),order['professional_id'])).fetchone()
        if not p or not 1<=int(qty)<=99: raise HTTPException(400,'Substituto indisponível ou quantidade inválida')
        result.append({'id':None,'product_id':p['id'],'product_name':p['name'],'quantity':int(qty),'unit_price_cents':p['promo_price_cents'] if p['promo_price_cents']>0 else p['price_cents'],'notes':''})
    if not result: raise HTTPException(400,'Sem itens disponíveis: recuse o pedido com motivo')
    if len(result)>100: raise HTTPException(400,'Limite de itens excedido')
    return result,sum(i['quantity']*i['unit_price_cents'] for i in result)+order['delivery_fee_cents']

def install(g):
    app=g['app'];db=g['db'];now=g['now_iso'];auth=g['require_user']
    def startup():
        c=db();initialize(c);c.commit();c.close()
    app.add_event_handler('startup',startup)
    g['ORDER_STATUS_LABELS'].update(reviewing='Pedido em revisão',awaiting_approval='Aguardando aprovação do cliente',revision_approved='Alteração aprovada',confirmed='Pedido confirmado')
    def data(oid):
        c=db()
        try:
            initialize(c)
            r=c.execute('SELECT * FROM order_revisions WHERE order_id=? ORDER BY id DESC LIMIT 1',(oid,)).fetchone()
            return dict(r)|{'items':json.loads(r['items_json'])} if r else None
        finally:c.close()
    g['templates'].env.globals['order_revision']=data
    def notify(c,o,title,message,merchant=False):
        uid=c.execute('SELECT user_id FROM professionals WHERE id=?',(o['professional_id'],)).fetchone()[0] if merchant else o['customer_id']
        if not uid:return
        link=f"/painel?abrir_pedido={o['id']}#pedido-{o['id']}" if merchant else f"/pedido/{o['tracking_token']}"
        n=c.execute('INSERT INTO notifications(user_id,title,message,link,created_at) VALUES(?,?,?,?,?)',(uid,title,message,link,now()))
        g['nowup_alerts112'].enqueue(c,uid,n.lastrowid,{'title':title,'body':message,'url':link,'tag':f"nowup-revision-{o['id']}"})
    def status(c,o,value):
        c.execute('UPDATE orders SET status=?,updated_at=? WHERE id=?',(value,now(),o['id']))
        c.execute('INSERT INTO order_status_history(order_id,status,created_at) VALUES(?,?,?)',(o['id'],value,now()))
    @app.post('/painel/pedidos/{order_id}/revisao')
    async def propose(request:Request,order_id:int):
        u=auth(request,'professional');form=await request.form();c=db()
        try:
            c.execute('BEGIN IMMEDIATE');initialize(c)
            o=c.execute('SELECT o.* FROM orders o JOIN professionals p ON p.id=o.professional_id WHERE o.id=? AND p.user_id=?',(order_id,u['id'])).fetchone()
            if not o:raise HTTPException(404,'Pedido não encontrado')
            if o['status'] not in EARLY:raise HTTPException(409,'Pedido aguardando resposta ou já confirmado')
            if not o['customer_id']:raise HTTPException(400,'Este fluxo exige um cliente cadastrado')
            qty={str(i['id']):form.get('qty_'+str(i['id']),i['quantity']) for i in c.execute('SELECT * FROM order_items WHERE order_id=?',(order_id,))}
            adds=list(zip(form.getlist('product_id'),form.getlist('add_quantity')))
            try:items,total=build_items(c,o,form.getlist('keep'),qty,adds)
            except (ValueError,TypeError):raise HTTPException(400,'Quantidade inválida')
            message=str(form.get('message','')).strip()[:500]
            c.execute("INSERT INTO order_revisions(order_id,items_json,total_cents,message,created_at) VALUES(?,?,?,?,?)",(order_id,json.dumps(items),total,message,now()))
            status(c,o,'awaiting_approval');notify(c,o,'Seu pedido precisa de aprovação',f'A loja propôs uma alteração. Novo total: R$ {total/100:.2f}. Confira e aceite ou recuse.')
            c.commit()
            return RedirectResponse(f'/painel?abrir_pedido={order_id}#pedido-{order_id}',303)
        finally:c.close()
    @app.post('/pedido/{token}/revisao/{revision_id}')
    async def answer(request:Request,token:str,revision_id:int):
        u=auth(request,'customer');form=await request.form();decision=form.get('decision');c=db()
        try:
            c.execute('BEGIN IMMEDIATE');initialize(c)
            o=c.execute('SELECT * FROM orders WHERE tracking_token=? AND customer_id=?',(token,u['id'])).fetchone()
            if not o:raise HTTPException(404,'Pedido não encontrado')
            r=c.execute('SELECT * FROM order_revisions WHERE order_id=? ORDER BY id DESC LIMIT 1',(o['id'],)).fetchone()
            if not r or r['id']!=revision_id or r['state']!='pending' or o['status']!='awaiting_approval':raise HTTPException(409,'Esta proposta já foi respondida ou não está mais válida')
            if decision not in {'accept','decline','cancel'}:raise HTTPException(400,'Resposta inválida')
            if decision=='accept':
                items=json.loads(r['items_json']);keep=[i['id'] for i in items if i['id'] is not None]
                for old in c.execute('SELECT id FROM order_items WHERE order_id=?',(o['id'],)).fetchall():
                    if old['id'] not in keep:
                        c.execute('DELETE FROM order_item_options WHERE order_item_id=?',(old['id'],));c.execute('DELETE FROM order_items WHERE id=?',(old['id'],))
                for i in items:
                    if i['id'] is not None:c.execute('UPDATE order_items SET quantity=? WHERE id=? AND order_id=?',(i['quantity'],i['id'],o['id']))
                    else:c.execute('INSERT INTO order_items(order_id,product_id,product_name,quantity,unit_price_cents,notes) VALUES(?,?,?,?,?,?)',(o['id'],i['product_id'],i['product_name'],i['quantity'],i['unit_price_cents'],i['notes']))
                c.execute('UPDATE orders SET subtotal_cents=?,total_cents=? WHERE id=?',(r['total_cents']-o['delivery_fee_cents'],r['total_cents'],o['id']))
                status(c,o,'revision_approved');state='approved';msg='Cliente aprovou a alteração. Confira e confirme o pedido.'
            elif decision=='decline':status(c,o,'reviewing');state='declined';msg='Cliente recusou a proposta. O pedido original foi preservado; envie outra opção.'
            else:
                status(c,o,'cancelled');state='cancelled';msg='Cliente cancelou o pedido durante a revisão.'
                c.execute('UPDATE orders SET cancellation_reason=? WHERE id=?',(msg,o['id']))
            c.execute('UPDATE order_revisions SET state=? WHERE id=?',(state,r['id']));notify(c,o,'Resposta à revisão',msg,True);c.commit()
            return RedirectResponse('/pedido/'+token,303)
        finally:c.close()
