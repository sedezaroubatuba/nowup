"""Editable, isolated showcase and reusable model, requested by the account owner."""
import inspect,json,secrets,shutil
from pathlib import Path
from contextlib import closing
from fastapi import Request,HTTPException
from fastapi.responses import RedirectResponse
from starlette.concurrency import run_in_threadpool
from nowup_fashion385 import seed,config

STORES={'demonstracao':('nowup-moda-demonstracao','Loja de demonstração • NowUp Moda',0),'modelo':('nowup-moda-modelo','Loja de Moda • Modelo para venda',1)}
NAMES={
 'vestido':('Vestido midi roxo','Vestido floral rosé','Vestido preto clássico','Vestido verde leve','Vestido bege casual'),
 'camiseta':('Camiseta roxa básica','Camiseta rosé algodão','Camiseta preta unissex','Camiseta verde casual','Camiseta bege oversized'),
 'tenis':('Tênis roxo casual','Tênis rosé urbano','Tênis preto confortável','Tênis verde esportivo','Tênis bege casual'),
 'sandalia':('Sandália roxa leve','Sandália rosé delicada','Sandália preta clássica','Sandália verde casual','Sandália caramelo'),
 'cinto':('Cinto roxo fino','Cinto rosé delicado','Cinto preto clássico'),
 'bolsa':('Bolsa roxa compacta','Bolsa rosé casual','Bolsa preta clássica')}

def upgrade_ai_images386(g):
    """Replace only our original sample drawings, preserving merchant edits."""
    assets=Path(__file__).parent/'static'/'fashion-ai386'
    with closing(g['db']()) as c,c:
        for asset in assets.glob('*.webp'):
            target=g['UPLOAD_DIR']/('moda386-'+asset.name)
            if not target.exists():shutil.copyfile(asset,target)
            old='moda385-'+asset.stem+'.svg'
            c.execute("UPDATE products SET image_filename=? WHERE image_filename=? AND professional_id IN (SELECT id FROM professionals WHERE is_demo=1 AND slug IN ('nowup-moda-demonstracao','nowup-moda-modelo'))",(target.name,old))

def initialize(g):
    assets=Path(__file__).parent/'static'/'fashion-demo385'
    g['UPLOAD_DIR'].mkdir(parents=True,exist_ok=True)
    for asset in assets.glob('*.svg'):
        target=g['UPLOAD_DIR']/('moda385-'+asset.name)
        if not target.exists():shutil.copyfile(asset,target)
    for kind,(slug,title,blocked) in STORES.items():
        email='moda385-'+kind+'@demo.nowup.invalid'
        with closing(g['db']()) as c,c:
            if c.execute('SELECT id FROM professionals WHERE slug=?',(slug,)).fetchone():continue
            if c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone():continue
            stamp=g['now_iso']()
            uid=c.execute("INSERT INTO users(role,name,email,password_hash,email_verified,created_at) VALUES('professional',?,?,?,1,?)",(title,email,g['hash_password'](secrets.token_urlsafe(48)),stamp)).lastrowid
            pid=c.execute("""INSERT INTO professionals(user_id,slug,display_name,business_type,offer_mode,plan_active,plan_requested,is_premium,simple_menu346,business_segment346,admission_status,blocked,is_demo,city,state,neighborhood,address,business_status,allows_pickup,allows_delivery,minimum_order_cents,description,avatar_filename,cover_filename,created_at)
             VALUES(?,?,?,'fashion','catalog','cardapio','cardapio',1,1,'Moda e acessórios','approved',?,1,'Ubatuba','SP','Centro','Endereço a definir','open',1,1,0,?,'moda385-logo.svg','moda385-cover.svg',?)""",(uid,slug,title,blocked,'Loja de demonstração. Produtos, ilustrações e preços fictícios. Edite este catálogo antes de vender.',stamp)).lastrowid
            seed(c,pid,stamp)
            category=c.execute("SELECT id FROM categories WHERE slug='moda-e-acessorios'").fetchone()
            if category:c.execute('INSERT OR IGNORE INTO professional_categories(professional_id,category_id) VALUES(?,?)',(pid,category[0]))
            ids={}
            for product_kind,names in NAMES.items():
                ids[product_kind]=[]
                for index,name in enumerate(names,1):
                    category={'vestido':'Vestidos','camiseta':'Camisetas','tenis':'Sapatos','sandalia':'Sapatos','cinto':'Acessórios','bolsa':'Acessórios'}[product_kind]
                    if index==1 and product_kind in ('vestido','camiseta','bolsa'):category='Novidades'
                    price={'vestido':9990,'camiseta':3990,'tenis':12990,'sandalia':7990,'cinto':2490,'bolsa':8990}[product_kind]+(index-1)*1000
                    size_kind='letters' if product_kind in ('vestido','camiseta') else 'numbers' if product_kind in ('tenis','sandalia') else 'none'
                    sizes='P, M, G, GG, XXG' if size_kind=='letters' else '35, 36, 37, 38, 39, 40, 41, 42' if size_kind=='numbers' else ''
                    custom=config(size_kind,sizes,'')
                    product=c.execute("""INSERT INTO products(professional_id,name,description,category,price_cents,image_filename,available,is_dish,extras_mode,customization192,recommend256,created_at,updated_at)
                     VALUES(?,?,?,?,?,?,1,?,'none',?,?,?,?)""",(pid,name,'Produto ilustrativo para demonstração. Preço fictício; confirme medidas, materiais e disponibilidade antes de vender.',category,price,f'moda385-{product_kind}-{index}.svg',int(bool(custom['groups'])),json.dumps(custom,ensure_ascii=False),int(product_kind in ('bolsa','cinto')),stamp,stamp)).lastrowid
                    ids[product_kind].append(product)
            for product in ids['vestido']:
                c.execute('UPDATE products SET related256=? WHERE id=?',(','.join(map(str,ids['bolsa'][:2]+ids['cinto'][:1]+ids['sandalia'][:2])),product))
            for product in ids['camiseta']:
                c.execute('UPDATE products SET related256=? WHERE id=?',(','.join(map(str,ids['tenis'][:2]+ids['cinto'][:2])),product))
            c.execute("INSERT INTO store_banners207(professional_id,title,image,mode,product_ids,active,link,sort_order) VALUES(?,?,?,'info','[]',1,'',0)",(pid,'Novidades da coleção','moda385-cover.svg'))
    upgrade_ai_images386(g)

