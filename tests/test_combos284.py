import json
import pytest
from fastapi import HTTPException
from test_merchant228 import env
from nowup_custom192 import parse_config, validate_customization


def test_combo_items_validation_and_required_choices():
    config=parse_config({'combo_items':[{'name':'Energético','quantity':4}], 'groups':[{'id':'drink','name':'Energético','min':1,'max':1,'options':['Tradicional','Sem açúcar']}]})
    assert config['combo_items']==[{'name':'Energético','quantity':4}]
    assert 'Sem açúcar' in validate_customization(config,{'groups':{'drink':['Sem açúcar']}},'',False)
    with pytest.raises(HTTPException):validate_customization(config,{'groups':{}},'',False)
    for quantity in [0,100,True,'4']:
        with pytest.raises(HTTPException):parse_config({'combo_items':[{'name':'Energético','quantity':quantity}]})


def test_combo_creation_edit_and_render(env):
    m,client,_,pid,_=env
    config={'combo_items':[{'name':'Jack Apple 1L','quantity':1},{'name':'Red Bull','quantity':4}], 'groups':[{'id':'drink','name':'Escolha o energético','min':1,'max':1,'options':['Tradicional','Sem açúcar']}], 'utensils':False,'notes':True}
    form={'name':'Combo personalizável 284','category':'__combos256','description':'Whisky e 4 energéticos.','price':'259,90','available':'1','extras_mode':'none','customization192':json.dumps(config)}
    assert client.post('/painel/cardapio/produtos',data=form,follow_redirects=False).status_code==303
    with m.db() as c:
        row=c.execute('SELECT * FROM products WHERE professional_id=? AND name=?',(pid,form['name'])).fetchone()
        product_id=row['id'];assert row['is_dish']==1 and row['is_combo256']==1
        assert json.loads(row['customization192'])['combo_items']==config['combo_items']
        slug=c.execute('SELECT slug FROM professionals WHERE id=?',(pid,)).fetchone()['slug']
    config['combo_items'][1]['quantity']=3;form['customization192']=json.dumps(config)
    assert client.post(f'/painel/cardapio/produtos/{product_id}',data=form,follow_redirects=False).status_code==303
    with m.db() as c:
        row=c.execute('SELECT * FROM products WHERE id=?',(product_id,)).fetchone()
        assert json.loads(row['customization192'])['combo_items'][1]['quantity']==3
        assert row['is_dish']==1
    html=client.get('/p/'+slug+'/menu').text
    assert 'data-combo256="1"' in html and 'Escolha o energético' in html
    form['customization192']=json.dumps({'combo_items':[{'name':'Red Bull','quantity':0}]})
    assert client.post(f'/painel/cardapio/produtos/{product_id}',data=form,follow_redirects=False).status_code==400


def test_percent_promotion_saved_as_checkout_price(env):
    m,client,_,pid,_=env
    form={'name':'Oferta percentual 285','category':'Geral','price':'10,00','available':'1','promo_enabled':'1','promo_mode':'percent','promo_percent':'15'}
    assert client.post('/painel/cardapio/produtos',data=form,follow_redirects=False).status_code==303
    with m.db() as c:
        row=c.execute('SELECT * FROM products WHERE professional_id=? AND name=?',(pid,form['name'])).fetchone()
        assert row['price_cents']==1000 and row['promo_price_cents']==850
        product_id=row['id']
    for invalid in ['100','-15','NaN','Infinity','abc']:
        form['promo_percent']=invalid
        assert client.post(f'/painel/cardapio/produtos/{product_id}',data=form,follow_redirects=False).status_code==400
    form['promo_percent']='15';form.pop('promo_enabled')
    assert client.post(f'/painel/cardapio/produtos/{product_id}',data=form,follow_redirects=False).status_code==303
    with m.db() as c:assert c.execute('SELECT promo_price_cents FROM products WHERE id=?',(product_id,)).fetchone()[0]==0
    panel=client.get('/painel')
    assert 'Desconto em %' in panel.text and '/static/promotions285.js?v=285' in panel.text
