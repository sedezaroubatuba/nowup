from datetime import date
import pytest
from fastapi import HTTPException
from nowup_period414 import selected_period
from test_merchant228 import env
from test_checkout411 import checkout

def test_calendar_periods_and_invalid_values():
    assert selected_period({'periodo':'dia','dia':'2026-11-11'})==(date(2026,11,11),)*2
    assert selected_period({'periodo':'mes','mes':'2024-02'})==(date(2024,2,1),date(2024,2,29))
    assert selected_period({'periodo':'ano','ano':'2024'})==(date(2024,1,1),date(2024,12,31))
    for params in [{'periodo':'dia','dia':'2026-02-30'},{'periodo':'ano','ano':'0'},{'periodo':'mes','mes':'2026-13'}]:
        with pytest.raises(HTTPException):selected_period(params)

def test_both_sales_reports_filter_closed_sales_in_local_calendar(checkout):
    m,client,pid,_,_=checkout
    with m.db() as c:
        for stamp,cents in [('2024-02-01T02:59:00+00:00',1100),('2024-02-01T03:00:00+00:00',2200),('2024-03-01T02:59:00+00:00',3300),('2024-03-01T03:00:00+00:00',4400),('2025-01-01T03:00:00+00:00',5500)]:
            c.execute("INSERT INTO orders(professional_id,customer_name,status,total_cents,created_at,updated_at,fulfillment_type,order_origin,payment_method) VALUES(?,'Period414','completed',?,?,?,'pickup','external','pix')",(pid,cents,stamp,stamp))
        report=m.checkout_report411(c,pid,date(2024,2,1),date(2024,2,29))
        assert report['total']==5500
    for base in ['/painel/vendas-manuais/relatorios?','/painel/checkout?tab=summary&']:
        for params,label in [('periodo=dia&dia=2024-02-01','22,00'),('periodo=mes&mes=2024-02','55,00'),('periodo=ano&ano=2024','110,00')]:
            r=client.get(base+params)
            assert r.status_code==200
            assert 'R$ '+label in r.text
            assert all(x in r.text for x in ['Ver dia','Ver mês','Ver ano'])
