"""Cash sessions over the existing order/POS ledger, on SQLite and PostgreSQL.

No imports of historical sales, no replacement of inventory or Pix integrations.
Closed sessions use immutable snapshots; source locks protect the manual ledger.
"""
import json,secrets
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from zoneinfo import ZoneInfo
from fastapi import Request,Form,HTTPException
from fastapi.responses import RedirectResponse

METHODS={'cash':'Dinheiro','pix':'Pix','credit':'Crédito','debit':'Débito'}

def stamp():return datetime.now(timezone.utc).isoformat()

def money(raw,zero=False):
    try:
        n=Decimal(str(raw).strip().replace(',','.'))
        if not n.is_finite() or n<0 or (n==0 and not zero) or n>1000000 or n.as_tuple().exponent < -2:raise ValueError()
        return int(n*100)
    except (ValueError,InvalidOperation):raise HTTPException(400,'Informe valor válido com até duas casas decimais.')

def initialize(c):
    c.executescript('''CREATE TABLE IF NOT EXISTS cash_sessions424(
        id INTEGER PRIMARY KEY,professional_id INTEGER NOT NULL REFERENCES professionals(id),
        opened_by INTEGER NOT NULL,opened_at TEXT NOT NULL,opening_cents INTEGER NOT NULL CHECK(opening_cents>=0),
        token TEXT NOT NULL,closed_at TEXT,closed_by INTEGER,counted_cents INTEGER,reason TEXT NOT NULL DEFAULT '',snapshot TEXT,
        UNIQUE(professional_id,token));
    CREATE UNIQUE INDEX IF NOT EXISTS cash_one_open424 ON cash_sessions424(professional_id) WHERE closed_at IS NULL;
    CREATE TABLE IF NOT EXISTS cash_moves424(id INTEGER PRIMARY KEY,session_id INTEGER NOT NULL REFERENCES cash_sessions424(id),
        kind TEXT NOT NULL CHECK(kind IN ('withdrawal','supply')),cents INTEGER NOT NULL CHECK(cents>0),actor_id INTEGER NOT NULL,
        reason TEXT NOT NULL,created_at TEXT NOT NULL,token TEXT NOT NULL,UNIQUE(session_id,token));
    CREATE TABLE IF NOT EXISTS cash_refunds424(id INTEGER PRIMARY KEY,session_id INTEGER NOT NULL REFERENCES cash_sessions424(id),kind TEXT NOT NULL,source_id INTEGER NOT NULL,method TEXT NOT NULL,cents INTEGER NOT NULL CHECK(cents>0),actor_id INTEGER NOT NULL,reason TEXT NOT NULL,created_at TEXT NOT NULL,token TEXT NOT NULL,UNIQUE(session_id,token));
    CREATE TABLE IF NOT EXISTS cash_sources424(kind TEXT NOT NULL,source_id INTEGER NOT NULL,
        session_id INTEGER NOT NULL REFERENCES cash_sessions424(id),PRIMARY KEY(kind,source_id));''')
    c.commit()

def guard_manual(c,sid):
    # init_db-based legacy fixtures may not have run all startup callbacks yet.
    if not c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cash_sources424'").fetchone():return
    if c.execute("SELECT 1 FROM cash_sources424 WHERE kind='manual' AND source_id=?",(sid,)).fetchone():
        raise HTTPException(409,'Venda incluída em caixa fechado. O fechamento e seus pagamentos estão protegidos.')
    if c.execute("SELECT 1 FROM cash_refunds424 r JOIN manual_payments107 p ON p.id=r.source_id WHERE r.kind='payment' AND p.sale_id=?",(sid,)).fetchone():raise HTTPException(409,'Venda com devolução registrada; preserve o histórico financeiro.')

