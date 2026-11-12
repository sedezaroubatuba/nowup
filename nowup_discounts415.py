"""Merchant checkout discounts, in integer cents and hundredths of a percent."""
from decimal import Decimal,InvalidOperation
from fastapi import HTTPException

def parse(kind,raw):
    if kind not in ('fixed','percent'):raise HTTPException(400,'Escolha desconto em reais ou porcentagem.')
    try:
        value=Decimal(str(raw).strip().replace(',','.'))
        if not value.is_finite() or value<0 or value.as_tuple().exponent < -2:raise ValueError()
        if value>(100 if kind=='percent' else 1000000):raise ValueError()
        return int(value*100)
    except (ValueError,InvalidOperation):raise HTTPException(400,'Informe um desconto válido, com até duas casas decimais; porcentagem de 0 a 100%.')

def amounts(c,sid):
    subtotal=c.execute('SELECT COALESCE(SUM(quantity*unit_price_cents),0) FROM manual_items107 WHERE sale_id=?',(sid,)).fetchone()[0]
    row=c.execute('SELECT discount_kind415,discount_value415 FROM manual_sales107 WHERE id=?',(sid,)).fetchone()
    kind,value=row['discount_kind415'],row['discount_value415']
    discount=(subtotal*value+5000)//10000 if kind=='percent' else value
    if discount>subtotal:raise HTTPException(400,'O desconto não pode superar o valor dos produtos. Ajuste ou remova o desconto primeiro.')
    return dict(subtotal_cents=subtotal,discount_cents=discount,discount_kind415=kind,discount_value415=value)
