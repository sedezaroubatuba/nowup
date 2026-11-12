"""Persistent first-use practice. Sample products never enter the public catalogue."""
import json
from datetime import datetime,timezone
from fastapi import Request,HTTPException
from fastapi.responses import JSONResponse,RedirectResponse
import nowup_sales107 as ledger
from nowup_costs413 import cents
TASKS=[('profile','Complete os dados da loja'),('category','Crie uma categoria de teste'),('bases','Prepare ingredientes, acompanhamentos e adicionais'),('normal','Cadastre um produto normal'),('meal','Monte um lanche ou refeição'),('weight','Cadastre um produto por peso'),('combo','Monte um combo'),('layout','Escolha 1, 2 ou 4 produtos'),('banner','Coloque a capa oficial da loja'),('slide','Crie um slide oficial')]
SAMPLES=[dict(id='burger',name='Lanche de exemplo',price=20),dict(id='fries',name='Batata de exemplo',price=10),dict(id='drink',name='Bebida sem marca',price=5),dict(id='whisky',name='Whisky de exemplo',price=70),dict(id='ice',name='Gelo de coco sem marca',price=4)]
PROFILE=[('display_name','Nome da loja'),('whatsapp','WhatsApp'),('description','Descrição'),('services','O que a loja oferece'),('city','Cidade'),('neighborhood','Bairro'),('avatar_filename','Logo'),('cover_filename','Capa'),('service_area','Área atendida'),('opening_hours','Horários')]

