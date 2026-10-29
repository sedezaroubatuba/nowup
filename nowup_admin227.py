"""Super ADM V227. SQLite/main; sessão existente, RBAC e persistência reais.

Não cria exemplos nem altera planos/valores de contratos durante a instalação.
Serviços externos não configurados falham explicitamente, sem falso sucesso.
"""
from __future__ import annotations
import base64, hashlib, hmac, html, io, json, re, secrets, sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

router=APIRouter(); G={}; TZ=ZoneInfo('America/Sao_Paulo')
MODULES={'dashboard','stores','finance','orders','customers','products','marketing','logistics','support','themes','settings','staff','system'}
KINDS={'plans':'finance','payments':'finance','billingCoupons':'finance','couriers':'logistics','deliveryRules':'logistics','coupons':'marketing','campaigns':'marketing','referrals':'marketing','themes':'themes','tickets':'support','staff':'staff','leads':'stores','storemeta':'stores','productCategories':'products','productmeta':'products','customermeta':'customers'}
FINALS={'completed','cancelled','rejected'}

def configure(g):G.update(g)
def stamp():return datetime.now(timezone.utc).isoformat()
def tokenhash(v):return hashlib.sha256(v.encode()).hexdigest()
def fail(status,msg):raise HTTPException(status,msg)
@contextmanager
def connection():
 c=G['db']()
 try:yield c
 except Exception:c.rollback();raise
 finally:c.close()
def initialize():
 with connection() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS adm227_entities(kind TEXT NOT NULL,id INTEGER NOT NULL,data TEXT NOT NULL,PRIMARY KEY(kind,id));
