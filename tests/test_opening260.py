import pytest
from test_audit255 import panel
from test_checkout247 import checkout


def test_home_opening_is_message_free_and_only_home(panel,monkeypatch):
 m,client,_=panel;monkeypatch.setattr(m,'current_user',lambda request:None)
 home=client.get('/?abertura=1');assert home.status_code==200,home.text[:200]
 assert 'id="nowup-opening490"' in home.text and 'opening490-nowup.mp4' in home.text
 assert 'Seu bairro.' not in home.text
 assert 'data-opening-scope="nowup"' in home.text
 assert 'id="nowup-opening490"' in client.get('/entrar').text
 with m.db() as c:
  slug=c.execute('SELECT slug FROM professionals ORDER BY id LIMIT 1').fetchone()[0]
  c.execute("UPDATE professionals SET plan_active='completo' WHERE slug=?",(slug,))
 assert 'id="nowup-opening490"' not in client.get('/p/'+slug+'/menu?loja=1').text


def test_super_admin_saves_validated_real_settings(panel,monkeypatch):
 m,client,_=panel;monkeypatch.setattr(m,'current_user',lambda request:None)
 r=client.post('/admin/super/abertura',data={'enabled':'1','sound':'1','duration':3100,'color':'#123456','frequency':'session'},follow_redirects=False)
 assert r.status_code==303,r.text
 page=client.get('/admin/super/abertura');assert page.status_code==200 and '3100' in page.text
 home=client.get('/').text;assert 'opening490-nowup.mp4' in home
 with m.db() as c:assert c.execute("SELECT value FROM site_settings WHERE key='opening260_color'").fetchone()[0]=='#123456'
 assert client.post('/admin/super/abertura',data={'duration':999999,'color':'red'}).status_code==400
 r=client.post('/admin/super/abertura',data={'duration':4200,'color':'#7136bf','frequency':'daily'},follow_redirects=False);assert r.status_code==303
 assert 'id="nowup-opening490"' not in client.get('/').text
 assert 'id="nowup-opening490"' in client.get('/?abertura=1').text


def test_settings_reject_unauthenticated_and_staff(panel,monkeypatch):
 import nowup_admin227 as admin
 m,client,_=panel;monkeypatch.setitem(admin.G,'current_user',lambda request:None)
 assert client.get('/admin/super/abertura').status_code==401
 monkeypatch.setattr(admin,'auth',lambda request,c:{'super':False})
 assert client.get('/admin/super/abertura').status_code==403
 assert client.post('/admin/super/abertura',data={}).status_code==403


def test_sede_zero_uses_its_own_approved_video_only_on_store_entry(panel):
 from types import SimpleNamespace
 m,_,_=panel
 template=m.templates.env.get_template('opening260.html')
 store={'slug':'adega-sede-zero','menu':'/p/adega-sede-zero/cardapio'}
 def page(path,store):
  return template.render(request=SimpleNamespace(url=SimpleNamespace(path=path),query_params={}),store_app256=store,order_link377=False,settings={})
 home=page('/p/adega-sede-zero/cardapio',store)
 assert 'data-opening-scope="sede-zero"' in home and 'opening490-sede-zero.mp4' in home
 assert 'opening490-nowup.mp4' not in home
 assert 'id="nowup-opening490"' not in page('/p/adega-sede-zero/pedidos',store)
 assert 'id="nowup-opening490"' not in page('/p/outra-loja/cardapio',{'slug':'outra-loja','menu':'/p/outra-loja/cardapio'})
