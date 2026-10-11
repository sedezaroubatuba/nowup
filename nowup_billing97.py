"""Etapa 1: preparação e simulação isolada. Não processa dinheiro real."""
import calendar
import hmac
import os
import secrets
from datetime import date, datetime, timezone
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

PLANS = {'vitrine': ('Só vitrine', 4990), 'cardapio': ('Só cardápio/catálogo', 4990), 'ambos': ('Vitrine + cardápio/catálogo', 9990)}
LABELS = {'pending':'Aguardando pagamento', 'paid':'Pago', 'overdue':'Em atraso', 'failed':'Pagamento recusado', 'cancelled':'Cancelado'}

def next_month(day):
    year, month = (day.year + 1, 1) if day.month == 12 else (day.year, day.month + 1)
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))

def init(conn):
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS billing97_test (
        professional_id INTEGER PRIMARY KEY REFERENCES professionals(id),
        plan TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', due TEXT NOT NULL,
        cancelled INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS billing97_history (
        id INTEGER PRIMARY KEY, professional_id INTEGER NOT NULL REFERENCES professionals(id),
        plan TEXT NOT NULL, cents INTEGER NOT NULL, status TEXT NOT NULL,
        due TEXT NOT NULL, created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS billing97_inbox (
        event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, resource_id TEXT NOT NULL,
        received TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'awaiting_review');
    ''')
    conn.commit()

def apply_test(conn, pid, action):
    row = conn.execute('SELECT * FROM billing97_test WHERE professional_id=?', (pid,)).fetchone()
    if not row: raise HTTPException(404, 'Crie uma assinatura de teste primeiro')
    if action == 'cancelled':
        conn.execute('UPDATE billing97_test SET cancelled=1 WHERE professional_id=?', (pid,))
    else:
        if row['cancelled']: raise HTTPException(409, 'Assinatura de teste cancelada')
        # Um ciclo pago não pode ser sobrescrito por um aviso repetido/antigo.
        if row['status'] == 'paid' and action != 'renew': return
        if action == 'renew':
            if row['status'] != 'paid': raise HTTPException(409, 'Pague o ciclo antes de renovar')
            due = next_month(date.fromisoformat(row['due'])).isoformat()
            conn.execute("UPDATE billing97_test SET due=?,status='pending' WHERE professional_id=?", (due,pid))
            return
        conn.execute('UPDATE billing97_test SET status=? WHERE professional_id=?', (action,pid))
    status = 'cancelled' if action == 'cancelled' else action
    conn.execute('INSERT INTO billing97_history(professional_id,plan,cents,status,due,created) VALUES(?,?,?,?,?,?)',
        (pid,row['plan'],PLANS[row['plan']][1],status,row['due'],datetime.now(timezone.utc).isoformat()))

def install(app, db, require_user, templates, context):
    router = APIRouter()
    @app.on_event('startup')
    def setup():
        with db() as conn: init(conn)
        conn.close()

    def csrf(request):
        cookie = request.cookies.get('billing97_csrf','')
        return cookie

    @router.get('/painel/pagamentos')
    def payments(request: Request):
        user=require_user(request,'professional')
        with db() as conn:
            pro=conn.execute('SELECT * FROM professionals WHERE user_id=?',(user['id'],)).fetchone()
            if not pro: raise HTTPException(404,'Loja não encontrada')
            sub=conn.execute('SELECT * FROM billing97_test WHERE professional_id=?',(pro['id'],)).fetchone()
            history=conn.execute('SELECT * FROM billing97_history WHERE professional_id=? ORDER BY id DESC LIMIT 100',(pro['id'],)).fetchall()
        conn.close()
        return templates.TemplateResponse('billing97.html',context(request,pro=pro,sub=sub,history=history,plans=PLANS,labels=LABELS))

    @router.get('/admin/assinaturas')
    def admin(request: Request):
        require_user(request,'admin'); token=csrf(request) or secrets.token_urlsafe(32)
        with db() as conn:
            rows=conn.execute('''SELECT p.id,p.display_name,p.plan_active,p.admission_status,b.plan,b.status,b.due,b.cancelled
                FROM professionals p LEFT JOIN billing97_test b ON b.professional_id=p.id WHERE p.is_demo=0 ORDER BY p.id DESC''').fetchall()
            events=conn.execute('SELECT * FROM billing97_inbox ORDER BY received DESC LIMIT 100').fetchall()
        conn.close()
        response=templates.TemplateResponse('billing97_admin.html',context(request,rows=rows,events=events,plans=PLANS,labels=LABELS,csrf=token))
        response.set_cookie('billing97_csrf',token,httponly=True,samesite='strict',secure=request.url.scheme=='https',path='/')
        return response

    @router.post('/admin/assinaturas/teste')
    def simulate(request: Request, pid:int=Form(...), action:str=Form(...), plan:str=Form('vitrine'), token:str=Form(...)):
        require_user(request,'admin')
        if not csrf(request) or not hmac.compare_digest(csrf(request),token): raise HTTPException(403,'Atualize a página e tente novamente')
        if action not in ('create','paid','failed','overdue','cancelled','renew'): raise HTTPException(400,'Ação inválida')
        if plan not in PLANS: raise HTTPException(400,'Plano inválido')
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            if not conn.execute('SELECT 1 FROM professionals WHERE id=? AND is_demo=0',(pid,)).fetchone(): raise HTTPException(404,'Loja não encontrada')
            if action=='create':
                conn.execute('''INSERT INTO billing97_test(professional_id,plan,due) VALUES(?,?,?)
                    ON CONFLICT(professional_id) DO UPDATE SET plan=excluded.plan,status='pending',due=excluded.due,cancelled=0''',(pid,plan,date.today().isoformat()))
            else: apply_test(conn,pid,action)
        conn.close()
        return RedirectResponse('/admin/assinaturas',303)

    @router.post('/integracoes/asaas/webhook')
    async def webhook(request: Request):
        # Somente inbox de Sandbox. Não libera/suspende planos reais nesta etapa.
        expected=os.getenv('ASAAS_SANDBOX_WEBHOOK_TOKEN','')
        supplied=request.headers.get('asaas-access-token','')
        if len(expected)<32 or not hmac.compare_digest(expected,supplied): raise HTTPException(401,'Notificação não autorizada')
        raw=await request.body()
        if len(raw)>262144: raise HTTPException(413,'Notificação muito grande')
        import json
        try: data=json.loads(raw)
        except (ValueError,UnicodeDecodeError): raise HTTPException(400,'JSON inválido')
        if not isinstance(data,dict): raise HTTPException(400,'Evento inválido')
        eid,kind=data.get('id'),data.get('event')
        if not isinstance(eid,str) or not isinstance(kind,str) or not eid or len(eid)>200 or len(kind)>100: raise HTTPException(400,'Evento inválido')
        resource=next((data[k] for k in ('payment','subscription','checkout') if isinstance(data.get(k),dict)),{})
        rid=resource.get('id','')
        if not isinstance(rid,str): raise HTTPException(400,'Recurso inválido')
        with db() as conn:
            conn.execute('INSERT OR IGNORE INTO billing97_inbox(event_id,event_type,resource_id,received) VALUES(?,?,?,?)',(eid,kind,rid[:200],datetime.now(timezone.utc).isoformat()))
        conn.close()
        return {'received':True}
    app.include_router(router)
