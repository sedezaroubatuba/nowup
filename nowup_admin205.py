"""ADM compacto V205. Integra-se às regras de autenticação e cobrança existentes."""
from datetime import datetime, timezone, date, timedelta
from collections import defaultdict
from urllib.parse import urlencode
import sqlite3
import inspect
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from nowup_admin72 import enrich_profiles, today_local
from nowup_admin97 import bounds, local_day
router=APIRouter()
G={}
SECTIONS={'inicio':'Visão geral','clientes':'Clientes','lojistas':'Lojistas','relatorios':'Relatórios por região','categorias':'Categorias de lojas','suporte':'Suporte','denuncias':'Denúncias','configuracoes':'Configuração geral'}
UFS=set('AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split())
def configure(globals_): G.update(globals_)
def db(): return G['db']()
def stamp(): return datetime.now(timezone.utc).isoformat()
def auth(r,role='admin'): return G['require_user'](r,role)
def redirect(section='inicio',**kw): return RedirectResponse('/admin/central?'+urlencode(dict(secao=section,**kw)),303)
def render(r,name,**kw):
    ctx=G['context'](r,**kw)
    if 'request' in inspect.signature(G['templates'].TemplateResponse).parameters:
        response=G['templates'].TemplateResponse(request=r,name=name,context=ctx)
    else:response=G['templates'].TemplateResponse(name,ctx)
    response.headers['Cache-Control']='no-store';return response

def initialize():
    c=db()
    try:
        for table in ('users','professionals'):
            for col in ('state','city') if table=='users' else ('state',):
                if col not in {r[1] for r in c.execute('PRAGMA table_info('+table+')')}:
                    c.execute('ALTER TABLE '+table+' ADD COLUMN '+col+" TEXT NOT NULL DEFAULT ''")
        c.executescript('''CREATE TABLE IF NOT EXISTS support205(
        id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),subject TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS support_messages205(id INTEGER PRIMARY KEY,ticket_id INTEGER NOT NULL REFERENCES support205(id),
        sender_id INTEGER NOT NULL REFERENCES users(id),body TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS support205_user ON support205(user_id,id);
        CREATE INDEX IF NOT EXISTS support_messages205_ticket ON support_messages205(ticket_id,id);
        CREATE TABLE IF NOT EXISTS admin_changes205(id INTEGER PRIMARY KEY,admin_id INTEGER NOT NULL,
        action TEXT NOT NULL,target TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS users205_region ON users(role,city,state,neighborhood);
        CREATE INDEX IF NOT EXISTS orders205_customer ON orders(customer_id,status);
        CREATE INDEX IF NOT EXISTS orders205_professional ON orders(professional_id,status);''')
        c.commit()
    finally:c.close()
def audit(c,u,action,target):c.execute('INSERT INTO admin_changes205(admin_id,action,target,created_at) VALUES(?,?,?,?)',(u['id'],action,str(target),stamp()))
def period(params):
    try:
        a=date.fromisoformat(params.get('inicio') or today_local().replace(day=1).isoformat());b=date.fromisoformat(params.get('fim') or today_local().isoformat())
    except ValueError:raise HTTPException(400,'Datas inválidas')
    if a>b or (b-a).days>366:raise HTTPException(400,'Escolha um período de até 367 dias')
    return a,b

def people(c,params,merchant=False):
    role='professional' if merchant else 'customer';a='p' if merchant else 'u';clauses=['u.role=?'];args=[role]
    if merchant:clauses.append('p.is_demo=0')
    for key,col in [('q','p.display_name' if merchant else 'u.name'),('bairro',a+'.neighborhood'),('cidade',a+'.city'),('estado',a+'.state')]:
        value=params.get(key,'').strip()[:120]
        if value:
            clauses.append(col+(' LIKE ?' if key=='q' else '=?'));args.append('%'+value+'%' if key=='q' else value)
    for key,op in [('inicio','>='),('fim','<=')]:
        value=params.get(key,'')
        if value:
            try: date.fromisoformat(value)
            except ValueError:raise HTTPException(400,'Data de cadastro inválida')
            clauses.append('date(u.created_at)'+op+'date(?)');args.append(value)
    st=params.get('situacao','')
    mapping={'ativos':"u.is_active=1" if not merchant else "u.is_active=1 AND p.blocked=0 AND p.admission_status='approved'",'inativos':"u.is_active=0" if not merchant else '(u.is_active=0 OR p.blocked=1)', 'email':'u.email_verified=0'}
    if st in mapping:clauses.append(mapping[st])
    if merchant:
        if st=='pendentes':clauses.append("p.admission_status='pending'")
        if st=='recusados':clauses.append("p.admission_status='rejected'")
        if st=='novos':clauses.append("julianday(u.created_at)>=julianday('now','-30 days')")
        due="date(p.billing_due_date)";paid="p.is_demo=0 AND p.plan_granted=0 AND p.plan_active IN ('cardapio','vitrine','ambos')"
        if st=='inadimplentes':clauses.append(paid+" AND "+due+"<date('now','-3 hours')")
        if st=='em-dia':clauses.append(paid+" AND "+due+">date('now','-3 hours','+7 days')")
        if st=='a-vencer':clauses.append(paid+" AND "+due+" BETWEEN date('now','-3 hours') AND date('now','-3 hours','+7 days')")
        if params.get('plano') in ('cardapio','vitrine','ambos'):clauses.append('p.plan_active=?');args.append(params['plano'])
    join='JOIN professionals p ON p.user_id=u.id' if merchant else ''
    owner='o.professional_id=p.id' if merchant else 'o.customer_id=u.id'
    for key,condition in [('pedidos','1=1'),('cancelamentos',"o.status IN ('cancelled','rejected')")]:
        v=params.get(key,'')
        if v in ('com','sem'):clauses.append(('NOT ' if v=='sem' else '')+'EXISTS(SELECT 1 FROM orders o WHERE '+owner+' AND '+condition+')')
    where=' AND '.join('('+s+')' for s in clauses)
    count=c.execute('SELECT COUNT(*) FROM users u '+join+' WHERE '+where,args).fetchone()[0]
    try:page=max(1,int(params.get('pagina','1')))
    except ValueError:page=1
    page=min(page,max(1,(count+24)//25))
    cols='u.id,u.name,u.neighborhood,u.created_at' if not merchant else 'u.id,p.id pid,p.display_name name,p.neighborhood,u.created_at'
    rows=[dict(r) for r in c.execute('SELECT '+cols+' FROM users u '+join+' WHERE '+where+' ORDER BY u.id DESC LIMIT 25 OFFSET ?',args+[(page-1)*25])]
    return rows,count,page

@router.get('/admin')
def entry(request:Request):auth(request);return redirect()
@router.get('/admin/central')
def dashboard(request:Request):
    auth(request);p=request.query_params;sec=p.get('secao','inicio')
    if sec not in SECTIONS:raise HTTPException(404,'Área inexistente')
    c=db();data=dict(sec=sec,sections=SECTIONS,params=p,people=[],count=0,page=1,detail=None,ticket=None)
    try:
        data['stats']={k:c.execute(sql).fetchone()[0] for k,sql in {
        'clientes':"SELECT count(*) FROM users WHERE role='customer'",'lojistas':"SELECT count(*) FROM professionals WHERE is_demo=0",'pendentes':"SELECT count(*) FROM professionals WHERE is_demo=0 AND admission_status='pending'",'suporte':"SELECT count(*) FROM support205 WHERE status!='resolved'",'denuncias':"SELECT count(*) FROM reports WHERE status!='resolved'"}.items()}
        data['stats']['inadimplentes']=people(c,{'situacao':'inadimplentes'},True)[1]
        if sec in ('clientes','lojistas'):
            data['people'],data['count'],data['page']=people(c,p,sec=='lojistas')
            try:uid=int(p.get('conta','0'))
            except ValueError:raise HTTPException(400,'Conta inválida')
            if uid:
                role='professional' if sec=='lojistas' else 'customer'
                u=c.execute('SELECT id,name,email,phone,is_active,email_verified,created_at,address,neighborhood,city,state FROM users WHERE id=? AND role=?',(uid,role)).fetchone()
                if not u:raise HTTPException(404,'Conta não encontrada')
                d=dict(u);d['pro']=None
                try:d['is_new']=(today_local()-local_day(d['created_at'])).days<=30
                except (ValueError,TypeError):d['is_new']=False
                if role=='professional':
                    pro=c.execute('SELECT * FROM professionals WHERE user_id=?',(uid,)).fetchone();d['pro']=enrich_profiles([pro])[0]
                    # V72 considera vitrine gratuita; V205 exibe cobrança dos três planos pagos.
                    if not pro['is_demo'] and not pro['plan_granted'] and pro['plan_active'] in ('cardapio','vitrine','ambos'):
                        prodata=dict(pro);prodata['is_premium']=1;d['pro'].update({k:v for k,v in enrich_profiles([prodata])[0].items() if k.startswith('billing_')})
                owner='professional_id' if d['pro'] else 'customer_id';oid=d['pro']['id'] if d['pro'] else uid
                d['orders']=[dict(r) for r in c.execute('SELECT id,order_code,status,total_cents,created_at FROM orders WHERE '+owner+'=? ORDER BY id DESC LIMIT 30',(oid,))]
                d['order_count']=c.execute('SELECT count(*) FROM orders WHERE '+owner+'=?',(oid,)).fetchone()[0]
                d['cancel_count']=c.execute("SELECT count(*) FROM orders WHERE "+owner+"=? AND status IN ('cancelled','rejected')",(oid,)).fetchone()[0]
                d['category_id']=c.execute('SELECT category_id FROM professional_categories WHERE professional_id=? LIMIT 1',(d['pro']['id'],)).fetchone()[0] if d['pro'] and c.execute('SELECT 1 FROM professional_categories WHERE professional_id=?',(d['pro']['id'],)).fetchone() else 0
                data['store_categories']=[dict(r) for r in c.execute('SELECT id,name,active FROM categories ORDER BY sort_order,name')]
                data['detail']=d
        if sec=='categorias':data['categories']=[dict(r) for r in c.execute('SELECT * FROM categories ORDER BY sort_order,name')]
        if sec=='denuncias':data['reports']=[dict(r) for r in c.execute('SELECT r.*,u.name customer,p.display_name store FROM reports r JOIN users u ON u.id=r.customer_id JOIN professionals p ON p.id=r.professional_id ORDER BY r.id DESC LIMIT 100')]
        if sec=='suporte':
            status=p.get('situacao','open');where=' WHERE t.status=?' if status in ('open','in_progress','resolved') else '';args=(status,) if where else ()
            data['tickets']=[dict(r) for r in c.execute('SELECT t.*,u.name,u.role FROM support205 t JOIN users u ON u.id=t.user_id'+where+' ORDER BY t.updated_at DESC LIMIT 100',args)]
            data['legacy_tickets']=[dict(r) for r in c.execute('SELECT * FROM admin_support97 ORDER BY id DESC LIMIT 50')]
            if p.get('chamado'):data['ticket']=ticket(c,int(p['chamado']))
        if sec=='relatorios':data.update(regional(c,p))
        if sec=='configuracoes':data['changes']=[dict(r) for r in c.execute('SELECT a.*,u.name FROM admin_changes205 a JOIN users u ON u.id=a.admin_id ORDER BY a.id DESC LIMIT 30')]
        data['ufs']=sorted(UFS)
        data['page_url']=lambda n:'/admin/central?'+urlencode(dict({k:v for k,v in p.items() if k!='conta'},pagina=n))
    finally:c.close()
    return render(request,'admin205.html',**data)

def regional(c,p):
    start,end=period(p);lo,hi=bounds(start,end);clauses=[];args=[]
    for key,col in [('cidade','p.city'),('estado','p.state'),('bairro','p.neighborhood')]:
        if p.get(key):clauses.append(col+'=?');args.append(p[key][:120])
    extra=' AND '+' AND '.join(clauses) if clauses else ''
    sales=[dict(r) for r in c.execute('''SELECT p.city,p.state,p.neighborhood,count(*) orders,sum(o.total_cents) amount FROM orders o JOIN professionals p ON p.id=o.professional_id
      WHERE p.is_demo=0 AND o.status='completed' AND julianday(COALESCE((SELECT max(h.created_at) FROM order_status_history h WHERE h.order_id=o.id AND h.status='completed'),o.updated_at))>=julianday(?) AND julianday(COALESCE((SELECT max(h.created_at) FROM order_status_history h WHERE h.order_id=o.id AND h.status='completed'),o.updated_at))<julianday(?)'''+extra+' GROUP BY p.state,p.city,p.neighborhood ORDER BY amount DESC',[lo,hi]+args)]
    delivery_clauses=[];delivery_args=[]
    for key,col in [('cidade','u.city'),('estado','u.state'),('bairro','o.neighborhood')]:
        if p.get(key):delivery_clauses.append(col+'=?');delivery_args.append(p[key][:120])
    delivery_extra=' AND '+' AND '.join(delivery_clauses) if delivery_clauses else ''
    delivered=[dict(r) for r in c.execute("""SELECT u.city,u.state,o.neighborhood,count(*) orders,sum(o.total_cents) amount FROM orders o
    JOIN professionals p ON p.id=o.professional_id LEFT JOIN users u ON u.id=o.customer_id
    WHERE p.is_demo=0 AND o.status='completed' AND o.fulfillment_type='delivery'
    AND julianday(COALESCE((SELECT max(h.created_at) FROM order_status_history h WHERE h.order_id=o.id AND h.status='completed'),o.updated_at))>=julianday(?)
    AND julianday(COALESCE((SELECT max(h.created_at) FROM order_status_history h WHERE h.order_id=o.id AND h.status='completed'),o.updated_at))<julianday(?)"""+delivery_extra+' GROUP BY u.state,u.city,o.neighborhood ORDER BY amount DESC',[lo,hi]+delivery_args)]
    registrations=[]
    for merchant in (False,True):
        a='p' if merchant else 'u';where=[];values=[]
        for key,col in [('cidade',a+'.city'),('estado',a+'.state'),('bairro',a+'.neighborhood')]:
            if p.get(key):where.append(col+'=?');values.append(p[key][:120])
        ex=' AND '+' AND '.join(where) if where else ''
        rows=c.execute('SELECT '+a+'.city,'+a+'.state,'+a+'.neighborhood,count(*) count FROM users u '+('JOIN professionals p ON p.user_id=u.id' if merchant else '')+" WHERE u.role=? AND julianday(u.created_at)>=julianday(?) AND julianday(u.created_at)<julianday(?)"+(' AND p.is_demo=0' if merchant else '')+ex+' GROUP BY '+a+'.state,'+a+'.city,'+a+'.neighborhood',['professional' if merchant else 'customer',lo,hi]+values).fetchall()
        registrations.append([dict(r) for r in rows])
    return dict(start=start.isoformat(),end=end.isoformat(),sales=sales,delivered=delivered,registrations=registrations)

def require_target(c,uid):
    u=c.execute("SELECT * FROM users WHERE id=? AND role IN ('customer','professional')",(uid,)).fetchone()
    if not u:raise HTTPException(404,'Conta não encontrada')
    return u

@router.post('/admin/central/contas/{uid}/editar')
def edit(request:Request,uid:int,name:str=Form(...),email:str=Form(...),phone:str=Form(''),address:str=Form(...),neighborhood:str=Form(...),city:str=Form(...),state:str=Form(...),category_id:int=Form(0)):
    actor=auth(request);normalized=G['normalize_email'](email)
    if not normalized or not all(x.strip() for x in (name,address,neighborhood,city)) or state not in UFS:raise HTTPException(400,'Preencha nome, e-mail e endereço completo válidos')
    c=db();send=None
    try:
        c.execute('BEGIN IMMEDIATE');u=require_target(c,uid)
        if c.execute('SELECT 1 FROM users WHERE email=? AND id!=?',(normalized,uid)).fetchone():raise HTTPException(409,'E-mail já utilizado')
        c.execute('UPDATE users SET name=?,email=?,phone=?,address=?,neighborhood=?,city=?,state=? WHERE id=?',(name.strip()[:120],normalized,phone.strip()[:30],address.strip()[:300],neighborhood.strip()[:120],city.strip()[:120],state,uid))
        if u['role']=='professional':
            c.execute('UPDATE professionals SET display_name=?,whatsapp=?,address=?,neighborhood=?,city=?,state=? WHERE user_id=?',(name.strip()[:120],phone.strip()[:30],address.strip()[:300],neighborhood.strip()[:120],city.strip()[:120],state,uid))
            if category_id:
                if not c.execute('SELECT id FROM categories WHERE id=? AND active=1',(category_id,)).fetchone():raise HTTPException(400,'Categoria indisponível')
                pid=c.execute('SELECT id FROM professionals WHERE user_id=?',(uid,)).fetchone()[0]
                c.execute('DELETE FROM professional_categories WHERE professional_id=?',(pid,))
                c.execute('INSERT INTO professional_categories(professional_id,category_id) VALUES(?,?)',(pid,category_id))
        if normalized!=u['email']:
            token,expires=G['verification_token']();c.execute('UPDATE users SET email_verified=0,verification_token=?,verification_expires_at=? WHERE id=?',(token,expires,uid));c.execute('DELETE FROM sessions WHERE user_id=?',(uid,));send=(normalized,name,token)
        audit(c,actor,'Cadastro editado; nova confirmação exigida' if send else 'Cadastro editado',uid);c.commit()
    finally:c.close()
    ok='cadastro-salvo'
    if send:
        try:sent=G['send_verification'](*send)
        except Exception:sent=False
        ok='email-confirmacao-enviado' if sent else 'email-salvo-envio-falhou'
    return redirect('lojistas' if u['role']=='professional' else 'clientes',conta=uid,ok=ok)

@router.post('/admin/central/contas/{uid}/situacao')
def toggle(request:Request,uid:int,active:int=Form(...),reason:str=Form(...)):
    actor=auth(request)
    if active not in (0,1) or not reason.strip():raise HTTPException(400,'Informe a situação e a justificativa')
    c=db()
    try:
        c.execute('BEGIN IMMEDIATE');u=require_target(c,uid)
        if u['role']=='professional' and active:
            pro=c.execute('SELECT admission_status FROM professionals WHERE user_id=?',(uid,)).fetchone()
            if pro['admission_status']!='approved':raise HTTPException(409,'Aprove o cadastro antes de reativar a loja')
        c.execute('UPDATE users SET is_active=? WHERE id=?',(active,uid))
        if u['role']=='professional':c.execute('UPDATE professionals SET blocked=? WHERE user_id=?',(1-active,uid))
        if not active:c.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
        audit(c,actor,('Reativação: ' if active else 'Inativação: ')+reason.strip()[:300],uid);c.commit()
    finally:c.close()
    return redirect('lojistas' if u['role']=='professional' else 'clientes',conta=uid,ok='situacao-salva')

def ticket(c,tid,uid=None):
    t=c.execute('SELECT t.*,u.name,u.role FROM support205 t JOIN users u ON u.id=t.user_id WHERE t.id=?'+(' AND t.user_id=?' if uid else ''),(tid,uid) if uid else (tid,)).fetchone()
    if not t:raise HTTPException(404,'Chamado não encontrado')
    d=dict(t);d['messages']=[dict(r) for r in c.execute('SELECT m.*,u.name,u.role FROM support_messages205 m JOIN users u ON u.id=m.sender_id WHERE ticket_id=? ORDER BY m.id',(tid,))];return d

def notify(c,uid,body,tid):
    u=c.execute('SELECT is_active FROM users WHERE id=?',(uid,)).fetchone()
    cur=c.execute("INSERT INTO notifications(user_id,title,message,link,created_at) VALUES(?,?,?,?,?)",(uid,'Mensagem da equipe NowUp',body[:180],'/suporte?chamado='+str(tid),stamp()))
    if u and u['is_active'] and G.get('nowup_alerts112'):G['nowup_alerts112'].enqueue(c,uid,cur.lastrowid,{'title':'Equipe NowUp','body':body[:180],'url':'/suporte?chamado='+str(tid),'tag':'suporte-'+str(tid)})

@router.post('/admin/central/contas/{uid}/mensagem')
def message(request:Request,uid:int,subject:str=Form(...),body:str=Form(...)):
    actor=auth(request)
    if not subject.strip() or not body.strip() or len(body)>4000:raise HTTPException(400,'Preencha assunto e mensagem de até 4.000 caracteres')
    c=db()
    try:
        u=require_target(c,uid);t=stamp();cur=c.execute('INSERT INTO support205(user_id,subject,created_at,updated_at) VALUES(?,?,?,?)',(uid,subject.strip()[:160],t,t));tid=cur.lastrowid
        c.execute('INSERT INTO support_messages205(ticket_id,sender_id,body,created_at) VALUES(?,?,?,?)',(tid,actor['id'],body.strip(),t));notify(c,uid,body,tid);audit(c,actor,'Mensagem enviada',uid);c.commit()
    finally:c.close()
    return redirect('suporte',chamado=tid,ok='mensagem-enviada')

@router.post('/admin/central/suporte/{tid}')
def reply_admin(request:Request,tid:int,status:str=Form(...),body:str=Form('')):
    actor=auth(request)
    if status not in ('open','in_progress','resolved') or len(body)>4000:raise HTTPException(400,'Dados inválidos')
    c=db()
    try:
        t=ticket(c,tid);s=stamp()
        if body.strip():
            c.execute('INSERT INTO support_messages205(ticket_id,sender_id,body,created_at) VALUES(?,?,?,?)',(tid,actor['id'],body.strip(),s));notify(c,t['user_id'],body,tid)
        c.execute('UPDATE support205 SET status=?,updated_at=? WHERE id=?',(status,s,tid));audit(c,actor,'Suporte: '+status,tid);c.commit()
    finally:c.close()
    return redirect('suporte',chamado=tid,ok='chamado-salvo')

@router.get('/suporte')
def support(request:Request,chamado:int=0):
    u=G['require_user'](request)
    if u['role']=='admin':return redirect('suporte')
    c=db()
    try:
        tickets=[dict(r) for r in c.execute('SELECT * FROM support205 WHERE user_id=? ORDER BY updated_at DESC LIMIT 100',(u['id'],))]
        selected=ticket(c,chamado,u['id']) if chamado else None
    finally:c.close()
    return render(request,'support205.html',tickets=tickets,selected=selected)
@router.post('/suporte')
def new_support(request:Request,subject:str=Form(...),body:str=Form(...)):
    u=G['require_user'](request)
    if u['role'] not in ('customer','professional'):raise HTTPException(403)
    if not subject.strip() or not body.strip() or len(body)>4000:raise HTTPException(400,'Preencha o assunto e a mensagem de até 4.000 caracteres')
    c=db();s=stamp()
    try:
        cur=c.execute('INSERT INTO support205(user_id,subject,created_at,updated_at) VALUES(?,?,?,?)',(u['id'],subject.strip()[:160],s,s));tid=cur.lastrowid
        c.execute('INSERT INTO support_messages205(ticket_id,sender_id,body,created_at) VALUES(?,?,?,?)',(tid,u['id'],body.strip(),s));c.commit()
    finally:c.close()
    return RedirectResponse('/suporte?chamado='+str(tid),303)
@router.post('/suporte/{tid}')
def reply_user(request:Request,tid:int,body:str=Form(...)):
    u=G['require_user'](request)
    if not body.strip() or len(body)>4000:raise HTTPException(400,'Escreva uma mensagem de até 4.000 caracteres')
    c=db()
    try:
        ticket(c,tid,u['id']);s=stamp();c.execute('INSERT INTO support_messages205(ticket_id,sender_id,body,created_at) VALUES(?,?,?,?)',(tid,u['id'],body.strip(),s));c.execute("UPDATE support205 SET status='open',updated_at=? WHERE id=?",(s,tid));c.commit()
    finally:c.close()
    return RedirectResponse('/suporte?chamado='+str(tid),303)

@router.post('/admin/central/categorias')
def category(request:Request,cid:int=Form(0),name:str=Form(...),icon:str=Form('🏪'),sort_order:int=Form(100),active:int=Form(1)):
    actor=auth(request);name=name.strip();slug=G['slugify'](name)
    if not name or len(name)>120 or not slug or active not in (0,1):raise HTTPException(400,'Categoria inválida')
    c=db()
    try:
        if cid:
            if not c.execute('SELECT id FROM categories WHERE id=?',(cid,)).fetchone():raise HTTPException(404)
            c.execute('UPDATE categories SET name=?,slug=?,icon=?,sort_order=?,active=? WHERE id=?',(name,slug,icon[:12],sort_order,active,cid))
        else:c.execute('INSERT INTO categories(name,slug,icon,sort_order,active) VALUES(?,?,?,?,?)',(name,slug,icon[:12],sort_order,active))
        audit(c,actor,'Categoria salva',cid or name);c.commit()
    except sqlite3.IntegrityError:raise HTTPException(409,'Já existe uma categoria com esse nome')
    finally:c.close()
    return redirect('categorias',ok='categoria-salva')
@router.post('/admin/central/denuncias/{rid}')
def complaint(request:Request,rid:int,status:str=Form(...)):
    actor=auth(request)
    if status not in ('open','in_progress','resolved'):raise HTTPException(400,'Situação inválida')
    c=db()
    try:
        if not c.execute('SELECT id FROM reports WHERE id=?',(rid,)).fetchone():raise HTTPException(404)
        c.execute('UPDATE reports SET status=? WHERE id=?',(status,rid));audit(c,actor,'Denúncia: '+status,rid);c.commit()
    finally:c.close()
    return redirect('denuncias',ok='denuncia-salva')
@router.post('/admin/central/configuracoes')
def settings(request:Request,public_email:str=Form(''),support_whatsapp:str=Form('')):
    actor=auth(request)
    if public_email and not G['normalize_email'](public_email):raise HTTPException(400,'E-mail de suporte inválido')
    c=db()
    try:
        for k,v in [('public_email',public_email[:160]),('support_whatsapp',support_whatsapp[:40])]:c.execute('INSERT INTO site_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,v))
        audit(c,actor,'Configuração de contato editada','site');c.commit()
    finally:c.close()
    return redirect('configuracoes',ok='configuracao-salva')

@router.post('/admin/central/lojas/{pid}/analise')
def analysis(request:Request,pid:int,decision:str=Form(...),reason:str=Form(''),payment_confirmed:str=Form(''),complimentary:str=Form('')):
    actor=auth(request)
    result=G['admin_review_professional'](request,pid,decision,reason,payment_confirmed,complimentary)
    # Preserve existing business validation and e-mail outcome.
    from urllib.parse import urlparse,parse_qs
    query=parse_qs(urlparse(result.headers.get('location','')).query)
    if 'erro' in query:raise HTTPException(400,'Cadastro não aprovado: '+query['erro'][0])
    c=db()
    try:audit(c,actor,'Análise de loja: '+decision,pid);c.commit()
    finally:c.close()
    return redirect('lojistas',ok='analise-registrada',aviso=query.get('aviso',[''])[0])

@router.post('/admin/central/lojas/{pid}/financeiro')
def billing(request:Request,pid:int,due_date:str=Form(''),last_paid:str=Form('')):
    actor=auth(request)
    result=G['admin_save_billing'](request,pid,due_date,last_paid)
    from urllib.parse import urlparse,parse_qs
    query=parse_qs(urlparse(result.headers.get('location','')).query)
    if 'erro' in query:raise HTTPException(400,'Não foi possível salvar: '+query['erro'][0])
    c=db()
    try:
        pro=c.execute('SELECT user_id FROM professionals WHERE id=?',(pid,)).fetchone()
        if not pro:raise HTTPException(404)
        audit(c,actor,'Mensalidade editada',pid);c.commit()
    finally:c.close()
    return redirect('lojistas',conta=pro['user_id'],ok='mensalidade-salva')
