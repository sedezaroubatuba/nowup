from test_checkout247 import checkout
from test_storeapp256 import shop


def test_whatsapp_reports_explain_new_recorded_flow(shop,monkeypatch):
    m,client,slug,pid,*_=shop
    m.nowup_sales107.initialize()
    with m.db() as c:
        owner=dict(c.execute('SELECT u.* FROM users u JOIN professionals p ON p.user_id=u.id WHERE p.id=?',(pid,)).fetchone())
    monkeypatch.setattr(m,'current_user',lambda request:owner)
    panel=client.get('/painel')
    assert panel.status_code==200
    assert 'O WhatsApp recebe o link do pedido.' in panel.text
    assert 'podem ser revisados pelo link' in panel.text
    report=client.get('/painel/vendas-manuais/relatorios')
    assert report.status_code==200
    assert 'ficam registrados com origem WhatsApp' in report.text
    assert 'O faturamento considera apenas pedidos finalizados' in report.text
    assert 'registre a venda manualmente' not in report.text
