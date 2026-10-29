"""Super ADM controls for the message-free animated opening."""
import re
from fastapi import Request,Form,HTTPException
from fastapi.responses import RedirectResponse

DEFAULTS={'enabled':'1','sound':'0','duration':'4200','color':'#7136bf','frequency':'daily'}
def config(settings):
    result={k:settings.get('opening260_'+k,v) for k,v in DEFAULTS.items()}
    try:result['duration']=max(2500,min(6000,int(result['duration'])))
    except (ValueError,TypeError):result['duration']=4200
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',str(result['color'])):result['color']='#7136bf'
    if result['frequency'] not in ('daily','session','always'):result['frequency']='daily'
    result['enabled']=result['enabled']=='1';result['sound']=result['sound']=='1'
    return result

def install(g):
    app=g['app'];admin=g['nowup_admin227']
    @app.get('/admin/super/abertura')
    def opening_settings260(request:Request):
        with admin.connection() as c:
            actor=admin.auth(request,c)
            if not actor['super']:raise HTTPException(403,'Somente o Super ADM pode alterar a abertura.')
            values=config(g['get_settings'](c))
        return g['templates'].TemplateResponse('opening_admin260.html',{'request':request,'opening':values},headers={'Cache-Control':'private, no-store'})
    @app.post('/admin/super/abertura')
    def save_opening260(request:Request,enabled:str=Form('0'),sound:str=Form('0'),duration:int=Form(4200),color:str=Form('#7136bf'),frequency:str=Form('daily')):
        if enabled not in ('0','1') or sound not in ('0','1') or not 2500<=duration<=6000 or not re.fullmatch(r'#[0-9a-fA-F]{6}',color) or frequency not in ('daily','session','always'):raise HTTPException(400,'Confira os ajustes da abertura.')
        with admin.connection() as c:
            actor=admin.auth(request,c)
            if not actor['super']:raise HTTPException(403,'Somente o Super ADM pode alterar a abertura.')
            for key,value in dict(enabled=enabled,sound=sound,duration=str(duration),color=color,frequency=frequency).items():c.execute('INSERT INTO site_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('opening260_'+key,value))
            admin.audit(c,actor,'Configuração da abertura NowUp alterada','opening260');c.commit()
        return RedirectResponse('/admin/super/abertura?salvo=1',303)