CREATE TABLE IF NOT EXISTS adm227_state(id INTEGER PRIMARY KEY,revision INTEGER NOT NULL DEFAULT 0,settings TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS adm227_audit(id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT NOT NULL,actor_id TEXT NOT NULL,action TEXT NOT NULL,target TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS adm227_access(id INTEGER PRIMARY KEY AUTOINCREMENT,actor_id TEXT NOT NULL,name TEXT NOT NULL,session_hash TEXT NOT NULL UNIQUE,start TEXT NOT NULL,last_activity TEXT NOT NULL,end TEXT NOT NULL DEFAULT '',state TEXT NOT NULL DEFAULT 'Conectado');
CREATE TABLE IF NOT EXISTS adm227_team_sessions(token_hash TEXT PRIMARY KEY,staff_id INTEGER NOT NULL,expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS adm227_challenges(challenge_hash TEXT PRIMARY KEY,staff_id INTEGER NOT NULL,code_hash TEXT NOT NULL,expires_at TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS adm227_invites(token_hash TEXT PRIMARY KEY,staff_id INTEGER NOT NULL,expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS adm227_limits(key TEXT PRIMARY KEY,started TEXT NOT NULL,attempts INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS adm227_audit_date ON adm227_audit(created_at,id);''')
  c.execute("INSERT OR IGNORE INTO adm227_state(id) VALUES(1)")
  if not c.execute("SELECT 1 FROM adm227_entities WHERE kind='plans'").fetchone():
   for i,(key,name,price) in enumerate([('start','Start',7900),('pro','Pro',14900),('premium','Premium',24900)],1):put(c,'plans',i,{'id':key,'name':name,'price':price,'features':'Plano de mensalidade; vinculação individual sem migração automática'})
  c.execute('CREATE INDEX IF NOT EXISTS order_items_order255 ON order_items(order_id,id)')
  c.execute('CREATE INDEX IF NOT EXISTS orders_store_date255 ON orders(professional_id,created_at,id)')
  c.execute('CREATE INDEX IF NOT EXISTS adm227_entities_kind255 ON adm227_entities(kind,id)')
  c.commit()
def rows(c,kind):return [json.loads(r[0]) for r in c.execute('SELECT data FROM adm227_entities WHERE kind=? ORDER BY id',(kind,))]
def get(c,kind,oid):
 r=c.execute('SELECT data FROM adm227_entities WHERE kind=? AND id=?',(kind,int(oid))).fetchone();return json.loads(r[0]) if r else None
def put(c,kind,oid,obj):c.execute('INSERT INTO adm227_entities VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data',(kind,int(oid),json.dumps(obj,ensure_ascii=False,separators=(',',':'))))
def nextid(c,kind):return c.execute('SELECT COALESCE(MAX(id),0)+1 FROM adm227_entities WHERE kind=?',(kind,)).fetchone()[0]
def audit(c,a,action,target=''):c.execute('INSERT INTO adm227_audit(actor,actor_id,action,target,created_at) VALUES(?,?,?,?,?)',(a['name'],a['actor_id'],action[:500],str(target)[:120],stamp()))
def validate_staff255(member):
 if type(member.get('enabled')) is not bool:fail(400,'Situação da equipe inválida. Use ativo ou desativado.')
 permissions=member.get('permissions')
 if not isinstance(permissions,list) or any(not isinstance(p,str) or p not in MODULES for p in permissions):fail(400,'Permissões inválidas.')
 if len(permissions)!=len(set(permissions)):fail(400,'Permissões duplicadas.')

def revoke_staff255(c,staff_id):
 for table in ('adm227_team_sessions','adm227_challenges','adm227_invites'):
  c.execute('DELETE FROM '+table+' WHERE staff_id=?',(staff_id,))
 c.execute("UPDATE adm227_access SET end=?,state='Revogada' WHERE actor_id=? AND end=''",(stamp(),'staff:'+str(staff_id)))

def auth(request,c,module=None):
 u=G['current_user'](request)
 if u and u['role']=='admin':
  a={'id':u['id'],'actor_id':'admin:'+str(u['id']),'name':u['name'],'email':u['email'],'permissions':sorted(MODULES),'super':True,'session':tokenhash(request.cookies.get('nowup_session',''))}
 else:
  raw=request.cookies.get('nowup_team227','');s=c.execute('SELECT staff_id FROM adm227_team_sessions WHERE token_hash=? AND expires_at>?',(tokenhash(raw),stamp())).fetchone() if raw else None
  member=get(c,'staff',s[0]) if s else None
  if not member:fail(401,'Entre novamente para acessar o painel.')
  if member.get('enabled') is not True:fail(403,'Esta conta de equipe foi desativada.')
  validate_staff255(member)
  a={**{k:member.get(k,'') for k in ('id','name','email')},'actor_id':'staff:'+str(member['id']),'permissions':member.get('permissions',[]),'super':False,'session':tokenhash(raw)}
 if module and module not in a['permissions']:fail(403,'Seu acesso não inclui este módulo.')
 access=c.execute('SELECT id,end FROM adm227_access WHERE session_hash=?',(a['session'],)).fetchone()
 if access and access['end']:fail(401,'Esta sessão foi encerrada pelo administrador. Entre novamente.')
 if not access:
  c.execute('INSERT INTO adm227_access(actor_id,name,session_hash,start,last_activity) VALUES(?,?,?,?,?)',(a['actor_id'],a['name'],a['session'],stamp(),stamp()));audit(c,a,'Entrada no Super ADM')
 elif request.headers.get('x-nowup-activity')=='1':c.execute('UPDATE adm227_access SET last_activity=? WHERE id=?',(stamp(),access['id']))
 c.commit();return a
def csrf(request):
 from nowup_runtime238 import mutation_origin_allowed
 if not mutation_origin_allowed(request) or request.headers.get('x-nowup-admin')!='227':fail(403,'Origem não autorizada. Atualize o painel e tente novamente.')
def limited(c,key,limit=8):
 now=stamp();old=c.execute('SELECT * FROM adm227_limits WHERE key=?',(key,)).fetchone()
 if old and old['started']>(datetime.now(timezone.utc)-timedelta(minutes=15)).isoformat():
  if old['attempts']>=limit:fail(429,'Muitas tentativas. Aguarde 15 minutos.')
  c.execute('UPDATE adm227_limits SET attempts=attempts+1 WHERE key=?',(key,))
 else:c.execute('INSERT INTO adm227_limits VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET started=excluded.started,attempts=1',(key,now))
 c.commit()
def parts(v):
 try:
  t=datetime.fromisoformat(v.replace('Z','+00:00'));t=t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t;t=t.astimezone(TZ);return t.date().isoformat(),t.hour
 except (ValueError,TypeError):return '',0
def localminute(value):
 try:
  dt=datetime.fromisoformat(value.replace('Z','+00:00'));dt=dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
  return dt.astimezone(TZ).minute
 except (ValueError,TypeError,AttributeError):return 0
def localday():return datetime.now(TZ).date().isoformat()
def metadata(c,kind):return {v['id']:v for v in rows(c,kind)}
def public_staff(v):return {k:v.get(k) for k in ('id','name','email','role','photo','enabled','permissions')}
def order_page255(c,a,before_id=0,limit=200,exact_id=None):
 if not set(a['permissions']).intersection({'dashboard','orders','customers','stores'}):
  return {'orders':[],'nextBefore':None}
 if type(limit) is not int or not 1<=limit<=200 or type(before_id) is not int or before_id<0:fail(400,'Paginação inválida.')
 where='WHERE id=?' if exact_id is not None else ('WHERE id<?' if before_id else '')
 params=(exact_id,) if exact_id is not None else ((before_id,) if before_id else ())
 selected=list(c.execute('SELECT * FROM orders '+where+' ORDER BY id DESC LIMIT ?',(*params,limit+1)))
 more=len(selected)>limit;selected=selected[:limit];ids=[r['id'] for r in selected];items={};assignments={}
 if ids:
  marks=','.join('?' for _ in ids)
  for row in c.execute('SELECT order_id,product_name,quantity,unit_price_cents FROM order_items WHERE order_id IN ('+marks+') ORDER BY id',ids):
   items.setdefault(row['order_id'],[]).append({'name':row['product_name'],'qty':row['quantity'],'price':row['unit_price_cents']})
  for row in c.execute("SELECT id,data FROM adm227_entities WHERE kind='order_assignment' AND id IN ("+marks+')',ids):assignments[row['id']]=json.loads(row['data'])
 orders=[]
 for r in selected:
  d,h=parts(r['created_at']);orders.append({'id':r['id'],'store':r['professional_id'],'customer':r['customer_id'],'date':d,'hour':h,'minute':localminute(r['created_at']),'total':r['total_cents'],'delivery':r['delivery_fee_cents'],'status':r['status'],'live':r['status'] not in FINALS,'createdAt':r['created_at'],'items':items.get(r['id'],[]),'courier':assignments.get(r['id'],{}).get('courier'),'coupon':''})
 return {'orders':orders,'nextBefore':ids[-1] if more else None}

@router.get('/admin/super/api/orders-page')
def orders_page255(request:Request,before_id:int=0,limit:int=200):
 with connection() as c:
  a=auth(request,c);result=order_page255(c,a,before_id,limit)
  result['revision']=c.execute('SELECT revision FROM adm227_state WHERE id=1').fetchone()[0]
  return JSONResponse(result,headers={'Cache-Control':'private, no-store','Vary':'Cookie'})

def snapshot(c,a):
 permissions=set(a['permissions']);super_=a['super'];need=lambda *args:bool(permissions.intersection(args))
 raw_stores=[dict(r) for r in c.execute("""SELECT p.*,u.name owner,u.email,u.is_active,
 COALESCE(cat.name,'') category229,COALESCE(rating.value,0) rating229
 FROM professionals p JOIN users u ON u.id=p.user_id
 LEFT JOIN (SELECT pc.professional_id,MIN(c.name) name FROM professional_categories pc JOIN categories c ON c.id=pc.category_id GROUP BY pc.professional_id) cat ON cat.professional_id=p.id
 LEFT JOIN (SELECT professional_id,AVG(stars) value FROM reviews GROUP BY professional_id) rating ON rating.professional_id=p.id
 ORDER BY p.id""")]
 sm=metadata(c,'storemeta');stores=[];settings=json.loads(c.execute('SELECT settings FROM adm227_state WHERE id=1').fetchone()[0]);plans=rows(c,'plans')
 # Existing prices remain unknown unless explicitly registered. Never assign R$79 to an old contract.
 for p in raw_stores:
  m=sm.get(p['id'],{});st={'id':p['id'],'name':p['display_name'],'city':p['city'],'neighborhood':p['neighborhood'],'category':'','approval':p['admission_status'],'online':bool(p['is_active'] and not p['blocked'] and p['admission_status']=='approved' and G['shop_status'](p)['open']),'paused':p['business_status']!='open','blocked':bool(p['blocked'] or not p['is_active']),'demo':bool(p['is_demo']),'featured':bool(p['featured']),'plan':m.get('plan','legacy'),'price':m.get('price',0),'due':p['billing_due_date'],'trialUntil':m.get('trialUntil',''),'cancelledAt':m.get('cancelledAt',''),'subscribedAt':m.get('subscribedAt',p['created_at'][:10]),'method':m.get('method','Pix'),'menu':[],'stage':m.get('stage',{'approved':'Aprovados','pending':'Em Análise','rejected':'Reprovados'}.get(p['admission_status'],'Em Análise')),'prep':p['prep_minutes'],'rating':0,'hoursByDay':m.get('hoursByDay',['']*7),'resources':m.get('resources',[]),'kyc':m.get('kyc',{}),'documents':{},'radius':m.get('radius',0)}
  if need('stores'):
   st.update(owner=p['owner'],email=p['email'],phone=p['whatsapp'],document=p['document'],address=p['address'],hours=p['opening_hours'],photo='/uploads/'+p['avatar_filename'] if p['avatar_filename'] else '',slug=p['slug'],publicUrl='/p/'+p['slug'])
  else:st.update(owner='',email='',phone='',document='',address='',hours='',photo='')
  st['category']=p['category229'];st['rating']=round(p['rating229'],1)
  if not need('stores'):st.update(kyc={},documents={})
  if not need('finance','dashboard'):st.update(price=0,due='',trialUntil='',cancelledAt='',subscribedAt='')
  stores.append(st)
 if need('stores'):
  for lead in rows(c,'leads'):stores.append({'city':'','neighborhood':'','category':'','owner':'','email':'','phone':'','document':'','address':'','hours':'','photo':'','radius':0,'prep':30,'rating':0,'hoursByDay':['']*7,'resources':[],'kyc':{},'documents':{},'plan':'legacy','price':0,'due':'','trialUntil':'','cancelledAt':'','subscribedAt':'','method':'Pix','online':False,'paused':False,'blocked':False,'featured':False,**lead})
 products=[];store_by_id={s['id']:s for s in stores};raw_products=[dict(r) for r in c.execute('SELECT * FROM products ORDER BY id')] if need('products','stores') else [];pm=metadata(c,'productmeta') if raw_products else {}
 for r in raw_products:
  if not need('products','stores'):break
  date_,hour=parts(r['created_at']);store=store_by_id.get(r['professional_id'],{})
  products.append({'id':r['id'],'store':r['professional_id'],'name':r['name'],'price':r['price_cents'],'photo':bool(r['image_filename']),'category':r['category'],'status':pm.get(r['id'],{}).get('status','Aprovado' if r['available'] else 'Pausado'),'date':date_,'hour':hour,'city':store.get('city',''),'image':'/uploads/'+r['image_filename'] if r['image_filename'] else ''})
  store.get('menu',[]).append({'name':r['name'],'price':r['price_cents']})
 page255=order_page255(c,a);orders=page255['orders']
 customers=[];cm=metadata(c,'customermeta')
 if need('customers'):
  for u in c.execute("SELECT * FROM users WHERE role='customer' ORDER BY id"):
   m=cm.get(u['id'],{});customers.append({'id':u['id'],'name':u['name'],'phone':u['phone'],'cpf':m.get('cpf',''),'birth':m.get('birth',''),'ageVerified':m.get('ageVerified',False),'city':u['city'],'neighborhood':u['neighborhood'],'address':u['address'],'blocked':not bool(u['is_active']),'joined':u['created_at'][:10]})
 elif need('orders','dashboard','marketing'):customers=[{'id':r['id'],'name':'Cliente #'+str(r['id']),'city':r['city'],'neighborhood':r['neighborhood']} for r in c.execute("SELECT id,city,neighborhood FROM users WHERE role='customer'")]
 if need('marketing'):
  purchases={r['customer_id']:r['last_purchase'] for r in c.execute("SELECT customer_id,MAX(created_at) last_purchase FROM orders WHERE status='completed' GROUP BY customer_id")}
  for customer in customers:customer['lastPurchase229']=purchases.get(customer['id'],'')[:10]
 current_settings=dict(c.execute('SELECT key,value FROM site_settings').fetchall());categories=[r['name'] for r in c.execute('SELECT name FROM categories ORDER BY sort_order,id')]
 cities=sorted({s['city'] for s in stores if s['city']}|{v.strip() for v in current_settings.get('active_cities','Ubatuba').split(',') if v.strip()})
 config={'autoBlock':False,'deliveryPerKm':0,'minOrder':0,'platformHours':'','globalMessage':'','homeTitle':current_settings.get('hero_title',''),'homeText':current_settings.get('hero_subtitle',''),'cities':cities,'activeCities':current_settings.get('active_cities','Ubatuba').split(','),**settings}
 banners=[]
 if need('settings'):
  for b in c.execute('SELECT * FROM home_banners210 ORDER BY position,id'):banners.append({'id':b['id'],'title':b['title'],'desktop':b['image'],'mobile':'','link':'','enabled':bool(b['active']),'start':'','end':'','city':'Todas','neighborhood':''})
 staff=[public_staff(s) for s in rows(c,'staff')] if super_ else []
 access=[]
 if super_:
  for s in c.execute('SELECT * FROM adm227_access ORDER BY id DESC LIMIT 2000'):access.append({'id':s['id'],'employee':int(s['actor_id'].split(':')[1]) if s['actor_id'].startswith('staff:') else -int(s['actor_id'].split(':')[1]),'name':s['name'],'start':s['start'],'end':s['end'],'lastActivity':s['last_activity'],'state':s['state'],'device':'Sessão registrada no servidor'})
 logs=[{'id':r['id'],'actor':r['actor'],'action':r['action'],'date':r['created_at']} for r in c.execute('SELECT * FROM adm227_audit ORDER BY id DESC LIMIT 5000')] if need('system') or super_ else []
 result={'version':1,'operationsVersion':2,'profile':{'name':a['name'],'email':a['email'],'phone':'','cpf':'','photo':''},'plans':plans if need('finance','dashboard','stores') else [],'stores':stores,'orders':orders,'customers':customers,'products':products,'categories':categories,'banners':banners,'settings':config,'sessions':access,'logs':logs,'staff':staff,'errors':[],'integrations':{'payments':'Não conectado','whatsapp':False,'push':False},'reports':[]}
 for kind,module in KINDS.items():
  if kind in ('leads','storemeta','productmeta','customermeta','staff'):continue
  if kind not in result:result[kind]=rows(c,kind) if module in permissions else []
 result['productCategories']=[x['name'] for x in rows(c,'productCategories')] if need('products') else []
 result['_meta']={'revision':c.execute('SELECT revision FROM adm227_state WHERE id=1').fetchone()[0],'actor':{k:a[k] for k in ('id','name','email','super','permissions')},'live':True,'unsupported':['gateway','whatsapp_api','push_campaign','automatic_billing_block','public_coupons','referrals_credit','theme_scheduler','assisted_login','kyc_provider','background_jobs'],'fetchedAt':stamp(),'orderPagination255':{'nextBefore':page255['nextBefore'],'pageSize':200}}
 return result

@router.get('/admin/super')
def page(request:Request):
 with connection() as c:
  try:auth(request,c)
  except HTTPException:return RedirectResponse('/admin/super/equipe/entrar',303)
 return FileResponse(Path(__file__).parent/'static'/'adm227'/'index.html',headers={'Cache-Control':'private, no-store'})
@router.get('/admin/super/api/state')
def state(request:Request):
 with connection() as c:a=auth(request,c);return JSONResponse(snapshot(c,a),headers={'Cache-Control':'private, no-store','Vary':'Cookie'})

@router.post('/admin/super/api/heartbeat')
def heartbeat(request:Request):
 csrf(request)
 with connection() as c:auth(request,c);c.commit()
 return {'ok':True}

def clean(v,maximum=300,required=False):
 if not isinstance(v,str) or len(v)>maximum or required and not v.strip():fail(400,'Campo textual inválido.')
 return v.strip()
def number(v,lo=0,hi=100000000):
 if isinstance(v,bool) or not isinstance(v,(int,float)) or int(v)!=v or not lo<=v<=hi:fail(400,'Valor numérico inválido.')
 return int(v)
def validdate(v,optional=True):
 if optional and not v:return ''
 try:date.fromisoformat(v)
 except (TypeError,ValueError):fail(400,'Data inválida.')
 return v
def image(c,a,value):
 if not value:return ''
 if not isinstance(value,str):fail(400,'Imagem inválida.')
 if value.startswith('/uploads/'):return value[len('/uploads/'):]
 if not value.startswith('data:image/'):fail(400,'Envie PNG, JPG ou WebP.')
 from PIL import Image,ImageOps,UnidentifiedImageError
 try:
  header,payload=value.split(',',1);raw=base64.b64decode(payload,validate=True)
  if len(raw)>750000:fail(400,'Imagem acima do limite de 750 KB.')
  im=Image.open(io.BytesIO(raw))
  if im.width*im.height>16000000:fail(400,'Dimensões da imagem acima do limite.')
  im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((1800,1800));name='adm227-'+secrets.token_hex(12)+'.jpg';im.save(G['UPLOAD_DIR']/name,'JPEG',quality=85);return name
 except (ValueError,OSError,UnidentifiedImageError):fail(400,'Não foi possível ler a imagem.')

def update_store(c,a,oid,v,why):
 p=c.execute('SELECT * FROM professionals WHERE id=?',(oid,)).fetchone()
 if not p:
  lead=get(c,'leads',oid)
  if lead is not None:
   allowed={'name','owner','city','neighborhood','stage','approval','phone','document','address','radius','prep','hoursByDay','kyc'}
   if set(v)-allowed:fail(400,'Alteração indisponível para lead.')
   lead.update(v);put(c,'leads',oid,lead);return
  fail(404,'Loja não encontrada.')
 allowed={'name','city','neighborhood','phone','document','address','radius','prep','hours','hoursByDay','owner','stage','approval','paused','blocked','blockReason','featured','kyc','documents','plan','price','due','trialUntil','cancelledAt','subscribedAt','method','resources','email','photo','menu','category'}
 if set(v)-allowed:fail(400,'Campo de loja não permitido.')
 if set(v)&{'plan','price','due','trialUntil','cancelledAt','method','subscribedAt'} and 'finance' not in a['permissions']:fail(403,'Permissão Financeiro necessária.')
 if 'email' in v:fail(400,'A troca de e-mail exige o fluxo de confirmação do cadastro atual.')
 if 'menu' in v:fail(400,'Cadastre produtos pelo painel da loja; os adicionais existentes precisam ser preservados.')
 if 'resources' in v:fail(400,'Os recursos seguem as regras atuais do plano. A troca de botões exige integração específica.')
 if 'documents' in v:fail(400,'O armazenamento privado de KYC ainda não está configurado.')
 m=get(c,'storemeta',oid) or {'id':oid};columns={}
 for key,col in {'name':'display_name','city':'city','neighborhood':'neighborhood','phone':'whatsapp','document':'document','address':'address','hours':'opening_hours','owner':None}.items():
  if key in v:
   val=clean(v[key],500, key in {'name','city','owner'})
   if col:columns[col]=val
   if key=='owner':c.execute('UPDATE users SET name=? WHERE id=?',(val,p['user_id']))
 if 'photo' in v:columns['avatar_filename']=image(c,a,v['photo'])
 if 'prep' in v:columns['prep_minutes']=number(v['prep'],1,240)
 if 'radius' in v:m['radius']=number(v['radius'],0,100)
 for key in ('paused','blocked','featured'):
  if key in v:
   if type(v[key]) is not bool:fail(400,'Situação inválida.')
   columns[{'paused':'business_status','blocked':'blocked','featured':'featured'}[key]]= ('paused' if v[key] else 'open') if key=='paused' else int(v[key])
 if 'stage' in v:
  if v['stage'] not in ('Docs Enviados','Em Análise','Aprovados','Reprovados','Leads'):fail(400,'Etapa inválida.')
  m['stage']=v['stage'];columns['admission_status']={'Aprovados':'approved','Reprovados':'rejected'}.get(v['stage'],'pending')
 if 'approval' in v:
  if v['approval'] not in ('approved','pending','rejected'):fail(400,'Aprovação inválida.')
  columns['admission_status']=v['approval']
 if columns.get('admission_status')=='rejected' or columns.get('blocked')==1:
  if len(why.strip())<8:fail(400,'Informe justificativa para bloquear ou reprovar.')
  columns['admission_reason']=why[:500]
 if 'due' in v:columns['billing_due_date']=validdate(v['due'])
 if 'plan' in v:
  plan=next((x for x in rows(c,'plans') if x['id']==v['plan']),None)
  if not plan:fail(400,'Plano SaaS não encontrado.')
  m.update(plan=plan['id'],price=plan['price'],subscribedAt=m.get('subscribedAt',localday()))
  # Commercial price does not silently alter cardápio/vitrine entitlements.
 if 'price' in v and 'plan' not in v:m['price']=number(v['price'])
 for key in ('trialUntil','cancelledAt','subscribedAt'):
  if key in v:m[key]=validdate(v[key])
 if 'method' in v:
  if v['method'] not in ('Pix','Cartão'):fail(400,'Forma de pagamento inválida.')
  m['method']=v['method']
 if 'hoursByDay' in v:
  if not isinstance(v['hoursByDay'],list) or len(v['hoursByDay'])!=7:fail(400,'Informe os sete dias da semana.')
  m['hoursByDay']=[clean(s,40) for s in v['hoursByDay']]
 if 'kyc' in v:fail(400,'KYC real ainda não está configurado; não marque documentos como verificados por esta tela.')
 if 'category' in v:
  cat=c.execute('SELECT id FROM categories WHERE name=? AND active=1',(clean(v['category'],120),)).fetchone()
  if not cat:fail(400,'Categoria de loja não encontrada.')
  c.execute('DELETE FROM professional_categories WHERE professional_id=?',(oid,));c.execute('INSERT INTO professional_categories VALUES(?,?)',(oid,cat[0]))
 if columns:c.execute('UPDATE professionals SET '+','.join(k+'=?' for k in columns)+' WHERE id=?',(*columns.values(),oid))
 put(c,'storemeta',oid,m)

def update_order(c,a,oid,v,why):
 if set(v)-{'status','courier'}:fail(400,'Campo do pedido não permitido.')
 o=c.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
 if not o:fail(404,'Pedido não encontrado.')
 if 'status' in v and v['status']!=o['status']:
  target=v['status'];allowed={'new','reviewing','confirmed','preparing','ready','out_for_delivery','completed','cancelled','rejected'}
  if target not in allowed:fail(400,'Situação inválida.')
  if o['status'] in FINALS:fail(409,'Pedido encerrado: a situação não pode ser reaberta.')
  if o['status']=='awaiting_approval' and target not in {'cancelled','rejected'}:fail(409,'Aguarde a aprovação do cliente.')
  if o['status'] in {'new','reviewing','revision_approved'} and target not in {'reviewing','confirmed','cancelled','rejected'}:fail(409,'Confirme o pedido antes de iniciar o preparo.')
  rank={'new':0,'reviewing':0,'revision_approved':0,'confirmed':1,'preparing':2,'ready':3,'out_for_delivery':4,'completed':5}
  if target in rank and rank[target]<rank.get(o['status'],0):fail(409,'Não é permitido voltar etapas do pedido.')
  if target in {'cancelled','rejected'} and len(why.strip())<8:fail(400,'Justifique o cancelamento.')
  c.execute('UPDATE orders SET status=?,cancellation_reason=?,updated_at=? WHERE id=?',(target,why[:300] if target in {'cancelled','rejected'} else '',stamp(),oid));c.execute('INSERT INTO order_status_history(order_id,status,created_at) VALUES(?,?,?)',(oid,target,stamp()))
  if o['customer_id']:
   message='Seu pedido foi atualizado pela equipe NowUp: '+G['ORDER_STATUS_LABELS'].get(target,target)+'.'
   n=c.execute('INSERT INTO notifications(user_id,title,message,link,created_at) VALUES(?,?,?,?,?)',(o['customer_id'],'Atualização do pedido',message,'/pedido/'+o['tracking_token'],stamp()))
   G['nowup_alerts112'].enqueue(c,o['customer_id'],n.lastrowid,{'title':'Atualização do pedido','body':message,'url':'/pedido/'+o['tracking_token'],'tag':'nowup-status-'+str(oid)})
 if 'courier' in v:
  courier=0 if v['courier'] is None else number(v['courier'],0)
  if courier and not get(c,'couriers',courier):fail(400,'Entregador não cadastrado.')
  put(c,'order_assignment',oid,{'id':oid,'courier':courier})

def update_customer(c,a,oid,v):
 if set(v)-{'name','phone','address','blocked','cpf','birth','ageVerified'}:fail(400,'Campo de cliente não permitido.')
 u=c.execute("SELECT * FROM users WHERE id=? AND role='customer'",(oid,)).fetchone()
 if not u:fail(404,'Cliente não encontrado.')
 if {'cpf','birth','ageVerified'}&set(v):fail(400,'Verificação documental +18 não conectada. Não é possível registrar comprovação por este formulário.')
 for key in ('name','phone','address'):
  if key in v:c.execute('UPDATE users SET '+key+'=? WHERE id=?',(clean(v[key],300,key=='name'),oid))
 if 'blocked' in v:
  if type(v['blocked']) is not bool:fail(400,'Bloqueio inválido.')
  c.execute('UPDATE users SET is_active=? WHERE id=?',(int(not v['blocked']),oid))
  if v['blocked']:c.execute('DELETE FROM sessions WHERE user_id=?',(oid,))

def update_product(c,a,oid,v,why):
 if set(v)-{'name','price','category','status','photo'}:fail(400,'Campo de produto não permitido.')
 r=c.execute('SELECT * FROM products WHERE id=?',(oid,)).fetchone()
 if not r:fail(404,'Produto não encontrado.')
 if 'photo' in v and bool(v['photo'])!=bool(r['image_filename']):fail(400,'Foto real exige envio do arquivo pelo editor do produto.')
 name=clean(v.get('name',r['name']),140,True);price=number(v.get('price',r['price_cents']));cat=clean(v.get('category',r['category']),80,True);status=v.get('status','Aprovado' if r['available'] else 'Pausado')
 if status not in ('Aprovado','Reprovado','Pendente','Pausado'):fail(400,'Moderação inválida.')
 if status=='Aprovado' and price<=0:fail(400,'Informe o preço antes de aprovar.')
 c.execute('UPDATE products SET name=?,price_cents=?,category=?,available=?,updated_at=? WHERE id=?',(name,price,cat,int(status=='Aprovado'),stamp(),oid));put(c,'productmeta',oid,{'id':oid,'status':status})

def update_entity(c,a,kind,oid,v,creating,why):
 if kind not in KINDS:fail(400,'Tipo de cadastro não permitido.')
 module=KINDS[kind]
 if module not in a['permissions']:fail(403,'Seu acesso não inclui '+module+'.')
 if kind in {'storemeta','productmeta','customermeta','leads'}:fail(400,'Use a operação específica do cadastro.')
 if kind in {'campaigns','referrals'}:fail(409,'Envio de campanha e créditos por indicação ainda não integrados. Nenhuma mensagem ou crédito foi criado.')
 if kind=='staff':fail(400,'Use a operação própria para funcionários.')
 if kind=='plans':
  if set(v)-{'id','name','price','features'}:fail(400,'Campo de plano inválido.')
  v={**v,'name':clean(v.get('name',''),60,True),'price':number(v.get('price'),1)}
 if kind=='payments':
  if not creating:fail(409,'Pagamentos registrados não podem ser sobrescritos.')
  if set(v)-{'id','store','date','amount','method','reference'}:fail(400,'Campo de pagamento inválido.')
  if not c.execute('SELECT 1 FROM professionals WHERE id=? AND is_demo=0',(number(v.get('store')),)).fetchone():fail(400,'Loja real não encontrada.')
  v.update(amount=number(v.get('amount'),1),date=validdate(v.get('date'),False),reference=clean(v.get('reference',''),150,True))
  if v['date']>localday():fail(400,'Pagamento não pode estar no futuro.')
  if v.get('method') not in ('Pix','Cartão'):fail(400,'Forma inválida.')
 if kind=='couriers':
  if set(v)-{'id','name','phone','vehicle','plate','enabled','neighborhood'}:fail(400,'Campo de entregador inválido.')
  clean(v.get('name',''),100,True);clean(v.get('phone',''),30)
 if kind=='deliveryRules':
  if set(v)-{'id','city','neighborhood','perKm','fixed','eta'}:fail(400,'Região inválida.')
  for k in ('city','neighborhood'):clean(v.get(k,''),100,True)
  for k in ('perKm','fixed'):number(v.get(k),0,100000)
  number(v.get('eta'),1,240)
 if kind in {'coupons','billingCoupons','themes','tickets'}:
  if len(json.dumps(v))>2000000:fail(400,'Cadastro muito grande.')
  if kind=='tickets':
   if v.get('status') not in ('Aberto','Em atendimento','Resolvido'):fail(400,'Situação do chamado inválida.')
   clean(v.get('reason',''),150,True)
   if not c.execute('SELECT 1 FROM professionals WHERE id=?',(number(v.get('store')),)).fetchone():fail(400,'Loja não encontrada.')
   old=get(c,'tickets',oid) if not creating else None
   previous=old.get('messages',[]) if old else []
   incoming=v.get('messages',[])
   if not isinstance(incoming,list) or incoming[:len(previous)]!=previous or len(incoming)>len(previous)+1:fail(409,'Mensagens anteriores devem ser preservadas.')
   for m in incoming:clean(m.get('body',''),1500,True)
   if len(incoming)>len(previous):incoming[-1].update(actor=a['name'],date=stamp())
  if kind=='themes':
   clean(v.get('name',''),100,True)
   for k in ('primary','accent'):
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',v.get(k,'')):fail(400,'Cor inválida.')
   if v.get('start','')>=v.get('end',''):fail(400,'Confira as datas do tema.')
   for k in ('logo','banner'):
    if v.get(k):v[k]='/uploads/'+image(c,a,v[k])
  if kind in ('coupons','billingCoupons'):
   if not re.fullmatch(r'[A-Z0-9_-]{3,24}',v.get('code','')):fail(400,'Código de cupom inválido.')
   if any(x.get('code')==v['code'] and x.get('id')!=v.get('id') for x in rows(c,kind)):fail(409,'Código já cadastrado.')
   if kind=='coupons' and v.get('type')=='percent' and not 0<float(v.get('value',0))<=100:fail(400,'Percentual inválido.')
 if creating:oid=nextid(c,kind);v['id']=oid
 put(c,kind,oid,v)

@router.post('/admin/super/api/change')
async def change(request:Request):
 csrf(request)
 if int(request.headers.get('content-length','0') or 0)>5000000:fail(413,'Requisição acima do limite.')
 try:body=await request.json()
 except ValueError:fail(400,'Conteúdo inválido.')
 if not isinstance(body,dict) or not isinstance(body.get('changes'),list) or len(body['changes'])>50:fail(400,'Alterações inválidas.')
 why=clean(body.get('reason',''),500,True)
 with connection() as c:
  a=auth(request,c);c.execute('BEGIN IMMEDIATE');current=snapshot(c,a)
  if body.get('revision')!=current['_meta']['revision']:fail(409,'Outro usuário alterou o painel. Atualize e tente novamente.')
  for op in body['changes']:
   if not isinstance(op,dict):fail(400,'Operação inválida.')
   kind=op.get('kind');v=op.get('value');before=op.get('before');creating=op.get('create') is True
   if not isinstance(v,dict):fail(400,'Campos inválidos.')
   oid=op.get('id',0)
   if kind=='staff' and not a['super']:fail(403,'Somente o Super Admin pode gerenciar funcionários.')
   if kind in {'stores','orders','customers','products','banners','staff','sessions'} and not creating:
    original=next((r for r in current[kind] if r['id']==oid),None)
    if not original and kind=='orders' and 'orders' in a['permissions']:
     found=order_page255(c,a,exact_id=number(oid,1))['orders'];original=found[0] if found else None
    if not original:fail(404,'Registro não disponível para seu acesso.')
    if any(original.get(k)!=val for k,val in (before or {}).items()):fail(409,'Este registro mudou. Atualize antes de salvar.')
   if kind=='stores':
    if 'stores' not in a['permissions'] and 'finance' not in a['permissions'] and 'support' not in a['permissions']:fail(403,'Sem permissão para lojas.')
    if 'stores' not in a['permissions'] and 'finance' in a['permissions'] and set(v)-{'plan','price','due','trialUntil','cancelledAt','subscribedAt','method'}:fail(403,'Financeiro não pode editar o cadastro da loja.')
    if 'stores' not in a['permissions'] and 'finance' not in a['permissions'] and set(v)-{'paused','blocked','blockReason'}:fail(403,'Suporte só pode pausar ou bloquear com justificativa.')
    if creating:
     # Lead is not a published store. A merchant must complete the existing signup flow.
     if v.get('demo'):fail(409,'Crie perfis fictícios no editor atual; eles serão preservados.')
     lid=max(1000000000,nextid(c,'leads'));v.update(id=lid,stage='Leads',approval='pending',demo=False,price=0,menu=[]);put(c,'leads',lid,v)
    else:update_store(c,a,number(oid,1),v,why)
   elif kind=='orders':
    if 'orders' not in a['permissions'] or creating:fail(403,'Sem permissão para pedidos.')
    update_order(c,a,number(oid,1),v,why)
   elif kind=='customers':
    if 'customers' not in a['permissions'] or creating:fail(403,'Sem permissão para clientes.')
    update_customer(c,a,number(oid,1),v)
   elif kind=='products':
    if 'products' not in a['permissions'] or creating:fail(403,'Sem permissão para produtos.')
    update_product(c,a,number(oid,1),v,why)
   elif kind=='banners':
    if 'settings' not in a['permissions']:fail(403,'Sem permissão para banners.')
    if set(v)-{'title','enabled','desktop'}:fail(409,'Somente imagem, título e situação dos banners atuais são suportados nesta etapa.')
    if creating:
     if c.execute('SELECT COUNT(*) FROM home_banners210').fetchone()[0]>=20:fail(400,'Limite de 20 banners.')
     title=clean(v.get('title',''),140,True);filename=image(c,a,v.get('desktop',''))
     if not filename:fail(400,'Envie a imagem do banner.')
     c.execute('INSERT INTO home_banners210(title,image,active,position) VALUES(?,?,?,?)',(title,'/uploads/'+filename,1,c.execute('SELECT COALESCE(MAX(position),0)+1 FROM home_banners210').fetchone()[0]))
    else:
     columns={}
     if 'title' in v:columns['title']=clean(v['title'],140,True)
     if 'enabled' in v:
      if type(v['enabled']) is not bool:fail(400,'Situação inválida.')
      columns['active']=int(v['enabled'])
     if 'desktop' in v:columns['image']='/uploads/'+image(c,a,v['desktop'])
     if columns:c.execute('UPDATE home_banners210 SET '+','.join(k+'=?' for k in columns)+' WHERE id=?',(*columns.values(),oid))
   elif kind=='categories':
    if 'settings' not in a['permissions']:fail(403,'Sem permissão para categorias.')
    names=v.get('items')
    if not isinstance(names,list) or len(names)!=len(current['categories']) or set(names)!=set(current['categories']):fail(400,'A reordenação deve preservar todas as categorias atuais.')
    for i,name in enumerate(names):c.execute('UPDATE categories SET sort_order=? WHERE name=?',(i,name))
   elif kind=='settings':
    if not a['super']:fail(403,'Configuração global exige Super ADM.')
    if v.get('autoBlock') is True:fail(409,'O bloqueio automático por cobrança exige gateway e validação antes de ativar.')
    if set(v)&{'deliveryPerKm','minOrder'}:fail(409,'As regras de entrega continuam por loja; configure no painel de cada loja.')
    cfg=json.loads(c.execute('SELECT settings FROM adm227_state WHERE id=1').fetchone()[0]);cfg.update(v)
    for key,target in [('homeTitle','hero_title'),('homeText','hero_subtitle')]:
     if key in v:c.execute('INSERT INTO site_settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(target,clean(v[key],600)))
    if 'activeCities' in v:
     if not isinstance(v['activeCities'],list) or not v['activeCities']:fail(400,'Mantenha pelo menos uma cidade ativa.')
     c.execute("INSERT INTO site_settings VALUES('active_cities',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(','.join(clean(x,100,True) for x in v['activeCities']),))
    c.execute('UPDATE adm227_state SET settings=? WHERE id=1',(json.dumps(cfg,ensure_ascii=False),))
   elif kind=='staff':
    if not a['super']:fail(403,'Somente Super ADM gerencia funcionários.')
    allowed={'name','email','role','photo','enabled','permissions'}
    if set(v)-allowed:fail(400,'Campo de funcionário inválido.')
    member={} if creating else get(c,'staff',oid)
    old_email=member.get('email','')
    member.update(v)
    if creating:member.setdefault('enabled',True)
    validate_staff255(member)
    member['name']=clean(member.get('name',''),100,True);member['email']=clean(member.get('email',''),200,True).lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',member['email']):fail(400,'E-mail inválido.')
    if any(x['email']==member['email'] and x['id']!=oid for x in rows(c,'staff')):fail(409,'E-mail já cadastrado.')
    if v.get('photo'):member['photo']='/uploads/'+image(c,a,v['photo'])
    if creating:
     oid=nextid(c,'staff');member.update(id=oid,password_hash='')
    put(c,'staff',oid,member)
    if member['enabled'] is False or (old_email and old_email!=member['email']):revoke_staff255(c,oid)
   elif kind=='sessions':
    if not a['super'] or creating or set(v)-{'end','state'}:fail(403,'Ação de sessão não permitida.')
    row=c.execute('SELECT * FROM adm227_access WHERE id=?',(oid,)).fetchone()
    c.execute("UPDATE adm227_access SET end=?,state='Revogada' WHERE id=?",(stamp(),oid));__import__('nowup_security').revoke_session(c,row['session_hash'])
    # Super-admin session is also denied at auth(), even if the original opaque token remains.
   elif kind=='profile':fail(400,'Use /admin/perfil para alterar o perfil com o fluxo atual de segurança.')
   elif kind=='productCategories':
    if 'products' not in a['permissions']:fail(403,'Sem permissão para categorias de produto.')
    items=v.get('items',[])
    if not isinstance(items,list) or len(items)>100 or any(not isinstance(n,str) or not n.strip() or len(n)>80 for n in items):fail(400,'Categorias inválidas.')
    c.execute("DELETE FROM adm227_entities WHERE kind='productCategories'")
    for i,n in enumerate(items,1):put(c,'productCategories',i,{'id':i,'name':n.strip()})
   else:
    original=next((r for r in current.get(kind,[]) if str(r.get('id'))==str(oid)),{})
    # Plan ids are commercial strings; persistence uses stable numeric keys.
    merged={**original,**v}
    if kind=='plans':oid=next((i+1 for i,r in enumerate(current['plans']) if r['id']==op.get('id')),0)
    update_entity(c,a,kind,number(oid,0),merged,creating,why)
  audit(c,a,why,','.join(str(o.get('kind'))+':'+str(o.get('id','novo')) for o in body['changes']))
  c.execute('UPDATE adm227_state SET revision=revision+1 WHERE id=1');c.commit();return JSONResponse(snapshot(c,a),headers={'Cache-Control':'no-store'})

@router.post('/admin/super/api/invite/{staff_id}')
def invite(request:Request,staff_id:int):
 csrf(request)
 with connection() as c:
  a=auth(request,c,'staff')
  if not a['super']:fail(403,'Somente Super ADM emite convites.')
  member=get(c,'staff',staff_id)
  if not member or not member['enabled']:fail(404,'Funcionário não encontrado.')
  raw=secrets.token_urlsafe(32);c.execute('DELETE FROM adm227_invites WHERE staff_id=?',(staff_id,));c.execute('INSERT INTO adm227_invites VALUES(?,?,?)',(tokenhash(raw),staff_id,(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat()));audit(c,a,'Convite individual de acesso emitido',staff_id);c.commit()
  return {'url':'/admin/super/equipe/ativar?token='+raw,'expiresInHours':24}

def form_page(title,body,error=''):
 return HTMLResponse('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>body{background:#101522;color:#e5e8f4;font:16px system-ui;margin:0;padding:30px}main{max-width:420px;margin:8vh auto;background:#1a2233;padding:26px;border-radius:14px}label{display:block;margin:16px 0}input{box-sizing:border-box;width:100%;padding:13px;margin-top:8px;border:1px solid #46506a;border-radius:7px;background:#101522;color:white}button,a{display:block;margin-top:18px;color:white}button{padding:13px;background:#8951c9;border:0;border-radius:7px;width:100%;font-size:16px}p{color:#adb7ce;line-height:1.6}</style><main><h1>'+html.escape(title)+'</h1>'+('<p role="alert">'+html.escape(error)+'</p>' if error else '')+body+'</main></html>',headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
@router.get('/admin/super/equipe/ativar')
def activation(request:Request,token:str=''):
 with connection() as c:r=c.execute('SELECT staff_id FROM adm227_invites WHERE token_hash=? AND expires_at>?',(tokenhash(token),stamp())).fetchone()
 if not r:return form_page('Convite inválido','<p>Peça um novo convite ao administrador.</p>')
 return form_page('Ativar acesso da equipe','<p>Crie uma senha de pelo menos 12 caracteres. Nunca envie sua senha por mensagem.</p><form method="post"><input type="hidden" name="token" value="'+html.escape(token,quote=True)+'"><label>Nova senha<input name="password" type="password" autocomplete="new-password" minlength="12" required></label><button>Ativar acesso</button></form>')
@router.post('/admin/super/equipe/ativar')
def activate(request:Request,token:str=Form(...),password:str=Form(...)):
 if not 12<=len(password)<=128:fail(400,'Use de 12 a 128 caracteres.')
 with connection() as c:
  c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT staff_id FROM adm227_invites WHERE token_hash=? AND expires_at>?',(tokenhash(token),stamp())).fetchone()
  if not r:fail(400,'Convite expirado ou já utilizado.')
  m=get(c,'staff',r[0])
  if not m or not m['enabled']:fail(403,'Acesso desativado.')
  m['password_hash']=G['hash_password'](password);put(c,'staff',m['id'],m);c.execute('DELETE FROM adm227_invites WHERE staff_id=?',(m['id'],));c.execute('DELETE FROM adm227_team_sessions WHERE staff_id=?',(m['id'],));c.commit()
 return RedirectResponse('/admin/super/equipe/entrar?ativado=1',303)
@router.get('/admin/super/equipe/entrar')
def team_entry(request:Request):
 return form_page('Entrar na equipe NowUp','<form method="post"><label>E-mail<input name="email" type="email" autocomplete="username" required></label><label>Senha<input name="password" type="password" autocomplete="current-password" required></label><button>Receber código por e-mail</button></form><a href="/entrar?tipo=admin">Sou Super ADM</a><p>O código de confirmação exige o envio de e-mail configurado no servidor.</p>')
@router.post('/admin/super/equipe/entrar')
def team_login(request:Request,email:str=Form(...),password:str=Form(...)):
 with connection() as c:
  limited(c,'login:'+tokenhash(email.strip().lower())+':'+tokenhash(request.client.host if request.client else ''))
  m=next((s for s in rows(c,'staff') if s['email']==email.strip().lower() and s['enabled']),None)
  if not m or not G['verify_password'](password,m.get('password_hash','')):return form_page('Acesso não confirmado','<a href="/admin/super/equipe/entrar">Tentar novamente</a>','Confira o e-mail e a senha.')
  challenge=secrets.token_urlsafe(32);code=f'{secrets.randbelow(1000000):06d}';c.execute('DELETE FROM adm227_challenges WHERE staff_id=?',(m['id'],));c.execute('INSERT INTO adm227_challenges(challenge_hash,staff_id,code_hash,expires_at) VALUES(?,?,?,?)',(tokenhash(challenge),m['id'],tokenhash(code),(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()));c.commit()
  sent=G['send_email'](m['email'],m['name'],'Código de acesso da equipe NowUp','<p>Seu código de acesso é <strong>'+code+'</strong>. Expira em 10 minutos.</p>')
  if not sent:
   c.execute('DELETE FROM adm227_challenges WHERE staff_id=?',(m['id'],));c.commit();return form_page('Envio indisponível','<p>Não foi possível enviar o código. Consulte o administrador.</p>')
  resp=RedirectResponse('/admin/super/equipe/codigo',303);resp.set_cookie('nowup_team_challenge227',challenge,max_age=600,httponly=True,secure=request.url.scheme=='https' or G['os'].getenv('NOWUP_HTTPS')=='1',samesite='lax',path='/admin/super');return resp
@router.get('/admin/super/equipe/codigo')
def code_page():return form_page('Confirme seu acesso','<form method="post"><label>Código recebido por e-mail<input name="code" inputmode="numeric" pattern="[0-9]{6}" autocomplete="one-time-code" required></label><button>Entrar</button></form>')
@router.post('/admin/super/equipe/codigo')
def code_submit(request:Request,code:str=Form(...)):
 ch=tokenhash(request.cookies.get('nowup_team_challenge227',''))
 with connection() as c:
  c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM adm227_challenges WHERE challenge_hash=?',(ch,)).fetchone()
  if not r or r['expires_at']<=stamp() or r['attempts']>=5:fail(401,'Código expirado. Entre novamente.')
  if not hmac.compare_digest(tokenhash(code),r['code_hash']):
   c.execute('UPDATE adm227_challenges SET attempts=attempts+1 WHERE challenge_hash=?',(ch,));c.commit();fail(401,'Código não confirmado.')
  member=get(c,'staff',r['staff_id'])
  if not member or not member['enabled']:fail(403,'Acesso desativado.')
  raw=secrets.token_urlsafe(32);c.execute('INSERT INTO adm227_team_sessions VALUES(?,?,?)',(tokenhash(raw),r['staff_id'],(datetime.now(timezone.utc)+timedelta(hours=8)).isoformat()));c.execute('DELETE FROM adm227_challenges WHERE challenge_hash=?',(ch,));c.commit()
  resp=RedirectResponse('/admin/super',303);resp.set_cookie('nowup_team227',raw,max_age=28800,httponly=True,secure=request.url.scheme=='https' or G['os'].getenv('NOWUP_HTTPS')=='1',samesite='lax',path='/admin/super');resp.delete_cookie('nowup_team_challenge227',path='/admin/super');return resp
@router.post('/admin/super/api/logout')
def logout(request:Request):
 csrf(request)
 with connection() as c:
  a=auth(request,c);c.execute("UPDATE adm227_access SET end=?,state='Deslogado' WHERE session_hash=?",(stamp(),a['session']));__import__('nowup_security').revoke_session(c,a['session']);audit(c,a,'Saída do Super ADM');c.commit()
 resp=JSONResponse({'ok':True,'next':'/admin/super/equipe/entrar'});resp.delete_cookie('nowup_team227',path='/admin/super');return resp
