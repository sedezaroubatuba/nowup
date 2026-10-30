import pytest
import nowup_neighborhoods267 as catalog
from test_delivery265 import channel,shop,checkout

def test_canonical_names():
    assert catalog.canonical('Ubatuba','ESTUFA 2')=='Estufa II'
    assert catalog.canonical('Ubatuba','Pereque Acu')=='Perequê-Açu'
    assert catalog.canonical('Ubatuba','Bairro inventado') is None
    assert not catalog.names('Outra cidade')
    assert len(catalog.NAMES)==len(set(catalog.NAMES))

def test_store_curated_and_manual_names_keep_own_rate(channel,monkeypatch):
    m,client,slug,pid,data,product,customer=channel
    with m.db() as c:
        c.execute("UPDATE professionals SET city='Ubatuba' WHERE id=?",(pid,))
        owner=dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?',(pid,)).fetchone())
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    path='/painel/cardapio/entregas89'
    response=client.post(path,data={'name':'Estufa 2','fee':'7,50','eta_minutes':'40','active':'1'},follow_redirects=False)
    assert response.status_code==303,response.text
    assert client.post(path,data={'name':'Estufa II','fee':'1','active':'1'}).status_code==400
    assert client.post(path,data={'name':'Inventado','fee':'1','active':'1'}).status_code==400
    with m.db() as c:
        zone=c.execute('SELECT * FROM professional_delivery_zones WHERE professional_id=?',(pid,)).fetchone()
        assert zone['name']=='Estufa II' and zone['fee_cents']==750
        pro=c.execute('SELECT * FROM professionals WHERE id=?',(pid,)).fetchone()
        assert m.delivery_quote89(c,pro,'estufa 2')==(750,'Estufa II')

    response=client.post(path,data={'name':'  Bairro Novo  ','manual':'1','fee':'9,50','active':'1'},follow_redirects=False)
    assert response.status_code==303
    assert response.headers['location'].endswith('#bairros-entrega265')
    assert client.post(path,data={'name':'bairro novo','manual':'1','fee':'1','active':'1'}).status_code==400
    assert client.post(path,data={'name':'x','manual':'1','fee':'1','active':'1'}).status_code==400
    with m.db() as c:
        pro=c.execute('SELECT * FROM professionals WHERE id=?',(pid,)).fetchone()
        assert m.delivery_quote89(c,pro,'BAIRRO NOVO')==(950,'Bairro Novo')
