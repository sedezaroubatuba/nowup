import pytest
from test_audit255 import panel
from test_checkout247 import checkout


def test_marketplace_opening_and_independent_store_modes(panel,monkeypatch):
 m,client,_=panel;monkeypatch.setattr(m,'current_user',lambda request:None)
 home=client.get('/?abertura=1');assert home.status_code==200,home.text[:200]
 assert 'id="nowup-opening260"' in home.text and 'data-opening-mode="nowup"' in home.text and 'nowup-opening488.webp' in home.text
 assert 'Seu bairro.' not in home.text
 assert 'opening-config260' in home.text
 assert 'id="nowup-opening260"' in client.get('/entrar').text
 with m.db() as c:
  slug=c.execute('SELECT slug FROM professionals ORDER BY id LIMIT 1').fetchone()[0]
  c.execute("UPDATE professionals SET plan_active='completo',is_premium=1,offer_mode='menu',admission_status='approved',blocked=0 WHERE slug=?",(slug,))
 assert 'id="nowup-opening260"' not in client.get('/p/'+slug+'/menu?loja=1').text
 store=client.get('/p/'+slug+'/cardapio');assert store.status_code==200,store.text[:200]
 mode='sede' if slug in ('adega-sede-zero','samuel-dos-santos-silva') else 'bike'
 assert 'data-opening-mode="'+mode+'"' in store.text and '#24272d' in store.text


def test_super_admin_saves_validated_real_settings(panel,monkeypatch):
 m,client,_=panel;monkeypatch.setattr(m,'current_user',lambda request:None)
 r=client.post('/admin/super/abertura',data={'enabled':'1','sound':'1','duration':3100,'color':'#123456','frequency':'session'},follow_redirects=False)
 assert r.status_code==303,r.text
 page=client.get('/admin/super/abertura');assert page.status_code==200 and '3100' in page.text
 home=client.get('/').text;assert '"duration": 3100' in home and '"sound": true' in home
 with m.db() as c:assert c.execute("SELECT value FROM site_settings WHERE key='opening260_color'").fetchone()[0]=='#123456'
 assert client.post('/admin/super/abertura',data={'duration':999999,'color':'red'}).status_code==400
 r=client.post('/admin/super/abertura',data={'duration':4200,'color':'#7136bf','frequency':'daily'},follow_redirects=False);assert r.status_code==303
 assert 'id="nowup-opening260"' not in client.get('/').text
 assert 'id="nowup-opening260"' in client.get('/?abertura=1').text


def test_settings_reject_unauthenticated_and_staff(panel,monkeypatch):
 import nowup_admin227 as admin
 m,client,_=panel;monkeypatch.setitem(admin.G,'current_user',lambda request:None)
 assert client.get('/admin/super/abertura').status_code==401
 monkeypatch.setattr(admin,'auth',lambda request,c:{'super':False})
 assert client.get('/admin/super/abertura').status_code==403
 assert client.post('/admin/super/abertura',data={}).status_code==403
