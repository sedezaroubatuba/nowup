import pytest
from test_storeapp257 import channel
from test_storeapp256 import shop
from test_checkout247 import checkout

def test_neighborhood_list_and_server_rates(channel):
    m,client,slug,pid,data,product,customer=channel
    with m.db() as c:
        c.execute('UPDATE professionals SET allows_delivery=1 WHERE id=?',(pid,))
        for name,fee,active in [('Centro',700,1),('Estufa II',500,1),('Inativo',900,0)]:
            c.execute('INSERT INTO professional_delivery_zones(professional_id,name,name_key,fee_cents,eta_minutes,active) VALUES(?,?,?,?,?,?)',(pid,name,m.zone_key89(name),fee,40,active))
    page=client.get('/p/'+slug+'/menu')
    assert page.status_code==200
    assert 'data-delivery-zone265' in page.text
    assert 'value="Centro" data-fee="700"' in page.text
    assert 'value="Inativo" data-fee=' not in page.text
    with m.db() as c:
        pro=c.execute('SELECT * FROM professionals WHERE id=?',(pid,)).fetchone()
        assert m.delivery_quote89(c,pro,'estufa ii')==(500,'Estufa II')
        assert m.delivery_quote89(c,pro,'Centro')==(700,'Centro')
        for name in ['Inativo','Outro bairro','']:
            with pytest.raises(m.HTTPException):m.delivery_quote89(c,pro,name)