def install(g):
    original_user=g['current_user']
    def scoped_user(request):
        return getattr(request.state,'fashion_owner385',None) or original_user(request)
    g['current_user']=scoped_user
    def target(request,kind):
        g['require_user'](request,'admin')
        if kind not in STORES:raise HTTPException(404)
        with closing(g['db']()) as c:
            p=c.execute('SELECT * FROM professionals WHERE slug=?',(STORES[kind][0],)).fetchone()
            if not p:raise HTTPException(404,'Loja não encontrada')
            u=c.execute('SELECT * FROM users WHERE id=?',(p['user_id'],)).fetchone()
            if u['email']!='moda385-'+kind+'@demo.nowup.invalid':raise HTTPException(403)
            return dict(p),dict(u)
    @g['app'].get('/admin/moda385/{kind}')
    def page(request:Request,kind:str):
        pro,_=target(request,kind)
        with closing(g['db']()) as c:
            products=[dict(p) for p in c.execute('SELECT * FROM products WHERE professional_id=? ORDER BY category,id',(pro['id'],))]
            categories=c.execute('SELECT * FROM product_categories WHERE professional_id=? ORDER BY sort_order,id',(pro['id'],)).fetchall()
        return g['templates'].TemplateResponse('fashion_demo385.html',g['context'](request,pro=pro,products=products,product_categories=categories,kind385=kind))
    async def save(request,kind,product_id=None):
        pro,user=target(request,kind)
        request.state.fashion_owner385=user
        form=await request.form()
        handler=g['pro_product_add'] if product_id is None else g['pro_product_edit']
        kwargs={'request':request}
        if product_id is not None:kwargs['product_id']=product_id
        for name,p in inspect.signature(handler).parameters.items():
            if name in kwargs:continue
            default=getattr(p.default,'default',p.default)
            if name in ('extra_ids','related256'):
                try:kwargs[name]=[int(v) for v in form.getlist(name)]
                except ValueError:raise HTTPException(400,'Seleção de produtos inválida')
            elif name=='extra_photos385':kwargs[name]=form.getlist(name)
            elif name in form:
                try:kwargs[name]=int(form[name]) if p.annotation is int else form[name]
                except ValueError:raise HTTPException(400,'Número inválido')
            elif name in ('name','price'):raise HTTPException(422,'Informe nome e preço')
            else:kwargs[name]=default
        await run_in_threadpool(handler,**kwargs)
        return RedirectResponse('/admin/moda385/'+kind+'?salvo=1',303)
    @g['app'].post('/admin/moda385/{kind}/produtos')
    async def add(request:Request,kind:str):return await save(request,kind)
    @g['app'].post('/admin/moda385/{kind}/produtos/{product_id}')
    async def edit(request:Request,kind:str,product_id:int):return await save(request,kind,product_id)
    @g['app'].post('/admin/moda385/{kind}/perfil')
    async def profile(request:Request,kind:str):
        pro,_=target(request,kind);f=await request.form()
        name=str(f.get('display_name','')).strip()
        if not name:raise HTTPException(400,'Informe o nome da loja')
        number=str(f.get('whatsapp','')).strip()
        if number:number=g['nowup_storeapp257'].phone(number)[2:]
        with closing(g['db']()) as c,c:
            c.execute('UPDATE professionals SET display_name=?,whatsapp=?,description=?,allows_pickup=?,allows_delivery=? WHERE id=?',(name[:120],number,str(f.get('description',''))[:1200],int(f.get('allows_pickup')=='1'),int(f.get('allows_delivery')=='1'),pro['id']))
        return RedirectResponse('/admin/moda385/'+kind+'?salvo=1',303)
