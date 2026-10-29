"""Store-specific install identity and presentation; shared verified order/auth rules."""
import base64
import hashlib
import io
import re
from pathlib import Path
from urllib.parse import quote, urlsplit
from fastapi import HTTPException, Request, Form
from fastapi.responses import JSONResponse, Response, RedirectResponse
from PIL import Image, ImageOps, ImageDraw

SLUG=re.compile(r'^[a-zA-Z0-9_-]{1,160}$')
HEADERS={'Cache-Control':'private, no-store','Vary':'Cookie'}

def store(g,slug,active=True):
    if not SLUG.fullmatch(slug or ''):raise HTTPException(404,'Loja não encontrada')
    c=g['db']()
    try:
        where=" AND p.blocked=0 AND p.admission_status='approved' AND p.plan_active IN ('cardapio','ambos') AND p.is_premium=1 AND p.offer_mode IN ('menu','catalog') AND u.is_active=1" if active else ''
        row=c.execute('SELECT p.* FROM professionals p JOIN users u ON u.id=p.user_id WHERE p.slug=?'+where,(slug,)).fetchone()
        if not row:raise HTTPException(404,'Cardápio não disponível')
        return dict(row)
    finally:c.close()

def presentation(p):
    slug=p['slug'];prefix='/p/'+quote(slug,safe='')
    return {'slug':slug,'name':p['display_name'],'menu':prefix+'/menu?loja=1',
        'manifest':prefix+'/manifest.webmanifest','icon':prefix+'/app-icon/192.png',
        'login':prefix+'/entrar?tipo=cliente','signup':'/cadastro/cliente?loja='+quote(slug,safe='')}

def page_context(g,request,values):
    p=getattr(request.state,'store_app256',None)
    candidate=values.get('pro')
    if p is None and candidate is not None and request.method=='GET' and request.url.path.startswith('/p/'):
        if candidate['plan_active']=='cardapio' or request.query_params.get('loja')=='1':
            try:p=store(g,candidate['slug'])
            except HTTPException:p=None
    return {'store_app256':presentation(p) if p else None}

