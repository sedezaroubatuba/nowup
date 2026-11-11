from bs4 import BeautifulSoup
from test_merchant228 import env


def test_cardapio_and_vitrine_are_disjoint_with_same_owner_session(env):
    m,client,ids,pid,other=env
    with m.db() as c:
        oid=c.execute("INSERT INTO orders(professional_id,customer_name,status,total_cents,created_at,updated_at,fulfillment_type,order_origin,tracking_token) VALUES(?,'EXCLUSIVE-CARDAPIO408','new',4000,?,?,'pickup','external','external408token')",(pid,m.now_iso(),m.now_iso())).lastrowid
        c.execute("INSERT INTO order_items(order_id,product_name,quantity,unit_price_cents) VALUES(?,'Produto408',1,4000)",(oid,))
    menu=client.get('/painel/cardapio/pedidos')
    assert menu.status_code==200 and 'EXCLUSIVE-CARDAPIO408' in menu.text
    assert 'Finalizado hoje' not in menu.text and 'Outra loja' not in menu.text
    assert not BeautifulSoup(menu.text,'html.parser').select('[data-order-alerts]')
    fragment=client.get('/painel/cardapio/pedidos?fragment=1')
    assert fragment.status_code==200 and 'EXCLUSIVE-CARDAPIO408' in fragment.text
    assert '<html' not in fragment.text
    main=client.get('/painel')
    assert main.status_code==200
    board=BeautifulSoup(main.text,'html.parser').select_one('[data-board228]')
    assert 'EXCLUSIVE-CARDAPIO408' not in board.text


def test_category_waits_for_admin_approval(env):
    m,client,ids,pid,other=env
    with m.db() as c:
        category=c.execute('SELECT id FROM categories WHERE active=1 ORDER BY id DESC LIMIT 1').fetchone()['id']
        before=[r[0] for r in c.execute('SELECT category_id FROM professional_categories WHERE professional_id=?',(pid,))]
        user_id=c.execute('SELECT user_id FROM professionals WHERE id=?',(pid,)).fetchone()[0]
    response=client.post('/painel/plano',data={'plan':'completo','offer_mode':'menu','category_id':category},follow_redirects=False)
    assert response.status_code==303
    with m.db() as c:
        assert [r[0] for r in c.execute('SELECT category_id FROM professional_categories WHERE professional_id=?',(pid,))]==before
        p=c.execute('SELECT plan_requested,plan_category408 FROM professionals WHERE id=?',(pid,)).fetchone()
        assert p['plan_requested']=='completo' and p['plan_category408']==category
        m.nowup_channels408.approve_category(c,pid)
        assert [r[0] for r in c.execute('SELECT category_id FROM professional_categories WHERE professional_id=?',(pid,))]==[category]
        c.rollback()
