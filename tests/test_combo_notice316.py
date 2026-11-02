import pytest
from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader
from nowup_custom192 import parse_config
from nowup_combo_pack305 import build_pack, read_pack


def test_notice_round_trip_and_immutable_order_snapshot():
    config=parse_config({'combo_items':[{'name':'Energético','quantity':1,'product_id':1}],'combo_notice316':'  Na falta do sabor, combinaremos a troca.  '})
    saved=build_pack(config,{'groups':{}})
    config['combo_notice316']='Texto alterado depois da compra'
    pack=read_pack(saved)
    assert pack['notice316']=='Na falta do sabor, combinaremos a troca.'
    assert parse_config({}).get('combo_notice316','')==''


@pytest.mark.parametrize('notice',[None,False,42,'a'*601])
def test_notice_validation(notice):
    with pytest.raises(HTTPException):parse_config({'combo_notice316':notice})


def test_notice_is_escaped_in_order_and_old_orders_remain_valid():
    config=parse_config({'combo_items':[{'name':'Gelo','quantity':1}],'combo_notice316':'<script>alert(1)</script>\nCombine a troca.'})
    saved=build_pack(config,{'groups':{}})
    env=Environment(loader=FileSystemLoader('templates'),autoescape=True);env.filters['combo_pack305']=read_pack
    html=env.get_template('combo_pack305.html').module.picking({'quantity':1,'combo_pack305':saved})
    assert '&lt;script&gt;' in html and '<script>' not in html
    pack=read_pack(saved);del pack['notice316'];assert read_pack(pack)
