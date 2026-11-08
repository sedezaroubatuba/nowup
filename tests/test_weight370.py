import io,json
import pytest
from PIL import Image
from fastapi import HTTPException
from test_checkout247 import checkout
from test_storeapp257 import channel
from test_storeapp256 import shop
from nowup_weight370 import portion_cents,weight_label

@pytest.mark.parametrize('rate,grams,total',[(7500,1200,9000),(7500,200,1500),(6599,1200,7919),(6599,300,1980),(5,100,1),(7500,1000,7500)])
def test_exact_portion_price(rate,grams,total):
 assert portion_cents(rate,grams)==total

@pytest.mark.parametrize('value',[None,True,0,-100,150,100.0,'200',100000])
def test_invalid_weights(value):
 with pytest.raises(HTTPException):portion_cents(7500,value)

def weighted(m,pid,rate=7500,promo=0):
 with m.db() as c:c.execute("UPDATE products SET name='Mussarela',price_cents=?,promo_price_cents=?,sold_by_weight370=1,is_combo256=0,is_dish=0,extras_mode='none',customization192='' WHERE id=?",(rate,promo,pid))


def test_internal_order_keeps_weight_rate_fixed_total_and_idempotency(checkout):
 m,client,url,data,pid,_=checkout;weighted(m,pid,6599)
 data['cart_json']=json.dumps([{'id':pid,'quantity':1,'weight_grams370':1200,'price':1}])
 a=client.post(url,data=data,follow_redirects=False);assert a.status_code==303,a.text
 assert client.post(url,data=data,follow_redirects=False).headers['location']==a.headers['location']
 with m.db() as c:
  assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==1
  assert c.execute('SELECT total_cents FROM orders').fetchone()[0]==7919
  item=c.execute('SELECT * FROM order_items').fetchone()
  assert item['weight_grams370']==1200 and item['price_per_kg370']==6599
  assert item['quantity']==1 and item['unit_price_cents']==7919
  assert '1,2 kg (1.200 g)' in item['product_name']
  assert 'Não cobre pelo excedente' in item['notes']

@pytest.mark.parametrize('grams',[0,True,150,100.1,'1200',100000,None])
def test_checkout_rejects_invalid_weight_without_order(checkout,grams):
 m,client,url,data,pid,_=checkout;weighted(m,pid)
 data['cart_json']=json.dumps([{'id':pid,'quantity':1,'weight_grams370':grams}])
 assert client.post(url,data=data,follow_redirects=False).status_code==400
 with m.db() as c:assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==0


def test_unweighted_product_rejects_forged_weight(checkout):
 m,client,url,data,pid,_=checkout
 data['cart_json']=json.dumps([{'id':pid,'quantity':1,'weight_grams370':100}])
 assert client.post(url,data=data,follow_redirects=False).status_code==400

@pytest.mark.parametrize('qty',[2,99])
def test_weighted_portion_cannot_be_multiplied_as_units(checkout,qty):
 m,client,url,data,pid,_=checkout;weighted(m,pid)
 data['cart_json']=json.dumps([{'id':pid,'quantity':qty,'weight_grams370':200}])
 assert client.post(url,data=data,follow_redirects=False).status_code==400

@pytest.mark.parametrize('mode',['whatsapp','panel','both'])
def test_weighted_independent_channels_use_same_promotion_and_message(channel,mode):
 m,client,slug,store,data,pid,_=channel;weighted(m,pid,7500,6500)
 with m.db() as c:c.execute("INSERT INTO store_menu257(professional_id,whatsapp,mode) VALUES(?,'5512999999999',?)",(store,mode))
 data['cart_json']=json.dumps([{'id':pid,'quantity':1,'weight_grams370':1200}])
 r=client.post('/p/'+slug+'/menu/whatsapp',data=data);assert r.status_code==200,r.text
 result=r.json();assert result['total_cents']==7800
 assert '1,2 kg (1.200 g)' in str(result['receipt']) and '78,00' in str(result['receipt'])
 assert 'Não cobre pelo excedente' in result['message']
 if mode!='whatsapp':
  with m.db() as c:assert c.execute('SELECT weight_grams370 FROM order_items').fetchone()[0]==1200


