import json
from pathlib import Path
import pytest
from fastapi import HTTPException
from test_merchant228 import env
from nowup_custom192 import parse_config
from nowup_combo_pack305 import build_pack,read_pack
from nowup_combo_units364 import slots
from nowup_storeapp257 import validate


def test_each_meal_has_independent_additional_limit_and_none_blocks_checkout(env):
    m,client,_,pid,_=env
    with m.db() as c:
        ids=[c.execute("INSERT INTO shared_extras155(professional_id,name,price_cents,available) VALUES(?,?,200,1)",(pid,'Extra410 '+str(i))).lastrowid for i in range(4)]
    created=[]
    for maximum,mode in [(2,'selected'),(3,'selected'),(3,'none')]:
        name='Lanche410 '+str(len(created))
        data={'name':name,'category':'Lanches','price':'25,00','available':'1','extras_mode':mode,'extra_ids':[str(i) for i in ids] if mode!='none' else [],'max_choices':str(maximum),'is_combo256':'0','customization192':json.dumps({'is_meal317':True,'notes':True})}
        response=client.post('/painel/cardapio/produtos',data=data,follow_redirects=False)
        assert response.status_code==303
        with m.db() as c:created.append(c.execute('SELECT id FROM products WHERE professional_id=? AND name=?',(pid,name)).fetchone()[0])
    with m.db() as c:
        choices=[]
        for product in created[:2]:choices.append([{'id':r[0]} for r in c.execute('SELECT id FROM product_options WHERE product_id=? AND available=1',(product,))])
        assert len(m.options_single158(c,created[0],choices[0][:2])[0])==2
        with pytest.raises(HTTPException):m.options_single158(c,created[0],choices[0][:3])
        assert len(m.options_single158(c,created[1],choices[1][:3])[0])==3
        with pytest.raises(HTTPException):m.options_single158(c,created[1],choices[1][:4])
        assert m.options_single158(c,created[2],[])[1]==0
        with pytest.raises(HTTPException):m.options_single158(c,created[2],choices[0][:1])


@pytest.mark.parametrize('quantities',[[5],[1,1,1]])
def test_fixed_combo_components_are_automatic_in_checkout_and_receipt(env,quantities):
    m,client,_,pid,_=env
    with m.db() as c:
        items=[]
        for index,quantity in enumerate(quantities):
            name=['Cachorro-quente410','X-frango410','Batata410'][index]
            product=c.execute("INSERT INTO products(professional_id,name,price_cents,extras_mode,available,created_at,updated_at) VALUES(?,?,1200,'none',1,?,?)",(pid,name,m.now_iso(),m.now_iso())).lastrowid
            items.append({'product_id':product,'name':name,'quantity':quantity,'principal':True})
        config=parse_config({'combo_items':items,'notes':True})
        combo=c.execute("INSERT INTO products(professional_id,name,category,price_cents,is_combo256,extras_mode,available,customization192,created_at,updated_at) VALUES(?,'Combo410','Combos',3900,1,'none',1,?,?,?)",(pid,json.dumps(config),m.now_iso(),m.now_iso())).lastrowid
        store=dict(c.execute('SELECT * FROM professionals WHERE id=?',(pid,)).fetchone());store['allows_pickup']=1;store['minimum_order_cents']=0
        rows,total,*_=validate(vars(m),c,store,json.dumps([{'id':combo,'quantity':1,'customization':{}}]),'pickup','pix','','','')
        assert total==3900
        packed=read_pack(rows[0][0]['combo_pack305'])
        assert [(i['product_id'],i['quantity'],i['role']) for i in packed['items']]==[(i['product_id'],i['quantity'],'principal') for i in items]
        assert len(slots(config,{}))==sum(quantities)


def test_panel_preserves_all_four_editors_and_loads_redesign(env):
    m,client,*_=env
    response=client.get('/painel');assert response.status_code==200
    for marker in ['product-editor410.js','product-editor410.css','id="novo-produto"','id="produtos-peso370"','id="cadastrar-combo"','id="novo-lanche322"','name="recommend256"','data-meal-editor322']:
        assert marker in response.text
    Path('/tmp/nowup-panel410.html').write_text(response.text)
