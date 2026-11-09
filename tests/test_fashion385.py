import json
import pytest
from fastapi import HTTPException
from test_merchant_signup346 import registration,registered
from test_storeapp256 import shop
from test_checkout247 import checkout
from test_merchant228 import env
from test_storeapp257 import channel
from nowup_fashion385 import config,editor,seed
from nowup_plans339 import for_store,PLANS

@pytest.mark.parametrize('kind,sizes,expected',[('letters','P, M, G, GG, XXG','Tamanho (letras)'),('numbers','35, 36, 37, 38','Numeração')])
def test_size_options_use_existing_cart_validation(kind,sizes,expected):
 from nowup_custom192 import parse_config,validate_customization
 c=parse_config(config(kind,sizes,'Preto, Branco'))
 assert c['groups'][0]['name']==expected and not c['utensils']
 assert editor(json.dumps(c))['kind']==kind
 with pytest.raises(HTTPException):validate_customization(c,{},'',False)
 selected={'removed':[],'groups':{'fashionSize385':[sizes.split(',')[0].strip()],'fashionColor385':['Preto']}}
 result=validate_customization(c,selected,'Separar para retirar',False)
 assert result
 with pytest.raises(HTTPException):validate_customization(c,{'removed':[],'groups':{'fashionSize385':['inexistente'],'fashionColor385':['Preto']}},'',False)

@pytest.mark.parametrize('kind,sizes,colors',[('letters','',''),('letters','35',''),('numbers','M',''),('letters','M, m',''),('unknown','M',''),('none','','Preto, Preto')])
def test_invalid_sizes(kind,sizes,colors):
 with pytest.raises(HTTPException):config(kind,sizes,colors)

def test_fashion_signup_simple_plan_category_novidades_and_price(registration):
 m,client,payload,_=registration
 data=payload();data.update(business_type='fashion',offer_mode='menu',city='São Sebastião')
 r=client.post('/cadastro/profissional',data=data)
 assert r.status_code==303 and r.headers['location']=='/cadastro/aguardando',r.text
 p=registered(m,data['email']);assert p['business_type']=='fashion' and p['offer_mode']=='catalog' and p['simple_menu346']==1
 assert p['plan_requested']=='cardapio' and for_store(p)['cardapio'][1]==3990
 with m.db() as c:
  names={row[0] for row in c.execute('SELECT name FROM product_categories WHERE professional_id=?',(p['id'],))}
  assert {'Novidades','Roupas','Vestidos','Camisetas','Sapatos','Acessórios'}<=names
  assert c.execute('SELECT c.slug FROM professional_categories pc JOIN categories c ON c.id=pc.category_id WHERE pc.professional_id=?',(p['id'],)).fetchone()[0]=='moda-e-acessorios'
 from pathlib import Path
 Path('/tmp/fashion-signup385.html').write_text(client.get('/cadastro/profissional').text)
 assert PLANS['cardapio'][1]==4990 and for_store({'business_type':'store'})['cardapio'][1]==4990
 data=payload();data.update(business_type='fashion',plan='ambos')
 assert 'erro=plano' in client.post('/cadastro/profissional',data=data).headers['location']

def test_create_edit_fashion_product_and_merchant_render(shop,monkeypatch):
 m,client,slug,store_id,url,order_data,old_product=shop
 for callback in m.app.router.on_startup:
  if callback.__name__!='start':callback()
 with m.db() as c:
  c.execute("UPDATE professionals SET business_type='fashion',offer_mode='catalog',plan_active='cardapio' WHERE id=?",(store_id,))
  uid=c.execute('SELECT user_id FROM professionals WHERE id=?',(store_id,)).fetchone()[0]
  seed(c,store_id,m.now_iso())
 monkeypatch.setattr(m,'current_user',lambda request:{'id':uid,'role':'professional'})
 data=dict(name='Vestido',category='Novidades',price='129,90',available='1',size_kind385='letters',sizes385='P, M, G',colors385='Roxo, Preto',extras_mode='none')
 r=client.post('/painel/cardapio/produtos',data=data,follow_redirects=False);assert r.status_code==303,r.text
 with m.db() as c:
  product=c.execute("SELECT * FROM products WHERE professional_id=? AND name='Vestido'",(store_id,)).fetchone()
  custom=json.loads(product['customization192']);assert custom['groups'][0]['options']==['P','M','G']
 page=client.get('/painel');assert page.status_code==200,page.text[:500]
 from pathlib import Path
 Path('/tmp/fashion-panel385.html').write_text(page.text)
 public=client.get('/p/'+slug+'/menu');assert public.status_code==200,public.text[:500]
 assert '/static/fashion385.js?v=385' in public.text and 'data-fashion-photos385=' in public.text
 assert 'name="size_kind385"' in page.text and 'Moda e acessórios' in page.text and 'Novidades' in page.text
 data.update(size_kind385='numbers',sizes385='36, 38, 40')
 r=client.post('/painel/cardapio/produtos/'+str(product['id']),data=data,follow_redirects=False);assert r.status_code==303,r.text
 with m.db() as c:assert json.loads(c.execute('SELECT customization192 FROM products WHERE id=?',(product['id'],)).fetchone()[0])['groups'][0]['name']=='Numeração'
 for key in ['is_combo256','sold_by_weight370']:
  assert client.post('/painel/cardapio/produtos',data={**data,key:'1'},follow_redirects=False).status_code==400


