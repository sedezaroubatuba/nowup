"""Customer accounts and opaque sessions belonging to one standalone store."""
import hashlib
import html
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from fastapi import Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from nowup_storeapp256 import store, presentation, HEADERS, SLUG


def cookie_name(p): return 'nowup_loja345_'+str(p['id'])
def cookie_path(p): return '/p/'+quote(p['slug'],safe='')+'/'


def request_store(g,request):
    if hasattr(request.state,'scope_store345'): return request.state.scope_store345
    p=getattr(request.state,'store_app256',None)
    if p is None:
        parts=request.url.path.split('/')
        if len(parts)>=3 and parts[1]=='p' and SLUG.fullmatch(parts[2]):
            try:
                candidate=store(g,parts[2],active=False)
                tail='/'.join(parts[3:])
                if (candidate['plan_active']=='cardapio' or request.query_params.get('loja')=='1'
                    or request.query_params.get('origem')=='externo' or request.cookies.get(cookie_name(candidate))
                    or tail in ('entrar','cadastro','recuperar-senha','redefinir-senha','verificar-email','reenviar-verificacao','aguardando','pedidos','sair','menu/whatsapp','cart-completion345') or tail.startswith('pedido/')):
                    p=candidate
            except HTTPException: pass
    request.state.scope_store345=p
    if p is not None: request.state.store_app256=p
    return p


def identity(g,request):
    p=request_store(g,request)
    return (request.cookies.get(cookie_name(p)),p['id'],cookie_name(p),cookie_path(p).rstrip('/')) if p else (request.cookies.get('nowup_session'),0,'nowup_session','/')


def session_response(g,request,p,uid):
    # Use the common opaque-session lifetime, then bind the record before any
    # cookie is sent. A store token is never valid in the marketplace.
    response=g['create_session_response'](uid,presentation(p)['menu'])
    from http.cookies import SimpleCookie
    cookies=SimpleCookie();cookies.load(response.headers['set-cookie'])
    token=cookies['nowup_session'].value
    with g['db']() as c:
        c.execute('UPDATE sessions SET store_id345=? WHERE token=?',(p['id'],token));c.commit()
    response.raw_headers=[(k,v) for k,v in response.raw_headers if k.lower()!=b'set-cookie']
    response.set_cookie(cookie_name(p),token,max_age=g['SESSION_DAYS']*86400,httponly=True,
        secure=request.url.scheme=='https' or g['os'].getenv('NOWUP_HTTPS')=='1',samesite='lax',path=cookie_path(p).rstrip('/'))
    response.headers.update(HEADERS)
    return response


def customer(c,p,email):
    return c.execute("SELECT * FROM users WHERE role='customer' AND customer_store345=? AND customer_email345=? AND is_active=1",(p['id'],email)).fetchone()


def send_confirmation(g,p,user,email,token):
    base=g['os'].getenv('NOWUP_BASE_URL','').strip().rstrip('/')
    if not base:return False
    link=base+cookie_path(p)+'verificar-email?token='+quote(token,safe='')
    return g['send_email'](email,user,'Confirme seu cadastro em '+p['display_name'],
        '<h2>'+html.escape(p['display_name'])+'</h2><p>Confirme sua conta exclusiva desta loja.</p><p><a href="'+html.escape(link,quote=True)+'">Confirmar e-mail</a></p><p>O link expira em 24 horas.</p>')


