from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel
from test_order_link377 import setup_order

def test_external_pix_confirmation_starts_preparation_once(channel,monkeypatch):
    m,client,result,o,item,owner,buyer=setup_order(channel)
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    with m.db() as c:
        m.nowup_notinha401.initialize(c)
        c.execute("UPDATE orders SET order_origin='external',status='confirmed' WHERE id=?",(o['id'],))
    endpoint='/painel/pedidos/'+str(o['id'])+'/conferir-pix'
    for _ in range(2):
        r=client.post(endpoint,headers={'Accept':'application/json'})
        assert r.status_code==200,r.text
    with m.db() as c:
        assert c.execute('SELECT status FROM orders WHERE id=?',(o['id'],)).fetchone()[0]=='preparing'
        assert c.execute("SELECT COUNT(*) FROM order_status_history WHERE order_id=? AND status='preparing'",(o['id'],)).fetchone()[0]==1
    assert 'data-pix-customer430' in client.get('/pedido/'+o['tracking_token']).text