def install(g):
    app=g['app']
    @app.get('/p/{slug}/manifest.webmanifest')
    def store_manifest256(slug:str):
        p=store(g,slug);view=presentation(p);prefix='/p/'+quote(slug,safe='')+'/'
        result={'id':prefix+'app','name':p['display_name'][:120],'short_name':p['display_name'][:30],
            'lang':'pt-BR','description':'Cardápio e pedidos de '+p['display_name'][:120],
            'start_url':view['menu'],'scope':prefix,'display':'standalone',
            'background_color':'#ffffff','theme_color':'#7136bf',
            'icons':[{'src':prefix+'app-icon/'+str(size)+'.png','sizes':f'{size}x{size}','type':'image/png','purpose':'any maskable'} for size in (192,512)]}
        return JSONResponse(result,media_type='application/manifest+json',headers=HEADERS)

    @app.get('/p/{slug}/app-icon/{size}.png')
    def store_icon256(slug:str,size:int):
        if size not in (192,512):raise HTTPException(404)
        p=store(g,slug);filename=p.get('avatar_filename','');data=None
        if re.fullmatch(r'[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp|gif)',filename,re.I):
            directory=Path(g['UPLOAD_DIR']).resolve();path=(directory/filename).resolve()
            if path.parent==directory and path.is_file() and path.stat().st_size<=8*1024*1024:data=path.read_bytes()
            if data is None:
                c=g['db']()
                try:
                    exists=c.execute("SELECT 1 FROM sqlite_master WHERE name='nowup_public_media245'").fetchone()
                    if exists:
                        row=c.execute('SELECT body FROM nowup_public_media245 WHERE filename=?',(filename,)).fetchone()
                        if row and len(row[0])<=12*1024*1024:
                            try:data=base64.b64decode(row[0],validate=True)
                            except (ValueError,TypeError):data=None
                finally:c.close()
        canvas=Image.new('RGB',(size,size),'#7136bf')
        try:
            if not data:raise ValueError()
            with Image.open(io.BytesIO(data)) as im:
                if im.width*im.height>24_000_000:raise ValueError()
                logo=ImageOps.contain(im.convert('RGBA'),(int(size*.7),int(size*.7)))
                canvas.paste(logo,((size-logo.width)//2,(size-logo.height)//2),logo)
        except (ValueError,OSError,Image.DecompressionBombError):
            # A store without a logo still has an independent deterministic icon.
            draw=ImageDraw.Draw(canvas);initial=''.join(w[0] for w in p['display_name'].split()[:2]).upper() or 'L'
            try:
                from PIL import ImageFont
                font=ImageFont.truetype('DejaVuSans.ttf',size//3)
            except OSError:
                from PIL import ImageFont
                font=ImageFont.load_default(size=size//3)
            draw.text((size//2,size//2),initial,fill='white',font=font,anchor='mm')
        output=io.BytesIO();canvas.save(output,format='PNG');body=output.getvalue()
        return Response(body,media_type='image/png',headers={**HEADERS,'ETag':'"'+hashlib.sha256(body).hexdigest()+'"','X-Content-Type-Options':'nosniff'})

    @app.get('/p/{slug}/entrar')
    def store_login256(request:Request,slug:str):
        request.state.store_app256=store(g,slug)
        result=g['login_page'](request)
        result.set_cookie('nowup_store_return256',slug,max_age=1800,httponly=True,secure=g['os'].getenv('NOWUP_HTTPS')=='1' or request.url.scheme=='https',samesite='lax',path='/')
        return result

    @app.post('/p/{slug}/entrar')
    def store_login_post256(request:Request,slug:str,email:str=Form(...),password:str=Form(...)):
        p=store(g,slug)
        import admin_customization
        # Older production auth has no Request parameter; preserve its exact policy.
        import inspect
        arguments={'email':email,'password':password,'tipo':'cliente'}
        if 'request' in inspect.signature(admin_customization.secure_login).parameters:arguments['request']=request
        result=admin_customization.secure_login(**arguments)
        location=result.headers.get('location','')
        if location=='/':
            result.headers['location']=presentation(p)['menu']
            result.delete_cookie('nowup_store_return256',path='/')
        elif location.startswith('/entrar?'):result.headers['location']='/p/'+quote(slug,safe='')+'/entrar?'+urlsplit(location).query
        result.headers.update(HEADERS)
        return result

    @app.get('/p/{slug}/pedido/{token}')
    def store_order256(request:Request,slug:str,token:str):
        p=store(g,slug,active=False);c=g['db']()
        try:
            order=c.execute('SELECT professional_id FROM orders WHERE tracking_token=?',(token,)).fetchone()
            if not order or order[0]!=p['id']:raise HTTPException(404,'Pedido não encontrado nesta loja')
        finally:c.close()
        request.state.store_app256=p
        return g['order_tracking'](request,token)

    @app.middleware('http')
    async def return_to_store256(request,call_next):
        authpaths={'/cadastro/cliente','/cadastro/aguardando','/verificar-email','/entrar','/recuperar-senha','/redefinir-senha'}
        if request.url.path not in authpaths:return await call_next(request)
        slug=request.query_params.get('loja') or request.cookies.get('nowup_store_return256','')
        p=None
        if slug:
            try:
                from starlette.concurrency import run_in_threadpool
                p=await run_in_threadpool(store,g,slug)
            except HTTPException:pass
        if p:request.state.store_app256=p
        response=await call_next(request)
        if p:
            location=response.headers.get('location','')
            if request.url.path=='/entrar' and request.method=='POST' and location=='/':
                response.headers['location']=presentation(p)['menu']
                response.delete_cookie('nowup_store_return256',path='/')
            elif request.url.path in {'/verificar-email','/redefinir-senha'} and location.startswith('/entrar'):
                response.headers['location']='/p/'+quote(slug,safe='')+'/entrar?'+urlsplit(location).query+'&tipo=cliente'
            if request.query_params.get('loja'):
                response.set_cookie('nowup_store_return256',slug,max_age=1800,httponly=True,secure=g['os'].getenv('NOWUP_HTTPS')=='1' or request.url.scheme=='https',samesite='lax',path='/')
        return response
