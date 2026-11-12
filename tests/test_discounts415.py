import pytest
from test_merchant228 import env
from test_checkout411 import checkout,open_sale,change,get

def test_discount_modes_recalculate_receipt_and_protect_payments(checkout):
    m,client,pid,product,_=checkout
    sid=open_sale(client)
    assert change(client,sid,'item',product_id=product,quantity=4).status_code==200
    assert change(client,sid,'discount',discount_kind='percent',discount_value='12,50').status_code==200
    state=get(client,sid)
    assert (state['subtotal_cents'],state['discount_cents'],state['remaining'])==(2000,250,1750)
    assert change(client,sid,'item',product_id=product,quantity=2).status_code==200
    assert get(client,sid)['total_cents']==2625
    assert change(client,sid,'discount',discount_kind='fixed',discount_value='5,00').status_code==200
    assert get(client,sid)['total_cents']==2500
    for kind,value in [('percent','100.01'),('percent','NaN'),('fixed','-1'),('fixed','31'),('fixed','1.001'),('fake','1')]:
        assert change(client,sid,'discount',discount_kind=kind,discount_value=value).status_code==400
        assert get(client,sid)['total_cents']==2500
    assert change(client,sid,'payment',method='pix',amount='24,00').status_code==200
    assert change(client,sid,'discount',discount_kind='fixed',discount_value='7,00').status_code==400
    assert get(client,sid)['remaining']==100
    receipt=client.get(f'/painel/checkout/vendas/{sid}/imprimir')
    assert 'Subtotal: R$ 30,00' in receipt.text and '− R$ 5,00' in receipt.text and 'Total: R$ 25,00' in receipt.text
    assert change(client,sid,'payment',method='cash',amount='1,00').status_code==200
    assert change(client,sid,'close').status_code==200
    assert change(client,sid,'discount',discount_kind='fixed',discount_value='0').status_code==409
    with m.db() as c:
        assert c.execute('SELECT total_cents FROM manual_sales107 WHERE id=?',(sid,)).fetchone()[0]==2500
        assert c.execute("SELECT COUNT(*) FROM manual_history107 WHERE sale_id=? AND action='discount'",(sid,)).fetchone()[0]==2

def test_clear_discount_and_free_sale_and_cent_rounding(checkout):
    m,client,pid,product,_=checkout
    sid=open_sale(client)
    assert change(client,sid,'close').status_code==400
    with m.db() as c:c.execute('UPDATE products SET price_cents=501,promo_price_cents=0 WHERE id=?',(product,))
    change(client,sid,'item',product_id=product)
    change(client,sid,'discount',discount_kind='percent',discount_value='50')
    assert get(client,sid)['discount_cents']==251
    change(client,sid,'discount',discount_kind='fixed',discount_value='0')
    assert get(client,sid)['total_cents']==501
    change(client,sid,'discount',discount_kind='percent',discount_value='100')
    assert get(client,sid)['remaining']==0
    assert change(client,sid,'close').status_code==200