def summary(c,s):
    if s['closed_at']:return json.loads(s['snapshot'])
    start=s['opened_at'];pid=s['professional_id'];payments={k:0 for k in METHODS};sales=[]
    orders=c.execute("""SELECT o.*,COALESCE((SELECT MAX(h.created_at) FROM order_status_history h WHERE h.order_id=o.id AND h.status='completed'),o.updated_at,o.created_at) sold_at
        FROM orders o WHERE o.professional_id=? AND o.status='completed' AND NOT EXISTS(SELECT 1 FROM cash_sources424 x WHERE x.kind='order' AND x.source_id=o.id)""",(pid,)).fetchall()
    for o in orders:
        if o['sold_at']<start:continue
        if o['payment_method'] not in METHODS:raise HTTPException(409,'Há pedido entregue sem forma de pagamento efetiva. Confira o pedido '+str(o['id'])+'.')
        payments[o['payment_method']]+=o['total_cents']
        sales.append(dict(kind='order',source_id=o['id'],code=o['order_code'] or str(o['id']),cents=o['total_cents']))
    for r in c.execute("SELECT * FROM manual_sales107 WHERE professional_id=? AND status='completed' AND closed_at>=? AND NOT EXISTS(SELECT 1 FROM cash_sources424 x WHERE x.kind='manual' AND x.source_id=manual_sales107.id)",(pid,start)):
        sales.append(dict(kind='manual',source_id=r['id'],code='CX-'+str(r['id']),cents=r['total_cents'],payments=[dict(payment) for payment in c.execute('SELECT id,method,cents FROM manual_payments107 WHERE sale_id=? ORDER BY id',(r['id'],))]))
    # Manual money is recognized when received, even if the account remains open.
    # Closing is blocked until all such accounts are completed/cancelled.
    for r in c.execute("SELECT p.method,SUM(p.cents) cents FROM manual_payments107 p JOIN manual_sales107 s ON s.id=p.sale_id WHERE s.professional_id=? AND p.created_at>=? AND s.status!='cancelled' GROUP BY p.method",(pid,start)):
        payments[r['method']]+=r['cents']
    for r in c.execute("SELECT p.method,SUM(p.cents) cents FROM manual_payments107 p JOIN manual_sales107 s ON s.id=p.sale_id WHERE s.professional_id=? AND s.status='cancelled' AND s.refund_recorded=1 AND s.closed_at>=? AND p.created_at<? GROUP BY p.method",(pid,start,start)):
        payments[r['method']]-=r['cents']
    refunds=[dict(r) for r in c.execute('SELECT * FROM cash_refunds424 WHERE session_id=? ORDER BY id',(s['id'],))]
    for refund in refunds:payments[refund['method']]-=refund['cents']
    moves=[dict(r) for r in c.execute('SELECT * FROM cash_moves424 WHERE session_id=? ORDER BY id',(s['id'],))]
    supply=sum(r['cents'] for r in moves if r['kind']=='supply');withdraw=sum(r['cents'] for r in moves if r['kind']=='withdrawal')
    pending=[dict(r) for r in c.execute("SELECT id,order_code label FROM orders WHERE professional_id=? AND status NOT IN ('completed','cancelled','rejected','whatsapp_finalized')",(pid,))]
    pending += [dict(r) for r in c.execute("SELECT -id id,label FROM manual_sales107 WHERE professional_id=? AND status='open'",(pid,))]
    return dict(payments=payments,sales=sales,sales_count=len(sales),sales_cents=sum(r['cents'] for r in sales),
        moves=moves,refunds=refunds,supply_cents=supply,withdrawal_cents=withdraw,expected_cents=s['opening_cents']+payments['cash']+supply-withdraw,pending=pending)

