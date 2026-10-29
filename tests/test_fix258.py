from datetime import datetime,date
import pytest
from test_storeapp257 import channel
from test_storeapp256 import shop
from test_checkout247 import checkout


def test_original_and_independent_login_are_rate_limited(channel,monkeypatch):
 import admin_customization
 m,client,slug,*_=channel;monkeypatch.setattr(admin_customization,'db',m.db)
 for _ in range(10):assert client.post('/p/'+slug+'/entrar',data={'email':'rate258@example.invalid','password':'invalid'},follow_redirects=False).status_code==303
 assert client.post('/entrar',data={'email':'rate258@example.invalid','password':'invalid'},follow_redirects=False).status_code==429


def test_refused_orders_and_local_date_match_period_summary(channel,monkeypatch):
 m,client,slug,pid,data,product,customer=channel
 with m.db() as c:
  owner=dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?',(pid,)).fetchone())
  for status,total,stamp in [('completed',1000,'2026-10-30T01:30:00+00:00'),('rejected',2000,'2026-10-29T15:00:00+00:00'),('completed',4000,'2026-10-30T04:00:00+00:00')]:
   c.execute('INSERT INTO orders(professional_id,customer_name,status,total_cents,created_at,updated_at) VALUES(?,?,?,?,?,?)',(pid,'Audit',status,total,stamp,stamp))
 m.nowup_sales107.initialize();monkeypatch.setattr(m,'current_user',lambda request:owner)
 page=client.get('/painel?inicio=2026-10-29&fim=2026-10-29&pedido_dia=2026-10-29')
 assert page.status_code==200,page.text[:200]
 assert page.context['order_summary']['revenue_cents']==1000
 assert page.context['day_order_summary']['revenue_cents']==1000
 assert page.context['order_summary']['avg_ticket_cents']==1000


@pytest.mark.parametrize('independent',[True,False])
def test_disabled_category_cannot_be_bought_from_stale_cart(channel,independent):
 m,client,slug,pid,data,product,customer=channel
 with m.db() as c:
  c.execute("UPDATE products SET category='Paused258' WHERE id=?",(product,))
  c.execute("INSERT INTO product_categories(professional_id,name,sort_order,active,created_at) VALUES(?,'Paused258',1,0,?)",(pid,m.now_iso()))
 response=client.post('/p/'+slug+'/menu/'+('whatsapp' if independent else 'pedido'),data=data)
 assert response.status_code==400,response.text
 with m.db() as c:assert c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==0


def test_products_use_deferred_urls_and_store_brand_stays_visible(channel):
 m,client,slug,pid,data,product,customer=channel
 from PIL import Image
 Image.new('RGB',(20,20),'purple').save(m.UPLOAD_DIR/'photo258.jpg')
 with m.db() as c:c.execute("UPDATE products SET image_filename='photo258.jpg' WHERE id=?",(product,))
 page=client.get('/p/'+slug+'/menu?loja=1');assert page.status_code==200
 assert 'data-src258="/uploads/photo258.jpg"' in page.text
 assert '/static/images258.js?v=258' in page.text
 assert 'Entrar para pedir' not in page.text