def install(g):
    app=g['app']
    replaced={'/p/{slug}/entrar','/p/{slug}/sair'}
    app.router.routes[:]=[r for r in app.router.routes if getattr(r,'path',None) not in replaced]

    def view(request,slug,template,**kwargs):
        p=store(g,slug);request.state.store_app256=p
        return g['templates'].TemplateResponse(template,g['context'](request,**kwargs),headers=HEADERS)

    @app.get('/p/{slug}/entrar')
    def login_page(request:Request,slug:str): return view(request,slug,'login.html')

    @app.post('/p/{slug}/entrar')
    def login(request:Request,slug:str,email:str=Form(...),password:str=Form(...)):
        p=store(g,slug)
        from nowup_auth247 import check
        check(g['db'],request,str(p['id'])+':'+email)
        with g['db']() as c: u=customer(c,p,email.strip().lower())
        error='1'
        if u and len(password)<=128 and g['verify_password'](password,u['password_hash']):
            if u['email_verified']: return session_response(g,request,p,u['id'])
            error='verificacao'
        return RedirectResponse(cookie_path(p)+'entrar?erro='+error,303)

    @app.get('/p/{slug}/cadastro')
    def signup_page(request:Request,slug:str): return view(request,slug,'signup_customer.html')

    @app.post('/p/{slug}/cadastro')
    def signup(request:Request,slug:str,name:str=Form(...),email:str=Form(...),phone:str=Form(...),password:str=Form(...),password_confirm:str=Form(...),accept_terms:str=Form(''),address:str=Form(''),neighborhood:str=Form(''),city:str=Form(''),state:str=Form(''),marketing_email309:str=Form(''),marketing_whatsapp309:str=Form('')):
        p=store(g,slug);error=''
        from nowup_auth247 import check
        check(g['db'],request,str(p['id'])+':'+email,kind='signup345')
        normalized=g['normalize_email'](email)
        if not all(v.strip() for v in (name,address,neighborhood,city)) or state not in g['nowup_admin205'].UFS:error='endereco'
        elif not normalized:error='email_invalido'
        elif not g['normalize_phone'](phone):error='telefone'
        elif not 8<=len(password)<=128 or password!=password_confirm or not accept_terms:error='senha'
        elif not g['email_service_configured']():error='email_indisponivel'
        if error:return RedirectResponse(cookie_path(p)+'cadastro?erro='+error,303)
        token,expires=g['verification_token']()
        with g['db']() as c:
            if customer(c,p,normalized):return RedirectResponse(cookie_path(p)+'cadastro?erro=email',303)
            # The internal unique key is never used as a contact address. The
            # same real email can have separate accounts at different stores.
            internal='loja345-'+secrets.token_hex(24)+'@nowup.local'
            try:
                uid=c.execute("INSERT INTO users(role,name,email,phone,password_hash,email_verified,verification_token,verification_expires_at,created_at,address,neighborhood,city,state,customer_store345,customer_email345) VALUES('customer',?,?,?,?,0,?,?,?,?,?,?,?,?,?)",(name.strip()[:120],internal,phone.strip()[:30],g['hash_password'](password),token,expires,g['now_iso'](),address.strip()[:300],neighborhood.strip()[:120],city.strip()[:120],state,p['id'],normalized)).lastrowid
                g['nowup_marketing309'].save(c,uid,False,False,source='store345')
                c.commit()
            except g['sqlite3'].IntegrityError:
                c.rollback();return RedirectResponse(cookie_path(p)+'cadastro?erro=email',303)
        sent=send_confirmation(g,p,name.strip(),normalized,token)
        return RedirectResponse(cookie_path(p)+'aguardando'+('' if sent else '?erro=envio_email'),303)

    @app.get('/p/{slug}/aguardando')
    def waiting(request:Request,slug:str):return view(request,slug,'verify_pending.html')

    @app.get('/p/{slug}/verificar-email')
    def verify(request:Request,slug:str,token:str=''):
        p=store(g,slug)
        with g['db']() as c:
            u=c.execute("SELECT id FROM users WHERE verification_token=? AND verification_expires_at>? AND customer_store345=? AND role='customer'",(token,g['now_iso'](),p['id'])).fetchone() if token else None
            if u:
                c.execute("UPDATE users SET email_verified=1,verification_token='',verification_expires_at='' WHERE id=?",(u['id'],));c.commit()
        return RedirectResponse(cookie_path(p)+'entrar?'+('verificado=1' if u else 'erro=verificacao'),303)

    @app.post('/p/{slug}/reenviar-verificacao')
    def resend(request:Request,slug:str,email:str=Form(...)):
        p=store(g,slug)
        from nowup_auth247 import verification,verification_token348
        verification(g['db'],request,str(p['id'])+':'+email.strip().lower())
        with g['db']() as c:
            u=customer(c,p,email.strip().lower())
            if u and not u['email_verified']:
                token,expires=verification_token348(u)
                c.execute('UPDATE users SET verification_token=?,verification_expires_at=? WHERE id=?',(token,expires,u['id']));c.commit()
                send_confirmation(g,p,u['name'],u['customer_email345'],token)
        return RedirectResponse(cookie_path(p)+'aguardando?reenviado=1',303)

    @app.get('/p/{slug}/recuperar-senha')
    def forgot_page(request:Request,slug:str):return view(request,slug,'forgot_password.html')

    @app.post('/p/{slug}/recuperar-senha')
    def forgot(request:Request,slug:str,email:str=Form(...)):
        p=store(g,slug)
        from nowup_auth247 import check
        check(g['db'],request,str(p['id'])+':'+email,kind='reset')
        with g['db']() as c:
            u=customer(c,p,email.strip().lower())
            if u:
                raw=secrets.token_urlsafe(40);digest=hashlib.sha256(raw.encode()).hexdigest()
                expires=(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat()
                c.execute('DELETE FROM password_reset_tokens WHERE user_id=?',(u['id'],))
                c.execute('INSERT INTO password_reset_tokens(token_hash,user_id,expires_at) VALUES(?,?,?)',(digest,u['id'],expires));c.commit()
                base=g['os'].getenv('NOWUP_BASE_URL','').strip().rstrip('/')
                if base:
                    link=base+cookie_path(p)+'redefinir-senha?token='+quote(raw)
                    g['send_email'](u['customer_email345'],u['name'],'Redefinir senha — '+p['display_name'],'<p><a href="'+html.escape(link,quote=True)+'">Criar nova senha desta loja</a></p><p>O link expira em 30 minutos.</p>')
        return RedirectResponse(cookie_path(p)+'recuperar-senha?enviado=1',303)

    def reset_token(p,token):
        with g['db']() as c:
            return c.execute("SELECT t.* FROM password_reset_tokens t JOIN users u ON u.id=t.user_id WHERE t.token_hash=? AND t.used=0 AND t.expires_at>? AND u.customer_store345=?",(hashlib.sha256(token.encode()).hexdigest(),g['now_iso'](),p['id'])).fetchone() if token else None

    @app.get('/p/{slug}/redefinir-senha')
    def reset_page(request:Request,slug:str,token:str=''):
        p=store(g,slug)
        return view(request,slug,'reset_password.html',token=token,invalid=not bool(reset_token(p,token)))

    @app.post('/p/{slug}/redefinir-senha')
    def reset(request:Request,slug:str,token:str=Form(...),password:str=Form(...),password_confirm:str=Form(...)):
        p=store(g,slug)
        if not reset_token(p,token):return RedirectResponse(cookie_path(p)+'entrar?erro=expirado',303)
        response=g['reset_password'](token,password,password_confirm)
        dest=response.headers.get('location','')
        if dest.startswith('/entrar'):response.headers['location']=cookie_path(p)+'entrar?'+dest.partition('?')[2]
        elif dest.startswith('/redefinir-senha'):response.headers['location']=cookie_path(p)+'redefinir-senha?'+dest.partition('?')[2]
        return response

    @app.post('/p/{slug}/sair')
    def logout(request:Request,slug:str):
        p=store(g,slug,active=False);token=request.cookies.get(cookie_name(p))
        if token:
            with g['db']() as c:
                c.execute('DELETE FROM sessions WHERE token=? AND store_id345=?',(token,p['id']));c.commit()
        response=RedirectResponse(presentation(p)['menu'],303)
        response.delete_cookie(cookie_name(p),path=cookie_path(p).rstrip('/'));return response

    @app.get('/p/{slug}/cart-completion345')
    def completion(request:Request,slug:str,request_key:str):
        p=store(g,slug,active=False);request.state.store_app256=p
        return g['cart_completion247'](request,request_key)

    # Reuse the validated order endpoints with a store-specific URL and cookie
    # path. Endpoint authorization still checks the actual account/order owner.
    from fastapi import Depends
    from fastapi.routing import APIRoute
    def order_boundary(request:Request,slug:str):
        p=store(g,slug,active=False);request.state.store_app256=p
        params=request.path_params
        with g['db']() as c:
            if 'order_id' in params:
                row=c.execute('SELECT professional_id FROM orders WHERE id=?',(params['order_id'],)).fetchone()
            elif 'token' in params:
                row=c.execute('SELECT professional_id FROM orders WHERE tracking_token=?',(params['token'],)).fetchone()
            else:return
        if not row or row['professional_id']!=p['id']:raise HTTPException(404,'Pedido não encontrado nesta loja')
    existing={getattr(r,'path','') for r in app.router.routes}
    def flattened(routes):
        for route in routes:
            nested=getattr(route,'original_router',None)
            if nested is not None:yield from flattened(nested.routes)
            else:yield route
    for route in list(flattened(app.router.routes)):
        if not isinstance(route,APIRoute):continue
        if not (route.path.startswith(('/pedidos/','/pedido/')) or route.path in ('/cliente/pedidos/resumo202','/cliente/avisos','/cliente/notificacoes/ler') or route.path.startswith('/cliente/push/')):continue
        path='/p/{slug}'+route.path
        if path in existing:continue
        app.add_api_route(path,route.endpoint,methods=list(route.methods),response_model=route.response_model,
            response_class=route.response_class,status_code=route.status_code,
            dependencies=[*route.dependencies,Depends(order_boundary)],include_in_schema=False)
