"""Manual appearance presets. Customer-only styling, independent Sede Zero override."""
from fastapi import Request, Form, HTTPException
from fastapi.responses import RedirectResponse

PRESETS = {'original':'Original','sede':'Sede Zero — Branco, preto e amarelo','natal':'Natal claro','2027':'Réveillon claro — Feliz 2027'}
STORE_PRESETS = {
    'original':'Roxo Essencial — principal',
    'lime':'Roxo + Verde Limão',
    'natal_store':'Natal — Roxo Essencial',
    'reveillon_store':'Réveillon — Roxo Essencial',
}

def store_selected(value):
    # Old inherited or seasonal settings do not change the new default;
    # new store-specific selections are persisted independently.
    return value if value in STORE_PRESETS else 'original'

def normalize(value, default='original'):
    if value == 'black':
        return 'sede'
    return value if value in PRESETS or (value == 'inherit' and default == 'inherit') else default

def selected(settings, path, slug=''):
    settings = settings or {}
    if path != '/' and not path.startswith('/p/'):
        return 'original'
    theme = normalize(settings.get('appearance505','original'))
    if slug == 'adega-sede-zero' and path.startswith('/p/'):
        return store_selected(settings.get('sede_appearance505','original'))
    if theme in ('natal','2027') and path != '/' and slug != 'adega-sede-zero':
        return 'original'
    return theme

def home_season524(settings):
    value = (settings or {}).get('home_season524', 'natal')
    return value if value in ('original', 'natal', '2027') else 'original'

def install(g):
    app, admin = g['app'], g['nowup_admin227']
    g['templates'].env.globals['home_season524'] = home_season524
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
        return g['templates'].TemplateResponse('appearance505.html',g['context'](request,presets505=PRESETS,store_presets505=STORE_PRESETS,current505=normalize(settings.get('appearance505','original')),store505=store_selected(settings.get('sede_appearance505','original')),merchant505=merchant,home_season524_current=home_season524(settings),marketplace_categories512=settings.get('marketplace_categories512','0')=='1',marketplace_test513=settings.get('marketplace_show_test_513','0')=='1'))
    @app.get('/admin/super/aparencia')
    def admin_view(request: Request):return view(request)
    @app.post('/admin/super/aparencia')
    def admin_save(request: Request, theme: str=Form(...), store_theme: str=Form(...), marketplace_categories: str=Form(''), marketplace_test: str=Form(''), home_season: str=Form('')):
        if theme not in PRESETS or store_theme not in STORE_PRESETS:raise HTTPException(400,'Tema inválido.')
        with admin.connection() as c:
            actor=admin.auth(request,c)
            if not actor['super']:raise HTTPException(403,'Somente Super ADM.')
            write(c,'appearance505',theme)
            write(c,'sede_appearance505',store_theme)
            if home_season in ('original','natal','2027'):
                write(c,'home_season524',home_season)
            if marketplace_categories in ('0','1'):
                write(c,'marketplace_categories512',marketplace_categories)
            if marketplace_test in ('0','1'):
                write(c,'marketplace_show_test_513',marketplace_test)
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
