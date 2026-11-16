"""Prelaunch admin operations: real support, private order detail and safe diagnostics."""
import json,re,shutil
from datetime import datetime,timezone,timedelta
from fastapi import Request,HTTPException
from fastapi.responses import JSONResponse,Response


def initialize(c):
    c.executescript('''CREATE TABLE IF NOT EXISTS support_team446(
        id INTEGER PRIMARY KEY,ticket_id INTEGER NOT NULL REFERENCES support205(id),
        staff_id INTEGER NOT NULL,actor TEXT NOT NULL,body TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS support_team446_ticket ON support_team446(ticket_id,id);
    CREATE TABLE IF NOT EXISTS adm446_incidents(id INTEGER PRIMARY KEY,
        route TEXT NOT NULL,status INTEGER NOT NULL,error_class TEXT NOT NULL,created_at TEXT NOT NULL);''')


def schedule(values,days):
    if not isinstance(values,list) or len(values)!=7:raise HTTPException(400,'Informe os sete dias da semana.')
    result={}
    for day,raw in zip(days,values):
        text=str(raw).strip().lower()
        if text in ('','fechado','fechada','folga'):result[day]={'enabled':False,'start':'09:00','end':'18:00'};continue
        match=re.fullmatch(r'(\d{2}:\d{2})\s*[-–—]\s*(\d{2}:\d{2})',text)
        if not match:raise HTTPException(400,'Use HH:MM-HH:MM ou fechado em cada dia.')
        for value in match.groups():
            try:datetime.strptime(value,'%H:%M')
            except ValueError:raise HTTPException(400,'Horário inválido.')
        if match[1]==match[2]:raise HTTPException(400,'Abertura e fechamento devem ser diferentes.')
        result[day]={'enabled':True,'start':match[1],'end':match[2]}
    return result


def hours(row,days):
    try:config=json.loads(row['business_hours'] or '{}')
    except (ValueError,TypeError):config={}
    if not isinstance(config,dict):config={}
    return [(str(config.get(day,{}).get('start','09:00'))+'-'+str(config.get(day,{}).get('end','18:00'))) if config.get(day,{}).get('enabled') else '' for day in days]


def team_messages(c,tid):
    # Original user/admin messages stay in their original ledger. Team authors are never impersonated.
    return [dict(id='team-'+str(r['id']),sender_id=None,name=r['actor'],role='admin',body=r['body'],created_at=r['created_at']) for r in c.execute('SELECT * FROM support_team446 WHERE ticket_id=? ORDER BY id',(tid,))]


def messages(c,tid):
    result=[dict(r) for r in c.execute('SELECT m.*,u.name,u.role FROM support_messages205 m JOIN users u ON u.id=m.sender_id WHERE ticket_id=? ORDER BY m.id',(tid,))]
    return sorted(result+team_messages(c,tid),key=lambda r:(r['created_at'],str(r['id'])))


def support_counts(c):
    return {'tickets':c.execute("SELECT COUNT(*) FROM support205 WHERE status<>'resolved'").fetchone()[0],
            'reports':c.execute("SELECT COUNT(*) FROM reports WHERE status<>'resolved'").fetchone()[0]}


