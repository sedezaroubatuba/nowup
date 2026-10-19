"""Banners opcionais por loja, com destinos restritos aos próprios produtos."""
import json
from contextlib import closing
from fastapi import APIRouter,Request,HTTPException
from fastapi.responses import RedirectResponse,JSONResponse
router=APIRouter();G={}
def configure(g):G.update(g)
def initialize():
    with closing(G['db']()) as c, c:
        c.executescript('''CREATE TABLE IF NOT EXISTS store_banner_settings207(professional_id INTEGER PRIMARY KEY REFERENCES professionals(id),seconds INTEGER NOT NULL DEFAULT 2);
        CREATE TABLE IF NOT EXISTS store_banners207(id INTEGER PRIMARY KEY,professional_id INTEGER NOT NULL REFERENCES professionals(id),title TEXT NOT NULL,image TEXT NOT NULL,mode TEXT NOT NULL,product_ids TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);''')
def owner(request,c):
    u=G['require_user'](request,'professional')
    p=c.execute('SELECT * FROM professionals WHERE user_id=?',(u['id'],)).fetchone()
    if not p:raise HTTPException(404,'Loja não encontrada')
    return p
@router.get('/painel/banners')
def editor(request:Request):
    c=G['db']()
    try:
        p=owner(request,c);s=c.execute('SELECT seconds FROM store_banner_settings207 WHERE professional_id=?',(p['id'],)).fetchone()
        banners=[dict(b) for b in c.execute('SELECT * FROM store_banners207 WHERE professional_id=? ORDER BY id',(p['id'],))]
        products=c.execute('SELECT id,name FROM products WHERE professional_id=? ORDER BY name',(p['id'],)).fetchall()
        for b in banners:b['ids']=json.loads(b['product_ids'])
        return G['templates'].TemplateResponse('banners207.html',G['context'](request,pro=p,banners=banners,products=products,seconds=s[0] if s else 2))
    finally:c.close()
@router.post('/painel/banners/tempo')
async def timing(request:Request):
    f=await request.form()
    try:n=int(f.get('seconds',2))
    except (ValueError,TypeError):raise HTTPException(400,'Informe os segundos em número inteiro')
    if not 1<=n<=120:raise HTTPException(400,'Escolha de 1 a 120 segundos')
    with closing(G['db']()) as c, c:
        p=owner(request,c);c.execute('INSERT INTO store_banner_settings207 VALUES(?,?) ON CONFLICT(professional_id) DO UPDATE SET seconds=excluded.seconds',(p['id'],n))
    return RedirectResponse('/painel/banners?salvo=1',303)
@router.post('/painel/banners/salvar')
async def save(request:Request):
    f=await request.form()
    try:bid=int(f.get('id',0));ids=list(dict.fromkeys(int(v) for v in f.getlist('products')))
    except (ValueError,TypeError):raise HTTPException(400,'Seleção de produtos inválida')
    title=str(f.get('title','')).strip()[:100];mode=f.get('mode');active=int(f.get('active')=='1')
    if not title:raise HTTPException(400,'Informe o título do banner')
    if mode not in ('info','single','selection'):raise HTTPException(400,'Escolha o destino do banner')
    if mode=='info':ids=[]
    elif not ids or len(ids)>200 or (mode=='single' and len(ids)!=1):raise HTTPException(400,'Selecione exatamente um produto no modo direto ou pelo menos um na seleção')
    with closing(G['db']()) as c, c:
        p=owner(request,c);old=c.execute('SELECT * FROM store_banners207 WHERE id=? AND professional_id=?',(bid,p['id'])).fetchone() if bid else None
        if bid and not old:raise HTTPException(404,'Banner não encontrado')
        if not bid and c.execute('SELECT COUNT(*) FROM store_banners207 WHERE professional_id=?',(p['id'],)).fetchone()[0]>=10:raise HTTPException(400,'Limite de 10 banners por loja')
        allowed={r[0] for r in c.execute('SELECT id FROM products WHERE professional_id=?',(p['id'],))}
        if not set(ids)<=allowed:raise HTTPException(400,'Selecione apenas produtos da sua loja')
        image=old['image'] if old else '';upload=f.get('image')
        if getattr(upload,'filename',None):image=G['save_image'](upload)
        if not image:raise HTTPException(400,'Envie a imagem do banner')
        values=(title,image,mode,json.dumps(ids),active)
        if old:c.execute('UPDATE store_banners207 SET title=?,image=?,mode=?,product_ids=?,active=? WHERE id=? AND professional_id=?',(*values,bid,p['id']))
        else:c.execute('INSERT INTO store_banners207(title,image,mode,product_ids,active,professional_id) VALUES(?,?,?,?,?,?)',(*values,p['id']))
    return RedirectResponse('/painel/banners?salvo=1',303)
@router.post('/painel/banners/{bid}/excluir')
def delete(request:Request,bid:int):
    with closing(G['db']()) as c, c:
        p=owner(request,c);c.execute('DELETE FROM store_banners207 WHERE id=? AND professional_id=?',(bid,p['id']))
    return RedirectResponse('/painel/banners?salvo=1',303)
@router.get('/api/loja/{slug}/banners207')
def public(slug:str):
    c=G['db']()
    try:
        p=c.execute("SELECT * FROM professionals WHERE slug=? AND blocked=0 AND admission_status='approved' AND plan_active IN ('cardapio','ambos')",(slug,)).fetchone()
        if not p or not p['is_premium'] or p['offer_mode'] not in ('menu','catalog'):raise HTTPException(404,'Loja não encontrada')
        s=c.execute('SELECT seconds FROM store_banner_settings207 WHERE professional_id=?',(p['id'],)).fetchone()
        allowed={r[0] for r in c.execute('SELECT id FROM products WHERE professional_id=?',(p['id'],))};items=[]
        for b in c.execute('SELECT * FROM store_banners207 WHERE professional_id=? AND active=1 ORDER BY id',(p['id'],)):
            ids=[v for v in json.loads(b['product_ids']) if v in allowed]
            if ids or b['mode']=='info':items.append({'title':b['title'],'image':'/uploads/'+b['image'],'mode':b['mode'],'ids':ids})
        return JSONResponse({'seconds':s[0] if s else 2,'items':items},headers={'Cache-Control':'no-store'})
    finally:c.close()