def install(g):
    def startup():
        with ledger.connection() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS onboarding_release416(id INTEGER PRIMARY KEY,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS onboarding416(professional_id INTEGER PRIMARY KEY REFERENCES professionals(id),data TEXT NOT NULL DEFAULT '{}',hidden INTEGER NOT NULL DEFAULT 0);''')
            c.execute('INSERT INTO onboarding_release416(id,created_at) VALUES(1,?) ON CONFLICT(id) DO NOTHING',(ledger.stamp(),))
    g['app'].router.add_event_handler('startup',startup)
    def load(c,pid,lock=False):
        c.execute("INSERT INTO onboarding416(professional_id) VALUES(?) ON CONFLICT(professional_id) DO NOTHING",(pid,))
        row=c.execute('SELECT * FROM onboarding416 WHERE professional_id=?'+(' FOR UPDATE' if lock and getattr(c,'dialect','sqlite')=='postgres' else ''),(pid,)).fetchone()
        return row,json.loads(row['data'])
    def status(c,p):
        row,data=load(c,p['id']);completed=data.get('completed',[])
        profile=[dict(label=label,done=bool(str(p[key] or '').strip())) for key,label in PROFILE]
        official={'profile':all(x['done'] for x in profile),'banner':bool(p['cover_filename']),'slide':bool(c.execute("SELECT 1 FROM store_banners207 WHERE professional_id=? AND image<>'' AND active=1",(p['id'],)).fetchone())}
        for key,done in official.items():
            if done and key not in completed:completed.append(key)
        data['completed']=completed
        c.execute('UPDATE onboarding416 SET data=? WHERE professional_id=?',(json.dumps(data,ensure_ascii=False),p['id']))
        tasks=[dict(id=key,title=title,done=key in completed) for key,title in TASKS]
        total=len(tasks);count=sum(t['done'] for t in tasks)
        cutoff=c.execute('SELECT created_at FROM onboarding_release416 WHERE id=1').fetchone()[0]
        def parsed(value):
            dt=datetime.fromisoformat(value.replace('Z','+00:00'));return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        return dict(tasks=tasks,percent=round(count*100/total),profile_percent=round(sum(x['done'] for x in profile)*100/len(profile)),profile=profile,complete=count==total,hidden=bool(row['hidden']),required=p['plan_active'] in ('cardapio','completo') and p['business_type']!='fashion' and parsed(p['created_at'])>=parsed(cutoff) and count<total,practice=data.get('practice',{}),samples=SAMPLES)
    def persist(c,pid,data):c.execute('UPDATE onboarding416 SET data=? WHERE professional_id=?',(json.dumps(data,ensure_ascii=False),pid))
    @g['app'].get('/painel/primeiros-passos/estado')
    def state(request:Request):
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);c.execute('BEGIN IMMEDIATE');data=status(c,p)
        return JSONResponse(data,headers={'Cache-Control':'private, no-store'})
    @g['app'].get('/painel/primeiros-passos')
    def page(request:Request):
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);c.execute('BEGIN IMMEDIATE');data=status(c,p)
        return g['templates'].TemplateResponse('onboarding416.html',g['context'](request,pro=p,learning416=data),headers={'Cache-Control':'private, no-store'})
    @g['app'].post('/painel/primeiros-passos/exercicio/{task}')
    async def practice(request:Request,task:str):
        ledger.check_origin(request)
        raw=await request.body()
        if len(raw)>20000:raise HTTPException(400,'Exercício muito grande.')
        try:values=json.loads(raw)
        except (ValueError,TypeError):raise HTTPException(400,'Confira o exercício.')
        if not isinstance(values,dict):raise HTTPException(400,'Confira o exercício.')
        allowed={'category','bases','normal','meal','weight','combo','layout'}
        if task not in allowed:raise HTTPException(400,'Etapa inválida.')
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);c.execute('BEGIN IMMEDIATE');row,data=load(c,p['id'],True)
            completed=data.get('completed',[])
            # Steps require a saved exercise, never just clicking Next.
            if task not in ('layout',):
                sequence=['category','bases','normal','meal','weight','combo']
                previous=sequence[:sequence.index(task)]
                if any(key not in completed for key in previous):raise HTTPException(409,'Conclua o exercício anterior primeiro.')
            clean={}
            if task=='layout':
                value=values.get('layout')
                if value not in ('large','pair','compact'):raise HTTPException(400,'Escolha 1, 2 ou 4 produtos.')
                g['require_premium_catalog'](c,u['id'])
                c.execute('UPDATE professionals SET carousel_layout235=? WHERE id=?',(value,p['id']));clean={'layout':value}
            else:
                name=str(values.get('name','')).strip()[:140]
                if not name:raise HTTPException(400,'Preencha o nome para praticar.')
                clean['name']=name
                if task not in ('category','bases'):
                    price=cents(values.get('price',''))
                    if price<=0:raise HTTPException(400,'Informe um preço maior que zero.')
                    clean['price_cents']=price
                if task=='bases':
                    ingredients=str(values.get('ingredients','')).strip()[:500]
                    accompaniment=str(values.get('accompaniment','')).strip()[:100]
                    extra=str(values.get('extra','')).strip()[:100]
                    price=cents(values.get('extra_price',''))
                    if not ingredients or not accompaniment or not extra or price<=0:raise HTTPException(400,'Pratique os ingredientes, um acompanhamento e um adicional pago com preço maior que zero.')
                    clean.update(ingredients=ingredients,accompaniment=accompaniment,extra=extra,extra_cents=price)
                if task=='normal':clean['category']=data.get('practice',{}).get('category',{}).get('name','Teste')
                if task=='meal':
                    ingredients=str(values.get('ingredients','')).strip()[:500]
                    try:limit=int(values.get('max_extras',0))
                    except (ValueError,TypeError):raise HTTPException(400,'Informe o limite de adicionais.')
                    if not ingredients or not 0<=limit<=20:raise HTTPException(400,'Preencha os ingredientes e um limite de 0 a 20 adicionais.')
                    clean.update(ingredients=ingredients,max_extras=limit,removable=str(values.get('removable','')).strip()[:300])
                    if limit:
                        extra=str(values.get('extra','')).strip()[:100]
                        if not extra:raise HTTPException(400,'Informe o nome do adicional ou escolha limite zero.')
                        extra_cost=cents(values.get('extra_price',''))
                        if extra_cost<=0:raise HTTPException(400,'Informe o preço do adicional pago.')
                        clean.update(extra=extra,extra_cents=extra_cost)
                if task=='weight':
                    try:grams=int(values.get('grams',0))
                    except (ValueError,TypeError):raise HTTPException(400,'Informe os gramas.')
                    if not 1<=grams<=100000:raise HTTPException(400,'Escolha de 1 a 100.000 gramas.')
                    clean.update(grams=grams,estimate_cents=(price*grams+999)//1000)
                if task=='combo':
                    items=values.get('items',[]);catalog={x['id']:x for x in SAMPLES}
                    if not isinstance(items,list) or not 1<=len(items)<=10:raise HTTPException(400,'Inclua pelo menos um item obrigatório no combo.')
                    selected=[]
                    for item in items:
                        if not isinstance(item,dict) or item.get('id') not in catalog:raise HTTPException(400,'Escolha um produto de exemplo.')
                        try:qty=int(item.get('quantity',0))
                        except (ValueError,TypeError):raise HTTPException(400,'Quantidade inválida.')
                        if not 1<=qty<=99:raise HTTPException(400,'Quantidade deve ser de 1 a 99.')
                        selected.append(dict(id=item['id'],name=catalog[item['id']]['name'],quantity=qty))
                    clean['items']=selected
            data.setdefault('practice',{})[task]=clean
            if task not in completed:completed.append(task)
            data['completed']=completed;persist(c,p['id'],data)
            data=status(c,c.execute('SELECT * FROM professionals WHERE id=?',(p['id'],)).fetchone())
        return JSONResponse(data,headers={'Cache-Control':'private, no-store'})
    @g['app'].post('/painel/primeiros-passos/preferencia')
    async def preference(request:Request):
        ledger.check_origin(request);form=await request.form()
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);c.execute('BEGIN IMMEDIATE');data=status(c,p)
            hidden=form.get('hidden')=='1'
            if hidden and not data['complete']:raise HTTPException(400,'Conclua as etapas práticas antes de ocultar o treinamento.')
            c.execute('UPDATE onboarding416 SET hidden=? WHERE professional_id=?',(int(hidden),p['id']))
        return RedirectResponse('/painel/primeiros-passos' if not hidden else '/painel',303)
    @g['app'].post('/painel/primeiros-passos/apagar-testes')
    def clear(request:Request):
        ledger.check_origin(request)
        with ledger.connection() as c:
            u,p=ledger.merchant(c,request);c.execute('BEGIN IMMEDIATE');row,data=load(c,p['id'],True)
            data['practice']={};persist(c,p['id'],data)
        return RedirectResponse('/painel/primeiros-passos',303)
