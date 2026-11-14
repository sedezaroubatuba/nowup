"""Transactional cash sessions and optional unit stock. SQLite migration is additive."""
import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo
from fastapi import HTTPException, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse

METHODS = {'cash': 'Dinheiro', 'pix': 'Pix', 'credit': 'Crédito', 'debit': 'Débito'}
ACTIVE = "'new','reviewing','awaiting_approval','revision_approved','confirmed','preparing','ready','out_for_delivery'"


def stamp():
    return datetime.now(timezone.utc).isoformat()


def amount(raw, zero=False):
    try:
        value = Decimal(str(raw).strip().replace(',', '.'))
        if not value.is_finite() or value < 0 or (not zero and value == 0) or value > 1000000 or value.as_tuple().exponent < -2:
            raise ValueError()
        return int(value * 100)
    except (InvalidOperation, ValueError, TypeError):
        raise HTTPException(400, 'Informe um valor válido com até duas casas decimais.')


def initialize(c):
    for table, column, definition in [('orders', 'cash_session256', 'INTEGER'), ('manual_sales107', 'cash_session256', 'INTEGER'), ('products', 'stock256', 'INTEGER CHECK(stock256 IS NULL OR stock256>=0)')]:
        if column not in {r[1] for r in c.execute('PRAGMA table_info('+table+')')}:
            c.execute('ALTER TABLE '+table+' ADD COLUMN '+column+' '+definition)
    c.executescript('''
    CREATE TABLE IF NOT EXISTS cash_sessions256(
      id INTEGER PRIMARY KEY, professional_id INTEGER NOT NULL REFERENCES professionals(id),
      opened_by INTEGER NOT NULL, opened_at TEXT NOT NULL, opening_cents INTEGER NOT NULL CHECK(opening_cents>=0),
      closed_at TEXT, closed_by INTEGER, counted_cents INTEGER, reason TEXT NOT NULL DEFAULT '', snapshot TEXT,
      open_token TEXT NOT NULL, UNIQUE(professional_id,open_token));
    CREATE UNIQUE INDEX IF NOT EXISTS cash_one_open256 ON cash_sessions256(professional_id) WHERE closed_at IS NULL;
    CREATE TABLE IF NOT EXISTS cash_entries256(
      id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES cash_sessions256(id),
      method TEXT NOT NULL CHECK(method IN ('cash','pix','credit','debit')), cents INTEGER NOT NULL,
      kind TEXT NOT NULL, source TEXT NOT NULL UNIQUE, reason TEXT NOT NULL DEFAULT '', actor_id INTEGER,
      created_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS cash_entries_session256 ON cash_entries256(session_id);
    CREATE TABLE IF NOT EXISTS cash_sales256(
      id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES cash_sessions256(id),
      source TEXT NOT NULL UNIQUE, cents INTEGER NOT NULL CHECK(cents>0), created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS cash_adjustments256(id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES cash_sessions256(id), receipt_id INTEGER NOT NULL REFERENCES cash_entries256(id), cents INTEGER NOT NULL CHECK(cents>0), token TEXT NOT NULL UNIQUE);
    CREATE TABLE IF NOT EXISTS stock_events256(
      id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL, actor_id INTEGER NOT NULL,
      before_quantity INTEGER, after_quantity INTEGER, created_at TEXT NOT NULL);
    CREATE TRIGGER IF NOT EXISTS cash_closed_update256 BEFORE UPDATE ON cash_sessions256 WHEN OLD.closed_at IS NOT NULL
      BEGIN SELECT RAISE(ABORT,'Caixa fechado: registro protegido.'); END;
    CREATE TRIGGER IF NOT EXISTS cash_closed_delete256 BEFORE DELETE ON cash_sessions256
      BEGIN SELECT RAISE(ABORT,'Caixa: registro protegido.'); END;
    CREATE TRIGGER IF NOT EXISTS cash_entry_insert256 BEFORE INSERT ON cash_entries256
      WHEN NOT EXISTS(SELECT 1 FROM cash_sessions256 WHERE id=NEW.session_id AND closed_at IS NULL)
      BEGIN SELECT RAISE(ABORT,'Caixa fechado.'); END;
    CREATE TRIGGER IF NOT EXISTS cash_entry_update256 BEFORE UPDATE ON cash_entries256
      BEGIN SELECT RAISE(ABORT,'Lançamento protegido.'); END;
    CREATE TRIGGER IF NOT EXISTS cash_entry_delete256 BEFORE DELETE ON cash_entries256
      BEGIN SELECT RAISE(ABORT,'Lançamento protegido.'); END;
    CREATE TRIGGER IF NOT EXISTS cash_sale_insert256 BEFORE INSERT ON cash_sales256
      WHEN NOT EXISTS(SELECT 1 FROM cash_sessions256 WHERE id=NEW.session_id AND closed_at IS NULL)
      BEGIN SELECT RAISE(ABORT,'Caixa fechado.'); END;
    CREATE TRIGGER IF NOT EXISTS cash_sale_update256 BEFORE UPDATE ON cash_sales256
      BEGIN SELECT RAISE(ABORT,'Venda protegida.'); END;
    CREATE TRIGGER IF NOT EXISTS cash_sale_delete256 BEFORE DELETE ON cash_sales256
      BEGIN SELECT RAISE(ABORT,'Venda protegida.'); END;
    ''')
    for table, kind in [('orders', 'order'), ('manual_sales107', 'manual')]:
        c.executescript(f'''
        CREATE TRIGGER IF NOT EXISTS cash_assign_{kind}256 AFTER INSERT ON {table}
        BEGIN UPDATE {table} SET cash_session256=(SELECT id FROM cash_sessions256 WHERE professional_id=NEW.professional_id AND closed_at IS NULL) WHERE id=NEW.id; END;
        CREATE TRIGGER IF NOT EXISTS cash_lock_{kind}256 BEFORE UPDATE ON {table}
        WHEN OLD.cash_session256 IS NOT NULL AND EXISTS(SELECT 1 FROM cash_sessions256 WHERE id=OLD.cash_session256 AND closed_at IS NOT NULL)
        BEGIN SELECT RAISE(ABORT,'Pedido vinculado a caixa fechado.'); END;
        CREATE TRIGGER IF NOT EXISTS cash_no_delete_{kind}256 BEFORE DELETE ON {table} WHEN OLD.cash_session256 IS NOT NULL
        BEGIN SELECT RAISE(ABORT,'Venda vinculada ao caixa: registro protegido.'); END;
        CREATE TRIGGER IF NOT EXISTS cash_fixed_session_{kind}256 BEFORE UPDATE OF cash_session256 ON {table}
        WHEN OLD.cash_session256 IS NOT NULL AND NEW.cash_session256 IS NOT OLD.cash_session256
        BEGIN SELECT RAISE(ABORT,'Vínculo de caixa protegido.'); END;
        ''')
    c.executescript('''
    CREATE TRIGGER IF NOT EXISTS cash_order_complete256 AFTER UPDATE OF status ON orders
    WHEN NEW.status='completed' AND OLD.status!='completed' AND NEW.cash_session256 IS NOT NULL
    BEGIN
      SELECT CASE WHEN NEW.payment_method NOT IN ('cash','pix','credit','debit') THEN RAISE(ABORT,'Informe a forma de pagamento efetiva antes de concluir.') END;
      INSERT INTO cash_sales256(session_id,source,cents,created_at) VALUES(NEW.cash_session256,'order:'||NEW.id,NEW.total_cents,NEW.updated_at);
      INSERT INTO cash_entries256(session_id,method,cents,kind,source,created_at) VALUES(NEW.cash_session256,NEW.payment_method,NEW.total_cents,'payment','order:'||NEW.id,NEW.updated_at);
    END;
    CREATE TRIGGER IF NOT EXISTS cash_manual_complete256 AFTER UPDATE OF status ON manual_sales107
    WHEN NEW.status='completed' AND OLD.status!='completed' AND NEW.cash_session256 IS NOT NULL
    BEGIN INSERT INTO cash_sales256(session_id,source,cents,created_at) VALUES(NEW.cash_session256,'manual:'||NEW.id,NEW.total_cents,NEW.updated_at); END;
    CREATE TRIGGER IF NOT EXISTS cash_manual_no_reverse256 BEFORE UPDATE ON manual_sales107
    WHEN OLD.status='completed' AND OLD.cash_session256 IS NOT NULL
    BEGIN SELECT RAISE(ABORT,'Venda concluída no caixa: use ajuste identificado, sem editar o histórico.'); END;
    CREATE TRIGGER IF NOT EXISTS cash_manual_payment256 AFTER INSERT ON manual_payments107
    WHEN (SELECT cash_session256 FROM manual_sales107 WHERE id=NEW.sale_id) IS NOT NULL
    BEGIN INSERT INTO cash_entries256(session_id,method,cents,kind,source,created_at)
      SELECT cash_session256,NEW.method,NEW.cents,'payment','manual-payment:'||NEW.id||':'||lower(hex(randomblob(8))),NEW.created_at FROM manual_sales107 WHERE id=NEW.sale_id; END;
    CREATE TRIGGER IF NOT EXISTS cash_manual_payment_delete256 BEFORE DELETE ON manual_payments107
    WHEN (SELECT cash_session256 FROM manual_sales107 WHERE id=OLD.sale_id) IS NOT NULL
    BEGIN
      SELECT CASE WHEN (SELECT status FROM manual_sales107 WHERE id=OLD.sale_id)!='open' THEN RAISE(ABORT,'Pagamento de venda encerrada protegido.') END;
      INSERT INTO cash_entries256(session_id,method,cents,kind,source,created_at)
      SELECT cash_session256,OLD.method,-OLD.cents,'correction','remove-payment:'||OLD.id,strftime('%Y-%m-%dT%H:%M:%f+00:00','now') FROM manual_sales107 WHERE id=OLD.sale_id;
    END;
    CREATE TRIGGER IF NOT EXISTS cash_manual_payment_update256 BEFORE UPDATE ON manual_payments107
    BEGIN SELECT RAISE(ABORT,'Corrija o pagamento com motivo, sem sobrescrever o registro.'); END;
    CREATE TRIGGER IF NOT EXISTS cash_manual_refund256 AFTER UPDATE OF status ON manual_sales107
    WHEN NEW.status='cancelled' AND OLD.status!='cancelled' AND NEW.cash_session256 IS NOT NULL
    BEGIN
      INSERT INTO cash_entries256(session_id,method,cents,kind,source,reason,created_at)
      SELECT NEW.cash_session256,method,-cents,'refund','refund-payment:'||id,NEW.cancel_reason,NEW.updated_at FROM manual_payments107 WHERE sale_id=NEW.id;
    END;
    ''')
    # Reservations apply only to newly created items after this migration. Existing
    # items get a null reservation marker and cannot silently consume legacy stock.
    for table in ('order_items', 'manual_items107'):
        if 'reserved256' not in {r[1] for r in c.execute('PRAGMA table_info('+table+')')}:
            c.execute('ALTER TABLE '+table+' ADD COLUMN reserved256 INTEGER NOT NULL DEFAULT 0')
    for items, sales, fk, prefix in [('order_items','orders','order_id','order'),('manual_items107','manual_sales107','sale_id','manual')]:
        c.executescript(f'''
        CREATE TRIGGER IF NOT EXISTS stock_insert_{prefix}256 AFTER INSERT ON {items}
        WHEN NEW.product_id IS NOT NULL AND (SELECT stock256 FROM products WHERE id=NEW.product_id) IS NOT NULL
        BEGIN
          SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM products p JOIN {sales} s ON s.id=NEW.{fk} WHERE p.id=NEW.product_id AND p.professional_id=s.professional_id AND p.available=1 AND p.stock256>=NEW.quantity AND s.status NOT IN ('completed','cancelled','rejected')) THEN RAISE(ABORT,'Estoque insuficiente ou produto indisponível.') END;
          UPDATE products SET stock256=stock256-NEW.quantity WHERE id=NEW.product_id;
          UPDATE {items} SET reserved256=1 WHERE id=NEW.id;
        END;
        CREATE TRIGGER IF NOT EXISTS stock_update_{prefix}256 BEFORE UPDATE OF quantity,product_id ON {items}
        WHEN OLD.reserved256=1
        BEGIN
          SELECT CASE WHEN NEW.product_id IS NOT OLD.product_id THEN RAISE(ABORT,'Substitua o item pela revisão do pedido.') END;
          SELECT CASE WHEN (SELECT status FROM {sales} WHERE id=OLD.{fk}) IN ('completed','cancelled','rejected') THEN RAISE(ABORT,'Estoque de pedido encerrado protegido.') END;
          SELECT CASE WHEN (SELECT stock256 FROM products WHERE id=OLD.product_id)<NEW.quantity-OLD.quantity THEN RAISE(ABORT,'Estoque insuficiente.') END;
          UPDATE products SET stock256=stock256+OLD.quantity-NEW.quantity WHERE id=OLD.product_id;
        END;
        CREATE TRIGGER IF NOT EXISTS stock_delete_{prefix}256 BEFORE DELETE ON {items} WHEN OLD.reserved256=1
        BEGIN
          SELECT CASE WHEN (SELECT status FROM {sales} WHERE id=OLD.{fk}) IN ('completed','cancelled','rejected') THEN RAISE(ABORT,'Estoque de pedido encerrado protegido.') END;
          UPDATE products SET stock256=stock256+OLD.quantity WHERE id=OLD.product_id;
        END;
        CREATE TRIGGER IF NOT EXISTS stock_cancel_{prefix}256 AFTER UPDATE OF status ON {sales}
        WHEN NEW.status IN ('cancelled','rejected') AND OLD.status NOT IN ('cancelled','rejected','completed')
        BEGIN
          UPDATE products SET stock256=stock256+(SELECT COALESCE(SUM(quantity),0) FROM {items} WHERE {fk}=NEW.id AND product_id=products.id AND reserved256=1) WHERE id IN (SELECT product_id FROM {items} WHERE {fk}=NEW.id AND reserved256=1);
          UPDATE {items} SET reserved256=0 WHERE {fk}=NEW.id;
        END;
        CREATE TRIGGER IF NOT EXISTS cash_item_update_{prefix}256 BEFORE UPDATE OF quantity,unit_price_cents ON {items}
        WHEN EXISTS(SELECT 1 FROM {sales} s JOIN cash_sessions256 c ON c.id=s.cash_session256 WHERE s.id=OLD.{fk} AND (s.status IN ('completed','cancelled','rejected') OR c.closed_at IS NOT NULL))
        BEGIN SELECT RAISE(ABORT,'Item financeiro protegido.'); END;
        CREATE TRIGGER IF NOT EXISTS cash_item_insert_{prefix}256 BEFORE INSERT ON {items}
        WHEN EXISTS(SELECT 1 FROM {sales} s JOIN cash_sessions256 c ON c.id=s.cash_session256 WHERE s.id=NEW.{fk} AND (s.status IN ('completed','cancelled','rejected') OR c.closed_at IS NOT NULL))
        BEGIN SELECT RAISE(ABORT,'Item financeiro protegido.'); END;
        CREATE TRIGGER IF NOT EXISTS cash_item_delete_{prefix}256 BEFORE DELETE ON {items}
        WHEN EXISTS(SELECT 1 FROM {sales} s JOIN cash_sessions256 c ON c.id=s.cash_session256 WHERE s.id=OLD.{fk} AND (s.status IN ('completed','cancelled','rejected') OR c.closed_at IS NOT NULL))
        BEGIN SELECT RAISE(ABORT,'Item financeiro protegido.'); END;
        ''')
    c.executescript("""
    CREATE TRIGGER IF NOT EXISTS stock_product_delete256 BEFORE DELETE ON products WHEN EXISTS(SELECT 1 FROM order_items i JOIN orders o ON o.id=i.order_id WHERE i.product_id=OLD.id AND i.reserved256=1 AND o.status NOT IN ('completed','cancelled','rejected')) OR EXISTS(SELECT 1 FROM manual_items107 i JOIN manual_sales107 s ON s.id=i.sale_id WHERE i.product_id=OLD.id AND i.reserved256=1 AND s.status='open')
    BEGIN SELECT RAISE(ABORT,'Produto com reserva de estoque: finalize os pedidos antes de excluir.'); END;
    CREATE TRIGGER IF NOT EXISTS order_terminal256 BEFORE UPDATE ON orders WHEN OLD.status IN ('completed','cancelled','rejected') AND (NEW.status!=OLD.status OR NEW.total_cents!=OLD.total_cents OR NEW.payment_method!=OLD.payment_method OR NEW.professional_id!=OLD.professional_id OR NEW.subtotal_cents!=OLD.subtotal_cents OR NEW.delivery_fee_cents!=OLD.delivery_fee_cents)
    BEGIN SELECT RAISE(ABORT,'Pedido encerrado: valores e status protegidos.'); END;
    CREATE TRIGGER IF NOT EXISTS order_transition256 BEFORE UPDATE OF status ON orders WHEN NEW.status!=OLD.status AND NOT (
      (NEW.status IN ('cancelled','rejected') AND OLD.status NOT IN ('completed','cancelled','rejected')) OR
      (OLD.status IN ('new','reviewing','revision_approved') AND NEW.status IN ('reviewing','confirmed','awaiting_approval')) OR
      (OLD.status='awaiting_approval' AND NEW.status IN ('revision_approved','reviewing')) OR
      (OLD.status='confirmed' AND NEW.status='preparing') OR
      (OLD.status='preparing' AND NEW.status='ready') OR
      (OLD.status='ready' AND ((NEW.fulfillment_type='delivery' AND NEW.status='out_for_delivery') OR (NEW.fulfillment_type='pickup' AND NEW.status='completed'))) OR
      (OLD.status='out_for_delivery' AND NEW.status='completed'))
    BEGIN SELECT RAISE(ABORT,'Mudança de status inválida.'); END;
    """)
    c.commit()


