import copy
import json
import pytest
from fastapi import HTTPException
from test_checkout247 import checkout
from nowup_custom192 import parse_config
from nowup_combos303 import attach_prices
from nowup_combo_pack305 import read_pack
from nowup_storeapp257 import validate

@pytest.fixture
def combo(checkout):
    m,client,url,data,combo_id,customer=checkout
    with m.db() as c:
        store=dict(c.execute('SELECT p.* FROM professionals p JOIN products pr ON pr.professional_id=p.id WHERE pr.id=?',(combo_id,)).fetchone())
        m.nowup_ingredients320.initialize(c)
        config=parse_config({'is_meal317':True,'ingredients':[{'name':'Pão','removable':False},{'name':'Tomate','removable':True},{'name':'Cebola','removable':True}]})
        child=c.execute("INSERT INTO products(professional_id,name,category,price_cents,extras_mode,customization192,available,created_at,updated_at) VALUES(?,'X-frango','Lanches',2000,'selected',?,1,'2026-11-05','2026-11-05')",(store['id'],json.dumps(config))).lastrowid
        group=c.execute("INSERT INTO product_option_groups(product_id,name,min_choices,max_choices) VALUES(?,'Adicionais',0,2)",(child,)).lastrowid
        option=c.execute("INSERT INTO product_options(product_id,name,price_cents,available,group_id) VALUES(?,'Bacon extra',350,1,?)",(child,group)).lastrowid
        fries=c.execute("INSERT INTO products(professional_id,name,price_cents,extras_mode,available,created_at,updated_at) VALUES(?,'Batata',1000,'none',1,'2026-11-05','2026-11-05')",(store['id'],)).lastrowid
        parent=parse_config({'combo_items':[{'product_id':child,'name':'X-frango','quantity':2},{'product_id':fries,'name':'Batata','quantity':1}]})
        c.execute('UPDATE products SET name=?,price_cents=4500,is_combo256=1,customization192=? WHERE id=?',('2 X-frango + fritas',json.dumps(parent),combo_id));c.commit()
    units=[{'key':'i0u0','product_id':child,'customization':{'removed':['Tomate']},'options':[{'id':option,'quantity':1}]},{'key':'i0u1','product_id':child,'customization':{'removed':['Cebola']},'options':[]}]
    raw={'id':combo_id,'quantity':1,'customization':{'units364':units}}
    return m,client,url,data,store,child,fries,option,raw


def check(combo,raw):
    m,_,_,_,store,*_=combo
    with m.db() as c:return validate(vars(m),c,store,json.dumps(raw),'pickup','pix','','','')


def test_metadata_order_totals_per_unit_and_persistent_kitchen_snapshot(combo):
    m,client,url,data,store,child,fries,option,raw=combo
    with m.db() as c:
        parent=dict(c.execute('SELECT * FROM products WHERE id=?',(raw['id'],)).fetchone())
        metadata=attach_prices(c,store['id'],[parent])[0]['combo_children364']
        assert metadata[str(child)]['config']['ingredients'][0]['removable'] is False
        assert metadata[str(child)]['options'][0]['id']==option
    second=copy.deepcopy(raw);second['customization']['units364'][0]['customization']['removed']=[];second['customization']['units364'][0]['options']=[]
    clean,subtotal,*_=check(combo,[raw,second]);assert subtotal==9350
    pack=read_pack(clean[0][0]['combo_pack305']);assert len(pack['units364'])==2
    assert pack['units364'][0]['notes']=='Retirar: Tomate' and pack['units364'][1]['notes']=='Retirar: Cebola'
    assert clean[0][4]==4850 and clean[1][4]==4500
    data['cart_json']=json.dumps([raw,second])
    result=client.post(url,data=data,follow_redirects=False);assert result.status_code==303,result.text
    with m.db() as c:
        order=c.execute('SELECT total_cents FROM orders ORDER BY id DESC LIMIT 1').fetchone();assert order[0]==9350
        lines=c.execute('SELECT notes,combo_pack305 FROM order_items ORDER BY id').fetchall();assert len(lines)==2
        assert 'X-frango 1: Retirar: Tomate' in lines[0]['notes']
        assert read_pack(lines[0]['combo_pack305'])['units364'][1]['position']==2
        assert c.execute('SELECT option_name,price_cents FROM order_item_options').fetchone()[0]=='X-frango 1: Bacon extra'
    page=client.get(result.headers['location']);assert page.status_code==200
    assert 'X-frango 1' in page.text and 'X-frango 2' in page.text


