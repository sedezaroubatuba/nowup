"""Manual appearance presets. Customer-only styling, independent Sede Zero override."""
from fastapi import Request, Form, HTTPException
from fastapi.responses import RedirectResponse

PRESETS = {'original':'Original','impacto':'Branco — Impacto','neon':'Neon escuro','natal':'Natal','2027':'Feliz 2027','black':'Black — Preto e amarelo'}
STORE_PRESETS = {'inherit':'Seguir tema geral', **PRESETS}

def selected(settings, path, slug=''):
    settings = settings or {}
    if path != '/' and not path.startswith('/p/'):
        return 'original'
    theme = settings.get('appearance505','original')
    if theme not in PRESETS:
        theme = 'original'
    if slug == 'adega-sede-zero' and path.startswith('/p/'):
        override = settings.get('sede_appearance505','inherit')
        if override in PRESETS:
            return override
    if theme in ('natal','2027') and path != '/' and slug != 'adega-sede-zero':
        return 'original'
    return theme

def install(g):
    app, admin = g['app'], g['nowup_admin227']
    def store_owner(request,c):
        u = g['require_user'](request,'professional')
        if not c.execute("SELECT 1 FROM professionals WHERE user_id=? AND slug='adega-sede-zero' AND is_demo=0",(u['id'],)).fetchone():
            raise HTTPException(403,'Disponível exclusivamente para a Sede Zero.')
    def write(c,key,value):
        c.execute("INSERT INTO site_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,value))
    def view(request,merchant=False):
        with admin.connection() as c:
            if merchant:
                store_owner(request,c)
            else:
                actor=admin.auth(request,c)
                if not actor['super']:raise HTTPException(403,'Somente Super ADM.')
            settings=g['get_settings'](c)
        return g['templates'].TemplateResponse('appearance505.html',g['context'](request,presets505=PRESETS,store_presets505=STORE_PRESETS,current505=settings.get('appearance505','original'),store505=settings.get('sede_appearance505','inherit'),merchant505=merchant))
    @app.get('/admin/super/aparencia')
    def admin_view(request: Request):return view(request)
    @app.post('/admin/super/aparencia')
    def admin_save(request: Request, theme: str=Form(...), store_theme: str=Form(...)):
        if theme not in PRESETS or store_theme not in STORE_PRESETS:raise HTTPException(400,'Tema inválido.')
        with admin.connection() as c:
            actor=admin.auth(request,c)
            if not actor['super']:raise HTTPException(403,'Somente Super ADM.')
            write(c,'appearance505',theme)
            write(c,'sede_appearance505',store_theme)
            admin.audit(c,actor,'Tema visual alterado',theme+' / '+store_theme)
            c.commit()
        return RedirectResponse('/admin/super/aparencia?salvo=1',303)
    @app.get('/painel/aparencia')
    def merchant_view(request: Request):return view(request,True)
    @app.post('/painel/aparencia')
    def merchant_save(request: Request, store_theme: str=Form(...)):
        if store_theme not in STORE_PRESETS:raise HTTPException(400,'Tema inválido.')
        with admin.connection() as c:
            store_owner(request,c)
            write(c,'sede_appearance505',store_theme)
            c.commit()
        return RedirectResponse('/painel/aparencia?salvo=1',303)