def session(c, pid, sid):
    row = c.execute('SELECT * FROM cash_sessions256 WHERE id=? AND professional_id=?', (sid,pid)).fetchone()
    if not row:
        raise HTTPException(404, 'Caixa não encontrado.')
    return dict(row)


def summary(c, s):
    if s['closed_at']:
        return json.loads(s['snapshot'])
    payments = {m: 0 for m in METHODS}
    for row in c.execute("SELECT method,SUM(cents) cents FROM cash_entries256 WHERE session_id=? AND kind NOT IN ('withdrawal','supply') GROUP BY method", (s['id'],)):
        payments[row['method']] = row['cents']
    movements = {r['kind']: r['cents'] for r in c.execute("SELECT kind,SUM(cents) cents FROM cash_entries256 WHERE session_id=? AND kind IN ('withdrawal','supply') GROUP BY kind", (s['id'],))}
    sales = c.execute('SELECT COUNT(*),COALESCE(SUM(cents),0) FROM cash_sales256 WHERE session_id=?', (s['id'],)).fetchone()
    expected = s['opening_cents'] + payments['cash'] + sum(movements.values())
    pending = [dict(r) for r in c.execute(f"SELECT id,order_code label,total_cents FROM orders WHERE cash_session256=? AND status IN ({ACTIVE})", (s['id'],))]
    pending += [dict(r) for r in c.execute("SELECT -id id,label,total_cents FROM manual_sales107 WHERE cash_session256=? AND status='open'", (s['id'],))]
    return dict(payments=payments, movements=movements, sales_count=sales[0], sales_cents=sales[1], expected_cents=expected, pending=pending, entries=[dict(r) for r in c.execute('SELECT * FROM cash_entries256 WHERE session_id=? ORDER BY id',(s['id'],))])


