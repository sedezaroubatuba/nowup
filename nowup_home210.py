"""Banners da página inicial — gestão exclusiva do administrador."""
from contextlib import closing
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
router = APIRouter()
G = {}
def configure(g):
    G.update(g)
    with closing(G['db']()) as c, c:
        c.executescript('''CREATE TABLE IF NOT EXISTS home_settings210(id INTEGER PRIMARY KEY CHECK(id=1), seconds INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS home_banners210(id INTEGER PRIMARY KEY,title TEXT NOT NULL,image TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,position INTEGER NOT NULL DEFAULT 0);
INSERT OR IGNORE INTO home_settings210 VALUES(1,1);''')
        for name,definition in [('kind498',"TEXT NOT NULL DEFAULT 'general'"),('store498',"TEXT NOT NULL DEFAULT ''"),('start498',"TEXT NOT NULL DEFAULT ''"),('end498',"TEXT NOT NULL DEFAULT ''")]:
            G['ensure_column'](c,'home_banners210',name,definition)
        # Marker survives deletion of every banner; never recreate a deleted image.
        c.execute('CREATE TABLE IF NOT EXISTS home_seed210(id INTEGER PRIMARY KEY)')
        if not c.execute('SELECT 1 FROM home_seed210 WHERE id=1').fetchone():
            c.execute("INSERT INTO home_banners210(title,image) VALUES(?,?)",('Descubra o melhor de Ubatuba','/static/nowup-ubatuba210.png'))
            c.execute('INSERT INTO home_seed210 VALUES(1)')
def admin(request):
    G['require_user'](request,'admin')
    if request.method=='POST':
        from urllib.parse import urlparse
        source=request.headers.get('origin') or request.headers.get('referer')
        if not source or urlparse(source).netloc != request.url.netloc:
            raise HTTPException(403,'Atualize a página antes de salvar')
def number(value,lo,hi):
    try:n=int(value)
    except (ValueError,TypeError):raise HTTPException(400,'Informe um número inteiro')
    if not lo<=n<=hi:raise HTTPException(400,f'Informe um valor entre {lo} e {hi}')
    return n
def active_banners(c):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today=datetime.now(ZoneInfo('America/Sao_Paulo')).date().isoformat()
    return [dict(r) for r in c.execute('''SELECT * FROM home_banners210 WHERE active=1
        AND (start498='' OR start498<=?) AND (end498='' OR end498>=?)
        AND (store498='' OR EXISTS (SELECT 1 FROM professionals p WHERE p.slug=store498 AND p.blocked=0 AND p.admission_status='approved' AND p.plan_active IN ('vitrine','ambos','completo')))
        ORDER BY position,id''',(today,today))]

@router.get('/api/home-banners210')
def feed():
    with closing(G['db']()) as c:
        items=[{k:b[k] for k in ('id','title','image')} for b in active_banners(c) if b['kind498']=='general']
        seconds=c.execute('SELECT seconds FROM home_settings210 WHERE id=1').fetchone()[0]
    return JSONResponse({'seconds':seconds,'items':items},headers={'Cache-Control':'no-store'})
@router.get('/admin/banners-inicio')
def editor(request:Request):
    admin(request)
    with closing(G['db']()) as c:
        banners=[dict(r) for r in c.execute('SELECT * FROM home_banners210 ORDER BY position,id')]
        seconds=c.execute('SELECT seconds FROM home_settings210 WHERE id=1').fetchone()[0]
        stores=[dict(r) for r in c.execute("SELECT slug,display_name FROM professionals WHERE blocked=0 AND admission_status='approved' AND plan_active IN ('vitrine','ambos','completo') ORDER BY display_name")]
    return G['templates'].TemplateResponse('home210.html',G['context'](request,banners210=banners,seconds210=seconds,stores498=stores))
@router.post('/admin/banners-inicio/tempo')
async def timing(request:Request):
    admin(request);f=await request.form();seconds=number(f.get('seconds'),1,120)
    with closing(G['db']()) as c,c:c.execute('UPDATE home_settings210 SET seconds=? WHERE id=1',(seconds,))
    return RedirectResponse('/admin/banners-inicio?salvo=1',303)
@router.post('/admin/banners-inicio/salvar')
async def save(request:Request):
    f=await request.form()
    from starlette.concurrency import run_in_threadpool
    return await run_in_threadpool(save_worker308,request,f)

def save_worker308(request,f):
    admin(request);bid=number(f.get('id',0),0,2147483647)
    title=str(f.get('title','')).strip()[:140]
    if not title:raise HTTPException(400,'Preencha o título')
    position=number(f.get('position',0),0,999)
    kind=str(f.get('kind498','general'))
    if kind not in ('general','promocoes','combos','geladas','chocolates'):raise HTTPException(400,'Tipo inválido')
    store=str(f.get('store498','')).strip()
    start,end=(str(f.get(k,'')).strip() for k in ('start498','end498'))
    from datetime import date
    try:
        for d in (start,end):
            if d and date.fromisoformat(d).isoformat()!=d:raise ValueError()
    except ValueError:raise HTTPException(400,'Data inválida')
    if start and end and start>end:raise HTTPException(400,'A data final deve ser posterior à inicial')
    with closing(G['db']()) as c,c:
        if store and not c.execute("SELECT 1 FROM professionals WHERE slug=? AND blocked=0 AND admission_status='approved' AND plan_active IN ('vitrine','ambos','completo')",(store,)).fetchone():raise HTTPException(400,'Loja inválida')
        old=c.execute('SELECT * FROM home_banners210 WHERE id=?',(bid,)).fetchone() if bid else None
        if bid and not old:raise HTTPException(404,'Banner não encontrado')
        if not bid and c.execute('SELECT COUNT(*) FROM home_banners210').fetchone()[0]>=20:raise HTTPException(400,'Limite de 20 banners')
        image=old['image'] if old else ''
        upload=f.get('image')
        if getattr(upload,'filename',None):image='/uploads/'+G['save_image'](upload)
        if not image:raise HTTPException(400,'Escolha uma imagem')
        values=(title,image,int(f.get('active')=='1'),position,kind,store,start,end)
        if old:c.execute('UPDATE home_banners210 SET title=?,image=?,active=?,position=?,kind498=?,store498=?,start498=?,end498=? WHERE id=?',(*values,bid))
        else:c.execute('INSERT INTO home_banners210(title,image,active,position,kind498,store498,start498,end498) VALUES(?,?,?,?,?,?,?,?)',values)
    return RedirectResponse('/admin/banners-inicio?salvo=1',303)
@router.post('/admin/banners-inicio/{bid}/excluir')
def delete(request:Request,bid:int):
    admin(request)
    with closing(G['db']()) as c,c:
        if not c.execute('DELETE FROM home_banners210 WHERE id=?',(bid,)).rowcount:raise HTTPException(404,'Banner não encontrado')
    return RedirectResponse('/admin/banners-inicio?salvo=1',303)

