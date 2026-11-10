import json
from pathlib import Path
from bs4 import BeautifulSoup
from starlette.requests import Request
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel


def zones(channel):
    m,client,slug,pid,data,product,customer=channel
    with m.db() as c:
        c.execute("UPDATE professionals SET allows_delivery=1,city='Ubatuba' WHERE id=?",(pid,))
        for name,fee,active in [('Centro',700,1),('Estufa II',500,1),('Inativo',900,0)]:
            c.execute('INSERT INTO professional_delivery_zones(professional_id,name,name_key,fee_cents,active) VALUES(?,?,?,?,?)',(pid,name,m.zone_key89(name),fee,active))


def test_registered_delivery_has_one_selector_and_no_manual_search(channel):
    zones(channel)
    m,client,slug,pid,data,product,customer=channel
    customer.update(address='Rua teste 20',neighborhood='Estufa II')
    page=client.get('/p/'+slug+'/menu?loja=1');assert page.status_code==200
    soup=BeautifulSoup(page.text,'html.parser');fields=soup.select('[data-address] [name=neighborhood]')
    assert len(fields)==1 and fields[0].name=='select'
    assert fields[0].select_one('option[selected]')['value']=='Estufa II'
    assert not soup.select('script[src*="neighborhood-search271"]')
    assert not fields[0].select_one('option[value=Inativo]')
    data.update(fulfillment_type='delivery',address='Rua teste 20',neighborhood='Estufa II',payment_method='pix')
    r=client.post('/p/'+slug+'/menu/whatsapp',data=data);assert r.status_code==200,r.text
    assert r.json()['total_cents']==800  # 300 product + 500 selected fee
    with m.db() as c:
        row=c.execute('SELECT neighborhood,delivery_fee_cents FROM orders').fetchone()
        assert tuple(row)==('Estufa II',500)


def test_signup_uses_store_list_and_rejects_unserved_area(channel,monkeypatch):
    zones(channel)
    m,client,slug,pid,*_=channel
    path='/p/'+slug+'/cadastro'
    soup=BeautifulSoup(client.get(path).text,'html.parser')
    field=soup.select_one('[name=neighborhood]')
    assert field.name=='select' and len(soup.select('[name=neighborhood]'))==1
    assert [o.get('value') for o in field.select('option')]==['','Centro','Estufa II']
    monkeypatch.setattr(m,'normalize_email',lambda value:value.strip().lower())
    monkeypatch.setattr(m,'email_service_configured',lambda:True)
    monkeypatch.setattr(m,'send_email',lambda *a,**kw:True)
    monkeypatch.setenv('NOWUP_BASE_URL','http://testserver')
    payload=dict(name='Cliente teste',email='zone397@example.com',phone='12999998888',password='test397-password',password_confirm='test397-password',accept_terms='1',address='Rua teste 10',neighborhood='Outro',city='Ubatuba',state='SP')
    bad=client.post(path,data=payload,follow_redirects=False);assert bad.headers['location'].endswith('?erro=bairro')
    payload['neighborhood']='Estufa II'
    good=client.post(path,data=payload,follow_redirects=False);assert good.headers['location'].endswith('/aguardando')
    with m.db() as c:assert c.execute('SELECT neighborhood FROM users WHERE customer_email345=?',(payload['email'],)).fetchone()[0]=='Estufa II'


def test_no_zones_keeps_manual_neighborhood(channel):
    _,client,slug,*_=channel
    for path in ['/p/'+slug+'/cadastro','/p/'+slug+'/menu?loja=1']:
        soup=BeautifulSoup(client.get(path).text,'html.parser')
        assert soup.select_one('[name=neighborhood]').name=='input'


def test_pilot_and_primary_copy_button_use_exclusive_link(channel,monkeypatch):
    m,client,slug,pid,*_=channel
    monkeypatch.setenv('NOWUP_MENU_ORIGIN','https://menu.example.com')
    with m.db() as c:pro=dict(c.execute('SELECT * FROM professionals WHERE id=?',(pid,)).fetchone())
    pro.update(slug='adega-sede-zero',plan_active='completo')
    request=Request({'type':'http','scheme':'https','server':('vitrine.example.com',443),'method':'GET','path':'/p/adega-sede-zero/menu','query_string':b'loja=1','headers':[(b'host',b'vitrine.example.com')]})
    pilot=m.templates.env.get_template('sede_zero_piloto383.html').render(pro=pro,request=request)
    assert BeautifulSoup(pilot,'html.parser').select_one('[data-share-url]')['data-share-url']=='https://menu.example.com/p/adega-sede-zero/menu?loja=1'
    source=Path('templates/pro_panel.html').read_text()
    line=next(s for s in source.splitlines() if 'data-copy-profile' in s)
    button=m.templates.env.from_string(line).render(pro=pro,request=request)
    assert BeautifulSoup(button,'html.parser').button['data-profile-url']=='https://menu.example.com/p/adega-sede-zero/menu?loja=1'
    pro['plan_active']='vitrine'
    button=m.templates.env.from_string(line).render(pro=pro,request=request)
    assert BeautifulSoup(button,'html.parser').button['data-profile-url']=='/p/adega-sede-zero'