def test_gallery_limit_and_preservation():
 from nowup_fashion385 import save_photos
 from types import SimpleNamespace as S
 calls=[]
 class Conn:
  def execute(self,*args):calls.append(args)
 g={'save_image':lambda u:u.filename}
 save_photos(g,Conn(),1,[]);assert calls==[]
 with pytest.raises(HTTPException):save_photos(g,Conn(),1,[S(filename=str(i)+'.jpg') for i in range(5)])
 assert calls==[]
 save_photos(g,Conn(),1,[S(filename='foto.jpg'),S(filename='costas.jpg')])
 assert json.loads(calls[0][1][0])==['foto.jpg','costas.jpg']


def test_demo_stores_editable_isolated_and_seed_is_idempotent(checkout,monkeypatch):
 m,client,*_=checkout
 for callback in m.app.router.on_startup:
  if callback.__name__!='start':callback()
 from nowup_fashion_demo385 import initialize
 with m.db() as c:
  demo=dict(c.execute("SELECT * FROM professionals WHERE slug='nowup-moda-demonstracao'").fetchone())
  model=dict(c.execute("SELECT * FROM professionals WHERE slug='nowup-moda-modelo'").fetchone())
  assert demo['is_demo']==1 and demo['blocked']==0 and model['blocked']==1
  assert c.execute('SELECT COUNT(*) FROM products WHERE professional_id=?',(demo['id'],)).fetchone()[0]==26
  assert c.execute('SELECT COUNT(*) FROM products WHERE professional_id=?',(model['id'],)).fetchone()[0]==26
  product=dict(c.execute('SELECT * FROM products WHERE professional_id=? ORDER BY id',(demo['id'],)).fetchone())
  assert product['related256']
  assert c.execute("SELECT COUNT(*) FROM products WHERE professional_id=? AND image_filename LIKE 'moda386-%'",(demo['id'],)).fetchone()[0]==26
  c.execute("UPDATE products SET name='Editado pelo dono',image_filename='foto-personalizada.webp' WHERE id=?",(product['id'],))
  admin=dict(c.execute("SELECT * FROM users WHERE role='admin' LIMIT 1").fetchone())
 initialize(vars(m))
 with m.db() as c:
  edited=c.execute('SELECT name,image_filename FROM products WHERE id=?',(product['id'],)).fetchone()
  assert edited[0]=='Editado pelo dono' and edited[1]=='foto-personalizada.webp'
 assert client.get('/admin/moda385/demonstracao').status_code in (303,403)
 monkeypatch.setattr(m,'current_user',lambda request:getattr(request.state,'fashion_owner385',None) or admin)
 response=client.get('/admin/moda385/demonstracao');assert response.status_code==200,response.text[:500]
 assert '26 produtos cadastrados' in response.text
 saved=client.post('/admin/moda385/demonstracao/produtos/'+str(product['id']),data={'name':'Vestido editado','price':'149,90','category':'Vestidos','size_kind385':'letters','sizes385':'M, G','extras_mode':'none','available':'1'},follow_redirects=False)
 assert saved.status_code==303,saved.text
 with m.db() as c:
  assert c.execute('SELECT name FROM products WHERE id=?',(product['id'],)).fetchone()[0]=='Vestido editado'
  foreign=c.execute('SELECT id FROM products WHERE professional_id=?',(model['id'],)).fetchone()[0]
 assert client.post('/admin/moda385/demonstracao/produtos/'+str(foreign),data={'name':'Intruso','price':'1','category':'Vestidos'},follow_redirects=False).status_code==404
 monkeypatch.setattr(m,'current_user',lambda request:None)
 public=client.get('/p/nowup-moda-demonstracao/menu');assert public.status_code==200,public.text[:500]
 assert 'data-demo-browse386="1" data-login-required="0"' in public.text
 assert 'Demonstração • acesso livre' in public.text and '"demoBrowse386": true' in public.text
 normal=client.get('/p/'+demo['slug'].replace('nowup-moda-demonstracao','not-a-store')+'/menu')
 assert normal.status_code==404
 assert client.get('/p/nowup-moda-modelo/menu').status_code==404


def test_fashion_whatsapp_selection_has_sizes_and_combined_payment(channel):
 m,client,slug,pid,data,product,customer=channel
 from nowup_custom192 import save_config
 with m.db() as c:
  c.execute("UPDATE professionals SET business_type='fashion',offer_mode='catalog',plan_active='cardapio' WHERE id=?",(pid,))
  save_config(c,product,config('letters','P, M, G','Preto, Branco'))
 data['payment_method']='pix'
 data['cart_json']=json.dumps([{'id':product,'quantity':1,'customization':{'removed':[],'groups':{'fashionSize385':['M'],'fashionColor385':['Preto']}}}])
 r=client.post('/p/'+slug+'/menu/whatsapp',data=data)
 assert r.status_code==200,r.text
 result=r.json();assert 'confirmar a disponibilidade' in result['message'] and 'M' in result['message'] and 'Preto' in result['message']
 assert 'Pagamento a combinar pelo WhatsApp.' in result['message'] and 'whatsapp_url' in result
 with m.db() as c:assert c.execute('SELECT payment_method FROM orders').fetchone()[0]=='on_delivery'