def install(m):
    r=m.router
    def response(data):return JSONResponse(data,headers={'Cache-Control':'private, no-store','Vary':'Cookie'})
    def revision(c):c.execute('UPDATE adm227_state SET revision=revision+1 WHERE id=1')
    def body_text(data,key,maximum=4000,required=False):return m.clean(data.get(key,''),maximum,required)

    @r.get('/admin/super/api/support')
    def support(request:Request,before:int=0,kind:str='tickets'):
        if before<0 or kind not in ('tickets','reports'):m.fail(400,'Filtro inválido.')
        with m.connection() as c:
            m.auth(request,c,'support')
            if kind=='tickets':
                rows=[dict(x) for x in c.execute('''SELECT t.*,u.name,u.role,
                (SELECT id FROM professionals WHERE user_id=t.user_id LIMIT 1) store
                FROM support205 t JOIN users u ON u.id=t.user_id
                WHERE (?=0 OR t.id<?) ORDER BY t.id DESC LIMIT 101''',(before,before))]
            else:
                rows=[dict(x) for x in c.execute('''SELECT r.*,p.display_name store_name,u.name customer_name
                FROM reports r JOIN professionals p ON p.id=r.professional_id JOIN users u ON u.id=r.customer_id
                WHERE (?=0 OR r.id<?) ORDER BY r.id DESC LIMIT 101''',(before,before))]
            more=len(rows)>100;rows=rows[:100]
            return response({'rows':rows,'nextBefore':rows[-1]['id'] if more else None,'counts':support_counts(c)})

    @r.get('/admin/super/api/support/{tid}')
    def support_detail(request:Request,tid:int):
        with m.connection() as c:
            m.auth(request,c,'support')
            ticket=c.execute('SELECT t.*,u.name FROM support205 t JOIN users u ON u.id=t.user_id WHERE t.id=?',(tid,)).fetchone()
            if not ticket:m.fail(404,'Chamado não encontrado.')
            return response({'ticket':dict(ticket),'messages':messages(c,tid)})

    @r.post('/admin/super/api/support/{tid}')
    async def support_reply(request:Request,tid:int):
        m.csrf(request)
        try:data=await request.json()
        except ValueError:m.fail(400,'Conteúdo JSON inválido.')
        if not isinstance(data,dict):m.fail(400,'Dados inválidos.')
        status=data.get('status');text=body_text(data,'body')
        if status not in ('open','in_progress','resolved'):m.fail(400,'Situação inválida.')
        with m.connection() as c:
            a=m.auth(request,c,'support');c.execute('BEGIN IMMEDIATE')
            ticket=c.execute('SELECT * FROM support205 WHERE id=?',(tid,)).fetchone()
            if not ticket:m.fail(404,'Chamado não encontrado.')
            at=m.stamp()
            if text:
                if a['super']:c.execute('INSERT INTO support_messages205(ticket_id,sender_id,body,created_at) VALUES(?,?,?,?)',(tid,a['id'],text,at))
                else:c.execute('INSERT INTO support_team446(ticket_id,staff_id,actor,body,created_at) VALUES(?,?,?,?,?)',(tid,a['id'],a['name'],text,at))
                # Reuse the actual support notification path; never send WhatsApp or email here.
                m.G['nowup_admin205'].notify(c,ticket['user_id'],text,tid)
            c.execute('UPDATE support205 SET status=?,updated_at=? WHERE id=?',(status,at,tid))
            m.audit(c,a,'Suporte real: '+status,tid);revision(c);c.commit()
        return response({'ok':True})

    @r.post('/admin/super/api/reports/{rid}')
    async def report_update(request:Request,rid:int):
        m.csrf(request)
        try:data=await request.json()
        except ValueError:m.fail(400,'Conteúdo JSON inválido.')
        if not isinstance(data,dict) or data.get('status') not in ('open','in_progress','resolved'):m.fail(400,'Situação inválida.')
        reason=body_text(data,'reason',500,True)
        with m.connection() as c:
            a=m.auth(request,c,'support');c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT id FROM reports WHERE id=?',(rid,)).fetchone():m.fail(404,'Denúncia não encontrada.')
            c.execute('UPDATE reports SET status=? WHERE id=?',(data['status'],rid));m.audit(c,a,'Denúncia real: '+data['status']+' - '+reason,rid);revision(c);c.commit()
        return response({'ok':True})

    @r.get('/admin/super/api/order/{oid}')
    def order_detail(request:Request,oid:int):
        with m.connection() as c:
            a=m.auth(request,c,'orders')
            o=c.execute('SELECT o.*,p.display_name FROM orders o JOIN professionals p ON p.id=o.professional_id WHERE o.id=?',(oid,)).fetchone()
            if not o:m.fail(404,'Pedido não encontrado.')
            o=dict(o)
            item_cols='id,product_name,quantity,unit_price_cents,notes'
            items=[dict(x) for x in c.execute('SELECT '+item_cols+' FROM order_items WHERE order_id=? ORDER BY id',(oid,))]
            for item in items:item['options']=[dict(x) for x in c.execute('SELECT option_name,price_cents FROM order_item_options WHERE order_item_id=? ORDER BY id',(item['id'],))]
            history=[dict(x) for x in c.execute('SELECT status,created_at FROM order_status_history WHERE order_id=? ORDER BY id',(oid,))]
            receipts=[dict(x) for x in c.execute('SELECT id,filename,content_type,size_bytes,created_at FROM order_receipts206 WHERE order_id=? ORDER BY id',(oid,))]
            for item in receipts:item['url']='/admin/super/api/order/'+str(oid)+'/receipt/'+str(item['id'])
            keys=('id','order_code','display_name','customer_name','customer_phone','address','address_reference','neighborhood','city','fulfillment_type','payment_method','status','order_origin','subtotal_cents','delivery_fee_cents','total_cents','notes','cancellation_reason','created_at','updated_at','change_for_cents')
            detail={key:o.get(key,'') for key in keys}
            detail['statusLabel']=m.G['ORDER_STATUS_LABELS'].get(o['status'],o['status'])
            for event in history:event['label']=m.G['ORDER_STATUS_LABELS'].get(event['status'],event['status'])
            from nowup_notinha401 import payment_checked
            detail['payment_confirmed']=payment_checked(c,o)
            detail['read_only']=o['status']=='whatsapp_finalized'
            m.audit(c,a,'Consulta de detalhes do pedido',oid);c.commit()
            return response({'order':detail,'items':items,'history':history,'receipts':receipts})

    @r.get('/admin/super/api/order/{oid}/receipt/{rid}')
    def receipt_download(request:Request,oid:int,rid:int):
        with m.connection() as c:
            a=m.auth(request,c,'orders')
            row=c.execute('SELECT content_type,content FROM order_receipts206 WHERE order_id=? AND id=?',(oid,rid)).fetchone()
            if not row:m.fail(404,'Comprovante não encontrado.')
            mime=row['content_type'] if row['content_type'] in ('application/pdf','image/jpeg') else 'application/octet-stream'
            ext='pdf' if mime=='application/pdf' else 'jpg'
            m.audit(c,a,'Consulta de comprovante privado',oid);c.commit()
            return Response(bytes(row['content']),media_type=mime,headers={'Cache-Control':'private, no-store','Content-Disposition':f'attachment; filename="comprovante-{oid}-{rid}.{ext}"','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; sandbox"})

    @r.get('/admin/super/api/operations')
    def operations(request:Request):
        with m.connection() as c:
            m.auth(request,c,'system')
            from nowup_database239 import is_postgres
            import nowup_backup as backup
            state=backup.state();last=state.get('last_external','');age=None
            if last:
                try:age=round((datetime.now(timezone.utc)-datetime.fromisoformat(last)).total_seconds()/3600,1)
                except (ValueError,TypeError):pass
            storage=shutil.disk_usage(m.G['UPLOAD_DIR'])
            checks={'database':{'engine':'postgres' if is_postgres() else 'sqlite','reachable':c.execute('SELECT 1').fetchone()[0]==1,'stores':c.execute('SELECT COUNT(*) FROM professionals').fetchone()[0],'orders':c.execute('SELECT COUNT(*) FROM orders').fetchone()[0],'lastOrder':c.execute('SELECT MAX(created_at) FROM orders').fetchone()[0]},
                    'backup':{'configured':not backup.missing_config(),'automatic':backup.automatic_enabled(),'running':backup._local.locked(),'lastSuccess':last,'ageHours':age,'failed':bool(state.get('error')),'warning':bool(state.get('warning')),'restoreVerified':False},
                    'storage':{'freeBytes':storage.free,'usedPercent':round(storage.used/storage.total*100,1)},
                    'emailConfigured':bool(m.G['email_service_configured']()),'billing':{'connected':False,'mode':'manual'},
                    'incidents':[dict(x) for x in c.execute('SELECT route,status,error_class,created_at FROM adm446_incidents ORDER BY id DESC LIMIT 50')]}
            return response(checks)

    def record(route,status,error):
        try:
            with m.connection() as c:
                c.execute('INSERT INTO adm446_incidents(route,status,error_class,created_at) VALUES(?,?,?,?)',(route,status,error,m.stamp()))
                c.execute('DELETE FROM adm446_incidents WHERE created_at<?',((datetime.now(timezone.utc)-timedelta(days=30)).isoformat(),));c.commit()
        except Exception:pass # Database failure must not hide the original response.

    @m.G['app'].middleware('http') if m.G.get('app') else (lambda fn:fn)
    async def capture_incidents(request,call_next):
        from starlette.concurrency import run_in_threadpool
        try:
            result=await call_next(request)
        except Exception as exc:
            route=getattr(request.scope.get('route'),'path','rota indisponível')
            await run_in_threadpool(record,route,500,type(exc).__name__)
            raise
        if result.status_code>=500:
            route=getattr(request.scope.get('route'),'path','rota indisponível')
            await run_in_threadpool(record,route,result.status_code,'HTTP_'+str(result.status_code))
        return result
