from test_checkout247 import checkout
from test_storeapp256 import shop


def test_whatsapp_sales_limitation_is_visible_in_both_reports(shop,monkeypatch):
    m,client,slug,pid,*_=shop
    m.nowup_sales107.initialize()
    with m.db() as c:
        owner=dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?',(pid,)).fetchone())
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    for path in ['/painel','/painel/vendas-manuais/relatorios']:
        r=client.get(path)
        assert r.status_code==200,r.text
        assert 'não são registrados automaticamente como vendas' in r.text
        assert 'registre a venda manualmente' in r.text
