import os
from pathlib import Path
from bs4 import BeautifulSoup
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from test_order_link377 import setup_order


def test_receipt_visual_structure_is_shared_by_marketplace_and_catalogue(channel,monkeypatch):
    m,client,result,o,item,owner,buyer=setup_order(channel)
    with m.db() as c:m.nowup_notinha401.initialize(c)
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    assert client.post('/painel/pedidos/'+str(o['id'])+'/status',data={'status':'confirmed'},follow_redirects=False).status_code==303
    assert client.post('/painel/pedidos/'+str(o['id'])+'/conferir-pix',follow_redirects=False).status_code==303
    for path in ['/pedidos/'+str(o['id'])+'/notinha','/p/'+channel[2]+'/pedidos/'+str(o['id'])+'/notinha']:
        response=client.get(path);assert response.status_code==200
        page=BeautifulSoup(response.text,'html.parser')
        assert page.select_one('.nu406-brand h2')
        assert page.select_one('.nu406-grand-total strong').text=='R$ 3,00'
        assert page.select_one('.nu406-payment.is-paid')
        assert page.select_one('.nu406-item')
        assert not page.select_one('pre.nu401-paper')
    if os.getenv('NOWUP_RECEIPT_PREVIEW406'):
        Path(os.environ['NOWUP_RECEIPT_PREVIEW406']).write_text(response.text)