def test_merchant_create_edit_photo_and_basic_form(checkout,monkeypatch):
 m,client,_,_,pid,_=checkout
 with m.db() as c:
  p=c.execute('SELECT p.* FROM professionals p JOIN products r ON r.professional_id=p.id WHERE r.id=?',(pid,)).fetchone()
  c.execute("UPDATE professionals SET plan_active='cardapio' WHERE id=?",(p['id'],))
  owner=dict(c.execute('SELECT * FROM users WHERE id=?',(p['user_id'],)).fetchone())
 monkeypatch.setattr(m,'current_user',lambda request:owner)
 photo=io.BytesIO();Image.new('RGB',(64,64),'yellow').save(photo,'JPEG')
 fields={'name':'Queijo por peso','category':'Frios','price':'75,00','promo_price':'65,00','sold_by_weight370':'1','extras_mode':'none','is_combo256':'0','available':'1','recommend256':'1'}
 r=client.post('/painel/cardapio/produtos',data=fields,files={'photo':('cheese.jpg',photo.getvalue(),'image/jpeg')},follow_redirects=False);assert r.status_code==303,r.text
 with m.db() as c:
  item=dict(c.execute('SELECT * FROM products WHERE name=?',(fields['name'],)).fetchone())
  assert item['sold_by_weight370']==1 and item['recommend256']==1 and item['price_cents']==7500 and item['promo_price_cents']==6500
  assert (m.UPLOAD_DIR/item['image_filename']).exists()
 assert client.post('/painel/cardapio/produtos/'+str(item['id']),data={**fields,'price':'80,00'},follow_redirects=False).status_code==303
 # Cannot turn an existing weighted product into a combo, even through a forged form.
 assert client.post('/painel/cardapio/produtos/'+str(item['id']),data={**fields,'is_combo256':'1'},follow_redirects=False).status_code==400


def test_weighted_cannot_be_bound_to_combo(checkout):
 from nowup_custom192 import parse_config,bind_combo_products
 m,_,_,_,pid,_=checkout;weighted(m,pid)
 config=parse_config({'combo_items':[{'product_id':pid,'name':'Mussarela','quantity':1}]})
 with m.db() as c:
  pro=c.execute('SELECT professional_id FROM products WHERE id=?',(pid,)).fetchone()[0]
  with pytest.raises(HTTPException):bind_combo_products(c,pro,config)


def test_weighted_mixed_cart_and_catalog_price_change_do_not_reprice_order(checkout):
 m,client,url,data,pid,_=checkout;weighted(m,pid,7500)
 with m.db() as c:
  pro=c.execute('SELECT professional_id FROM products WHERE id=?',(pid,)).fetchone()[0]
  stamp=m.now_iso();other=c.execute("INSERT INTO products(professional_id,name,price_cents,extras_mode,created_at,updated_at) VALUES(?,'Refrigerante',500,'none',?,?)",(pro,stamp,stamp)).lastrowid
 data['cart_json']=json.dumps([{'id':pid,'quantity':1,'weight_grams370':1200},{'id':other,'quantity':2}])
 assert client.post(url,data=data,follow_redirects=False).status_code==303
 with m.db() as c:
  c.execute('UPDATE products SET price_cents=99900 WHERE id=?',(pid,))
  assert c.execute('SELECT total_cents FROM orders').fetchone()[0]==10000
  assert c.execute('SELECT price_per_kg370 FROM order_items WHERE product_id=?',(pid,)).fetchone()[0]==7500


def test_duplicate_portions_rejected_so_weight_is_one_total(checkout):
 m,client,url,data,pid,_=checkout;weighted(m,pid)
 data['cart_json']=json.dumps([{'id':pid,'quantity':1,'weight_grams370':100}]*2)
 assert client.post(url,data=data,follow_redirects=False).status_code==400


def test_weighted_order_cannot_have_quantity_or_price_changed_in_revision(checkout):
 from nowup_review127 import build_items
 m,client,url,data,pid,_=checkout;weighted(m,pid)
 data['cart_json']=json.dumps([{'id':pid,'quantity':1,'weight_grams370':200}])
 assert client.post(url,data=data,follow_redirects=False).status_code==303
 with m.db() as c:
  order=c.execute('SELECT * FROM orders').fetchone();item=c.execute('SELECT * FROM order_items').fetchone()
  with pytest.raises(HTTPException):build_items(c,order,[str(item['id'])],{str(item['id']):2},[])
  with pytest.raises(HTTPException):build_items(c,order,[str(item['id'])],{},[(pid,1)])
  items,total=build_items(c,order,[str(item['id'])],{},[])
  assert total==1500 and items[0]['weight_grams370']==200