def install(g):
    app, db, auth = g['app'], g['db'], g['require_user']
    def startup():
        c=db()
        try: initialize(c)
        finally: c.close()
    app.add_event_handler('startup', startup)

    @app.exception_handler(sqlite3.IntegrityError)
    async def constraint_error(request, exc):
        # Do not expose database/table details or user-supplied SQL.
        return JSONResponse({'detail':'Operação não concluída. Confira estoque, pagamento e situação do caixa; atualize antes de tentar novamente.'},status_code=409)

    def actor(c, request):
        u=g['require_user'](request,'professional')
        p=c.execute('SELECT * FROM professionals WHERE user_id=? AND blocked=0',(u['id'],)).fetchone()
        if not p: raise HTTPException(403,'Loja indisponível.')
        return u,p

    @app.get('/painel/caixa')
    def page(request: Request, caixa: int=0):
        c=db()
        try:
            u,p=actor(c,request)
            rows=[dict(r) for r in c.execute('SELECT * FROM cash_sessions256 WHERE professional_id=? ORDER BY id DESC LIMIT 50',(p['id'],))]
            s=session(c,p['id'],caixa) if caixa else (rows[0] if rows else None)
            def local_label(raw):return datetime.fromisoformat(raw).astimezone(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M') if raw else ''
            for row in rows:
                row['opened_label']=local_label(row['opened_at'])
            if s:
                s['opened_label']=local_label(s['opened_at']);s['closed_label']=local_label(s['closed_at'])
            data=summary(c,s) if s else None
            legacy=c.execute("SELECT COUNT(*) FROM orders WHERE professional_id=? AND status='completed' AND cash_session256 IS NULL",(p['id'],)).fetchone()[0]
            return g['templates'].TemplateResponse('cash256.html',g['context'](request,pro=p,cash=s,report=data,history=rows,methods=METHODS,legacy=legacy,token=g['secrets'].token_urlsafe(24)),headers={'Cache-Control':'private, no-store'})
        finally: c.close()

    @app.post('/painel/caixa/abrir')
    def open_cash(request: Request, initial: str=Form('0'), token: str=Form(...)):
        cents=amount(initial,zero=True)
        if not 16<=len(token)<=100: raise HTTPException(400,'Identificador inválido.')
        c=db()
        try:
            c.execute('BEGIN IMMEDIATE');u,p=actor(c,request)
            old=c.execute('SELECT id,opening_cents FROM cash_sessions256 WHERE professional_id=? AND open_token=?',(p['id'],token)).fetchone()
            if old:
                if old['opening_cents']!=cents:raise HTTPException(409,'Identificador de abertura já usado com outro saldo.')
                sid=old['id']
            else:
                if c.execute('SELECT 1 FROM cash_sessions256 WHERE professional_id=? AND closed_at IS NULL',(p['id'],)).fetchone(): raise HTTPException(409,'Já existe um caixa aberto.')
                sid=c.execute('INSERT INTO cash_sessions256(professional_id,opened_by,opened_at,opening_cents,open_token) VALUES(?,?,?,?,?)',(p['id'],u['id'],stamp(),cents,token)).lastrowid
            c.commit()
            return RedirectResponse('/painel/caixa?caixa='+str(sid),303)
        finally: c.close()

    @app.post('/painel/caixa/{sid}/movimento')
    def movement(request: Request, sid: int, kind: str=Form(...), value: str=Form(...), reason: str=Form(...), token: str=Form(...)):
        cents=amount(value)
        if kind not in ('withdrawal','supply') or not reason.strip() or not 16<=len(token)<=100: raise HTTPException(400,'Informe tipo, motivo e identificador válidos.')
        c=db()
        try:
            c.execute('BEGIN IMMEDIATE');u,p=actor(c,request);s=session(c,p['id'],sid)
            source='movement:'+str(sid)+':'+token
            old=c.execute('SELECT * FROM cash_entries256 WHERE source=?',(source,)).fetchone()
            signed=-cents if kind=='withdrawal' else cents
            if old:
                if (old['cents'],old['kind'],old['reason'])!=(signed,kind,reason.strip()[:500]): raise HTTPException(409,'Identificador já usado com outros dados.')
            else:
                if s['closed_at']: raise HTTPException(409,'Caixa fechado.')
                if kind=='withdrawal' and cents>summary(c,s)['expected_cents']: raise HTTPException(400,'Sangria maior que o dinheiro disponível.')
                c.execute('INSERT INTO cash_entries256(session_id,method,cents,kind,source,reason,actor_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(sid,'cash',signed,kind,source,reason.strip()[:500],u['id'],stamp()))
            c.commit();return RedirectResponse('/painel/caixa?caixa='+str(sid),303)
        finally: c.close()

    @app.post('/painel/caixa/{sid}/fechar')
    def close_cash(request: Request, sid: int, counted: str=Form(...), reason: str=Form('')):
        cents=amount(counted,zero=True);c=db()
        try:
            c.execute('BEGIN IMMEDIATE');u,p=actor(c,request);s=session(c,p['id'],sid)
            if s['closed_at']: raise HTTPException(409,'Caixa já fechado.')
            data=summary(c,s)
            if data['pending']: raise HTTPException(409,'Há pedidos ou comandas em aberto neste caixa. Confira a lista antes de fechar.')
            data['counted_cents']=cents;data['difference_cents']=cents-data['expected_cents']
            if data['difference_cents'] and not reason.strip(): raise HTTPException(400,'Informe o motivo da diferença de caixa.')
            data['entries']=[dict(r) for r in c.execute('SELECT * FROM cash_entries256 WHERE session_id=? ORDER BY id',(sid,))]
            data['sales']=[dict(r) for r in c.execute('SELECT * FROM cash_sales256 WHERE session_id=? ORDER BY id',(sid,))]
            c.execute('UPDATE cash_sessions256 SET closed_at=?,closed_by=?,counted_cents=?,reason=?,snapshot=? WHERE id=?',(stamp(),u['id'],cents,reason.strip()[:500],json.dumps(data,ensure_ascii=False),sid));c.commit()
            return RedirectResponse('/painel/caixa?caixa='+str(sid),303)
        finally: c.close()

    @app.post('/painel/caixa/{sid}/devolver')
    def refund(request: Request, sid: int, receipt_id: int=Form(...), value: str=Form(...), reason: str=Form(...), token: str=Form(...)):
        cents=amount(value)
        if not reason.strip() or not 16<=len(token)<=100:raise HTTPException(400,'Informe motivo e identificador válidos.')
        c=db()
        try:
            c.execute('BEGIN IMMEDIATE');u,p=actor(c,request);s=session(c,p['id'],sid)
            receipt=c.execute("SELECT e.* FROM cash_entries256 e JOIN cash_sessions256 s ON s.id=e.session_id WHERE e.id=? AND s.professional_id=? AND e.kind='payment' AND e.cents>0",(receipt_id,p['id'])).fetchone()
            if not receipt:raise HTTPException(404,'Recebimento não encontrado nesta loja.')
            source='adjustment:'+str(sid)+':'+token
            old=c.execute('SELECT * FROM cash_adjustments256 WHERE token=?',(source,)).fetchone()
            if old:
                if (old['receipt_id'],old['cents'])!=(receipt_id,cents):raise HTTPException(409,'Identificador já usado com outros dados.')
                return RedirectResponse('/painel/caixa?caixa='+str(sid),303)
            if s['closed_at']:raise HTTPException(409,'Abra uma sessão para registrar a devolução sem alterar o caixa anterior.')
            if receipt['source'].startswith('manual-payment:'):
                pay_id=int(receipt['source'].split(':')[1])
                paid_sale=c.execute("SELECT s.status FROM manual_payments107 p JOIN manual_sales107 s ON s.id=p.sale_id WHERE p.id=? AND p.created_at=? AND p.method=? AND p.cents=?",(pay_id,receipt['created_at'],receipt['method'],receipt['cents'])).fetchone()
                if not paid_sale or paid_sale['status']!='completed':raise HTTPException(409,'Ajuste permitido apenas para recebimento de venda concluída.')
            returned=c.execute('SELECT COALESCE(SUM(cents),0) FROM cash_adjustments256 WHERE receipt_id=?',(receipt_id,)).fetchone()[0]
            if returned+cents>receipt['cents']:raise HTTPException(400,'Devolução supera o saldo do recebimento original.')
            if receipt['method']=='cash' and cents>summary(c,s)['expected_cents']:raise HTTPException(400,'Dinheiro insuficiente para a devolução.')
            c.execute('INSERT INTO cash_adjustments256(session_id,receipt_id,cents,token) VALUES(?,?,?,?)',(sid,receipt_id,cents,source))
            c.execute('INSERT INTO cash_entries256(session_id,method,cents,kind,source,reason,actor_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(sid,receipt['method'],-cents,'refund',source,'Recebimento #'+str(receipt_id)+': '+reason.strip()[:450],u['id'],stamp()))
            c.commit();return RedirectResponse('/painel/caixa?caixa='+str(sid),303)
        finally:c.close()

    @app.get('/painel/estoque')
    def inventory(request: Request):
        c=db()
        try:
            u,p=actor(c,request)
            products=c.execute('SELECT id,name,stock256 FROM products WHERE professional_id=? ORDER BY name',(p['id'],)).fetchall()
            return g['templates'].TemplateResponse('stock256.html',g['context'](request,pro=p,products=products),headers={'Cache-Control':'private, no-store'})
        finally:c.close()

    @app.post('/painel/estoque/{pid}')
    def inventory_change(request: Request, pid: int, quantity: str=Form(''), previous: str=Form('')):
        c=db()
        try:
            c.execute('BEGIN IMMEDIATE');u,p=actor(c,request)
            product=c.execute('SELECT * FROM products WHERE id=? AND professional_id=?',(pid,p['id'])).fetchone()
            if not product: raise HTTPException(404,'Produto não encontrado.')
            actual='' if product['stock256'] is None else str(product['stock256'])
            if previous!=actual: raise HTTPException(409,'Estoque mudou. Atualize antes de salvar.')
            value=None
            if quantity.strip():
                if not quantity.isascii() or not quantity.isdigit() or len(quantity)>7:raise HTTPException(400,'Informe unidades inteiras entre 0 e 9999999, ou deixe vazio.')
                value=int(quantity)
            # Enabling/disabling or recounting during active sales would make the
            # reservation baseline ambiguous, so require all such sales to finish.
            for items,sales,fk in [('order_items','orders','order_id'),('manual_items107','manual_sales107','sale_id')]:
                if c.execute(f"SELECT 1 FROM {items} i JOIN {sales} s ON s.id=i.{fk} WHERE i.product_id=? AND s.status NOT IN ('completed','cancelled','rejected') LIMIT 1",(pid,)).fetchone(): raise HTTPException(409,'Finalize ou cancele os pedidos deste produto antes de ajustar o estoque.')
            if value is not None:
                config=json.loads(product['customization192'] or '{}')
                if 'sell_by_weight' in product.keys() and product['sell_by_weight']: raise HTTPException(400,'Controle por unidades não se aplica a produtos por peso.')
                if config.get('groups') or config.get('included195'): raise HTTPException(400,'Confira os componentes do combo antes de ativar controle por unidades.')
            c.execute('UPDATE products SET stock256=?,updated_at=? WHERE id=?',(value,stamp(),pid))
            c.execute('INSERT INTO stock_events256(product_id,actor_id,before_quantity,after_quantity,created_at) VALUES(?,?,?,?,?)',(pid,u['id'],product['stock256'],value,stamp()));c.commit()
            return RedirectResponse('/painel/estoque',303)
        finally:c.close()