def install(g):
    app=g['app'];db=g['db']
    def startup():
        c=db()
        try:first=not c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cash_sessions424'").fetchone()
        finally:c.close()
        if first:
            import nowup_backup
            if not nowup_backup.missing_config():
                # Existing encrypted storage, native PG dump and remote checksum
                # verification. Failure stops this rollout before cash migration.
                nowup_backup.external_backup()
        c=db()
        try:
            initialize(c)
            if getattr(c,'dialect','sqlite')=='postgres':
                from nowup_database239 import finalize_postgres_constraints
                finalize_postgres_constraints(c);c.commit()
            import logging
            logging.getLogger('uvicorn.error').info('NowUp cash424 schema ready backend=%s',getattr(c,'dialect','sqlite'))
        finally:c.close()
    app.router.add_event_handler('startup',startup)
    def actor(c,request):
        u=g['require_user'](request,'professional')
        p=c.execute('SELECT * FROM professionals WHERE user_id=? AND blocked=0',(u['id'],)).fetchone()
        if not p:raise HTTPException(403,'Loja indisponível.')
        return u,p
    def owned(c,pid,sid):
        s=c.execute('SELECT * FROM cash_sessions424 WHERE id=? AND professional_id=?',(sid,pid)).fetchone()
        if not s:raise HTTPException(404,'Caixa não encontrado.')
        return dict(s)
    def go(sid):return RedirectResponse('/painel/caixa?caixa='+str(sid),303)
    @app.get('/painel/caixa')
    def page(request:Request,caixa:int=0):
        c=db()
        try:
            c.execute('BEGIN IMMEDIATE');u,p=actor(c,request)
            history=[dict(r) for r in c.execute('SELECT * FROM cash_sessions424 WHERE professional_id=? ORDER BY id DESC LIMIT 50',(p['id'],))]
            s=owned(c,p['id'],caixa) if caixa else (history[0] if history else None)
            report=summary(c,s) if s else None
            for row in history+([s] if s else []):
                row['opened_label']=datetime.fromisoformat(row['opened_at']).astimezone(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')
                row['closed_label']=datetime.fromisoformat(row['closed_at']).astimezone(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M') if row['closed_at'] else ''
            return g['templates'].TemplateResponse('cash424.html',g['context'](request,pro=p,cash=s,report=report,history=history,methods=METHODS,cardapio_panel408=True,token=secrets.token_urlsafe(24)),headers={'Cache-Control':'private, no-store'})
        finally:c.close()
    @app.post('/painel/caixa/abrir')
    def opening(request:Request,initial:str=Form('0'),token:str=Form(...)):
        cents=money(initial,True)
        if not 16<=len(token)<=100:raise HTTPException(400,'Identificador inválido.')
        c=db()
        try:
            c.execute('BEGIN IMMEDIATE');u,p=actor(c,request)
            old=c.execute('SELECT id,opening_cents FROM cash_sessions424 WHERE professional_id=? AND token=?',(p['id'],token)).fetchone()
            if old:
                if old['opening_cents']!=cents:raise HTTPException(409,'Abertura já registrada com outro valor.')
                return go(old['id'])
            if c.execute('SELECT 1 FROM cash_sessions424 WHERE professional_id=? AND closed_at IS NULL',(p['id'],)).fetchone():raise HTTPException(409,'Já há um caixa aberto.')
            sid=c.execute('INSERT INTO cash_sessions424(professional_id,opened_by,opened_at,opening_cents,token) VALUES(?,?,?,?,?)',(p['id'],u['id'],stamp(),cents,token)).lastrowid
            c.commit();return go(sid)
        finally:c.close()
    @app.post('/painel/caixa/{sid}/movimento')
    def movement(request:Request,sid:int,kind:str=Form(...),value:str=Form(...),reason:str=Form(...),token:str=Form(...)):
        cents=money(value)
        if kind not in ('withdrawal','supply') or not reason.strip() or not 16<=len(token)<=100:raise HTTPException(400,'Confira tipo, motivo e identificador.')
        c=db()
        try:
            c.execute('BEGIN IMMEDIATE');u,p=actor(c,request);s=owned(c,p['id'],sid)
            old=c.execute('SELECT * FROM cash_moves424 WHERE session_id=? AND token=?',(sid,token)).fetchone()
            if old:
                if (old['kind'],old['cents'],old['reason'])!=(kind,cents,reason.strip()[:500]):raise HTTPException(409,'Movimento já registrado com outros dados.')
                return go(sid)
            if s['closed_at']:raise HTTPException(409,'Caixa fechado.')
            if kind=='withdrawal' and cents>summary(c,s)['expected_cents']:raise HTTPException(400,'Sangria maior que o dinheiro disponível.')
            c.execute('INSERT INTO cash_moves424(session_id,kind,cents,actor_id,reason,created_at,token) VALUES(?,?,?,?,?,?,?)',(sid,kind,cents,u['id'],reason.strip()[:500],stamp(),token));c.commit();return go(sid)
        finally:c.close()
    @app.post('/painel/caixa/{sid}/devolver')
    def refund(request:Request,sid:int,kind:str=Form(...),source_id:int=Form(...),value:str=Form(...),reason:str=Form(...),token:str=Form(...)):
        cents=money(value)
        if kind not in ('order','payment') or not reason.strip() or not 16<=len(token)<=100:raise HTTPException(400,'Confira origem, motivo e identificador.')
        c=db()
        try:
            c.execute('BEGIN IMMEDIATE');u,p=actor(c,request);s=owned(c,p['id'],sid)
            old=c.execute('SELECT * FROM cash_refunds424 WHERE session_id=? AND token=?',(sid,token)).fetchone()
            if old:
                if (old['kind'],old['source_id'],old['cents'])!=(kind,source_id,cents):raise HTTPException(409,'Devolução já registrada com outros dados.')
                return go(sid)
            if s['closed_at']:raise HTTPException(409,'Abra uma sessão para registrar a devolução sem alterar o caixa anterior.')
            if kind=='order':
                receipt=c.execute("SELECT payment_method method,total_cents cents FROM orders WHERE id=? AND professional_id=? AND status='completed'",(source_id,p['id'])).fetchone()
            else:
                receipt=c.execute("SELECT p.method,p.cents FROM manual_payments107 p JOIN manual_sales107 s ON s.id=p.sale_id WHERE p.id=? AND s.professional_id=? AND s.status='completed'",(source_id,p['id'])).fetchone()
            if not receipt or receipt['method'] not in METHODS:raise HTTPException(404,'Recebimento de venda concluída não encontrado nesta loja.')
            returned=c.execute('SELECT COALESCE(SUM(cents),0) FROM cash_refunds424 WHERE kind=? AND source_id=?',(kind,source_id)).fetchone()[0]
            if returned+cents>receipt['cents']:raise HTTPException(400,'Devolução maior que o saldo do recebimento original.')
            if receipt['method']=='cash' and cents>summary(c,s)['expected_cents']:raise HTTPException(400,'Dinheiro insuficiente para esta devolução.')
            c.execute('INSERT INTO cash_refunds424(session_id,kind,source_id,method,cents,actor_id,reason,created_at,token) VALUES(?,?,?,?,?,?,?,?,?)',(sid,kind,source_id,receipt['method'],cents,u['id'],reason.strip()[:500],stamp(),token));c.commit();return go(sid)
        finally:c.close()
    @app.post('/painel/caixa/{sid}/fechar')
    def closing(request:Request,sid:int,counted:str=Form(...),reason:str=Form('')):
        cents=money(counted,True);c=db()
        try:
            c.execute('BEGIN IMMEDIATE');u,p=actor(c,request);s=owned(c,p['id'],sid)
            if s['closed_at']:raise HTTPException(409,'Caixa já fechado.')
            data=summary(c,s)
            if data['pending']:raise HTTPException(409,'Finalize ou cancele os pedidos e comandas em aberto antes de fechar o caixa.')
            data.update(counted_cents=cents,difference_cents=cents-data['expected_cents'])
            if data['difference_cents'] and not reason.strip():raise HTTPException(400,'Justifique a diferença de caixa.')
            for source in data['sales']:c.execute('INSERT INTO cash_sources424(kind,source_id,session_id) VALUES(?,?,?)',(source['kind'],source['source_id'],sid))
            c.execute('UPDATE cash_sessions424 SET closed_at=?,closed_by=?,counted_cents=?,reason=?,snapshot=? WHERE id=? AND closed_at IS NULL',(stamp(),u['id'],cents,reason.strip()[:500],json.dumps(data,ensure_ascii=False),sid))
            c.commit();return go(sid)
        finally:c.close()
