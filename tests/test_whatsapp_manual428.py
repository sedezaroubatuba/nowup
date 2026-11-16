import json
from urllib.parse import parse_qs, urlsplit
from test_checkout247 import checkout
from test_storeapp256 import shop
from test_storeapp257 import channel


def test_manual_handoff_contains_full_order_and_no_customer_payment_link(channel):
    from datetime import datetime,timedelta,timezone
    m,client,slug,pid,data,product,customer=channel
    data.update(notes='Entregar na portaria',payment_method='pix')
    result=client.post('/p/'+slug+'/menu/whatsapp',data=data).json()
    assert result['recorded'] and result['internal_checkout432'] and not result['whatsapp_only']
    assert 'pix' not in result and 'pix' not in result['receipt']
    with m.db() as conn:
        conn.execute('UPDATE orders SET created_at=?',((datetime.now(timezone.utc)-timedelta(seconds=61)).isoformat(),))
    handoff=client.post(result['redirect']+'/espera434').json()
    message=parse_qs(urlsplit(handoff['whatsapp_url']).query)['text'][0]
    assert 'Auditoria' in message and 'R$ 3,00' in message
    assert 'Maria da conta' in message and 'Entregar na portaria' in message
    assert 'Aceite e pagamento bloqueados no NowUp' in message
    assert 'data-pix-payment' not in client.get(result['redirect']).text
    with m.db() as conn:
        assert conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==1
        assert conn.execute('SELECT status,order_origin FROM orders').fetchone()[:]==('whatsapp_finalized','external')


def test_cash_handoff_includes_change_and_keeps_server_prices(channel):
    m, client, slug, pid, data, product, customer = channel
    data.update(payment_method='cash', change_for='20,00', cart_json=json.dumps([{'id':product,'quantity':2}]))
    response = client.post('/p/'+slug+'/menu/whatsapp', data=data)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['total_cents'] == 600
    assert 'Troco para: R$ 20,00' in result['message']
    assert 'Troco: R$ 14,00' in result['message']
    assert '2x Auditoria' in result['message']
    assert 'pix' not in result