@pytest.mark.parametrize('case',['mandatory','wrong_product','duplicate_key','extra_unit','foreign_extra','unavailable','hidden_category','not_combo'])
def test_rejects_tampered_or_stale_units(combo,case):
    m,_,_,_,store,child,fries,option,raw=combo
    first=raw['customization']['units364'][0]
    if case=='mandatory':first['customization']['removed']=['Pão']
    elif case=='wrong_product':first['product_id']=fries
    elif case=='duplicate_key':raw['customization']['units364'].append(copy.deepcopy(first))
    elif case=='extra_unit':first['key']='i0u2'
    elif case=='foreign_extra':first['options']=[{'id':999999}]
    elif case=='unavailable':
        with m.db() as c:c.execute('UPDATE products SET available=0 WHERE id=?',(child,))
    elif case=='hidden_category':
        with m.db() as c:c.execute("INSERT INTO product_categories(professional_id,name,active,created_at) VALUES(?,'Lanches',0,'2026-11-05')",(store['id'],))
    else:
        with m.db() as c:c.execute('UPDATE products SET is_combo256=0 WHERE id=?',(raw['id'],))
    with pytest.raises(HTTPException):check(combo,[raw])


def test_required_child_choice_and_current_extra_price(combo):
    m,_,_,_,store,child,_,option,raw=combo
    with m.db() as c:
        config=parse_config({'groups':[{'id':'ponto','name':'Ponto','min':1,'max':1,'options':['Bem passado','Ao ponto']}]})
        c.execute('UPDATE products SET customization192=? WHERE id=?',(json.dumps(config),child))
    for unit in raw['customization']['units364']:unit['customization']={}
    with pytest.raises(HTTPException):check(combo,[raw])
    for unit in raw['customization']['units364']:unit['customization']={'groups':{'ponto':['Ao ponto']}}
    with m.db() as c:c.execute('UPDATE product_options SET price_cents=550 WHERE id=?',(option,))
    assert check(combo,[raw])[1]==5050


def test_whatsapp_lists_each_unit_and_charges_extra_once(combo,monkeypatch):
    m,client,_,data,store,_,_,_,raw=combo
    with m.db() as c:
        c.execute("UPDATE professionals SET plan_active='completo',whatsapp='12999999999' WHERE id=?",(store['id'],))
        customer=dict(c.execute("SELECT * FROM users WHERE email='audit247@example.invalid'").fetchone())
    customer.update(name='Teste combo',phone='12988887777')
    monkeypatch.setattr(m,'current_user',lambda request:customer)
    data['cart_json']=json.dumps([raw])
    response=client.post('/p/'+store['slug']+'/menu/whatsapp',data=data)
    assert response.status_code==200,response.text
    result=response.json()
    assert result['total_cents']==4850
    assert result['merchant_url'] in result['message']
    with m.db() as c:
        saved=c.execute('SELECT notes FROM order_items').fetchone()[0]
        assert 'X-frango 1: Retirar: Tomate' in saved
        assert 'X-frango 2: Retirar: Cebola' in saved
    page=client.get(result['redirect']);assert page.status_code==200
    assert 'Tomate' in page.text and 'Cebola' in page.text and 'Bacon extra' in page.text


def test_meal_combo_uses_item_refs_and_keeps_outer_drinks_in_one_place(combo):
    m,client,url,data,store,child,fries,option,raw=combo
    with m.db() as c:
        parent=parse_config({'is_meal317':True,'meal_groups324':True,'meal_combo324':True,'ingredients':[{'name':'Molho da casa','removable':True}],'groups':[{'id':'lanches','name':'Lanches','min':2,'max':2,'quantity_mode':True,'options':['X-frango'],'item_refs325':[{'kind':'product','id':child}]},{'id':'batata','name':'Fritas','min':1,'max':1,'quantity_mode':True,'options':['Batata'],'item_refs325':[{'kind':'item','id':29}]}]})
        c.execute('UPDATE products SET is_combo256=0,customization192=? WHERE id=?',(json.dumps(parent),raw['id']))
        config=json.loads(c.execute('SELECT customization192 FROM products WHERE id=?',(child,)).fetchone()[0])
        config.update(meal_combo324=True,meal_groups324=True,groups=[{'id':'bebida','name':'Bebida avulsa','min':1,'max':1,'options':['Coca','Guaraná']}])
        c.execute('UPDATE products SET customization192=? WHERE id=?',(json.dumps(config),child))
        metadata=attach_prices(c,store['id'],[dict(c.execute('SELECT * FROM products WHERE id=?',(raw['id'],)).fetchone())])[0]['combo_children364']
        assert metadata[str(child)]['config']['groups']==[]
        assert len(metadata[str(child)]['config']['ingredients'])==3
    raw['customization']['removed']=['Molho da casa']
    raw['customization']['groups']={'lanches':['X-frango','X-frango'],'batata':['Batata']}
    for index,unit in enumerate(raw['customization']['units364']):unit['key']='g0u'+str(index)
    clean,subtotal,*_=check(combo,[raw]);assert subtotal==4850
    assert len(read_pack(clean[0][0]['combo_pack305'])['units364'])==2
    assert 'Retirar: Molho da casa' in read_pack(clean[0][0]['combo_pack305'])['details365']
    data['cart_json']=json.dumps([raw]);result=client.post(url,data=data,follow_redirects=False);assert result.status_code==303,result.text
