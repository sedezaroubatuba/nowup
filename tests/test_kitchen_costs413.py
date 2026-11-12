import json,secrets
import pytest
from test_merchant228 import env
from test_checkout411 import checkout,open_sale,get,change


def test_customer_name_and_per_unit_kitchen_details_and_prices(checkout):
    m,client,pid,_,_=checkout
    cfg={'is_meal317':True,'ingredients':[{'name':'Pão','removable':False},{'name':'Tomate','removable':True}],'notes':True,'utensils':False}
    with m.db() as c:
        meal=c.execute("INSERT INTO products(professional_id,name,category,price_cents,extras_mode,customization192,available,created_at,updated_at) VALUES(?,'X-bacon413','Lanches',2500,'selected',?,1,?,?)",(pid,json.dumps(cfg),m.now_iso(),m.now_iso())).lastrowid
        group=c.execute("INSERT INTO product_option_groups(product_id,name,min_choices,max_choices) VALUES(?,'Adicionais',0,2)",(meal,)).lastrowid
        extra=c.execute("INSERT INTO product_options(product_id,name,price_cents,available,group_id) VALUES(?,'Queijo extra',300,1,?)",(meal,group)).lastrowid
        combo=c.execute("INSERT INTO products(professional_id,name,category,price_cents,is_combo256,extras_mode,customization192,available,created_at,updated_at) VALUES(?,'Combo 2 lanches413','Combos',4500,1,'none',?,1,?,?)",(pid,json.dumps({'combo_items':[{'name':'X-bacon413','product_id':meal,'quantity':2,'principal':True}],'notes':True,'utensils':False}),m.now_iso(),m.now_iso())).lastrowid
    sid=open_sale(client)
    selections=[{'customization':{'removed':['Tomate']},'options':[{'id':extra,'price':0}],'notes':'Bem passado'}]
    assert change(client,sid,'item',product_id=meal,quantity=1,selections_json=json.dumps(selections)).status_code==400
    assert change(client,sid,'customer',customer_name='Samuel').status_code==200
    assert change(client,sid,'item',product_id=meal,quantity=1,selections_json=json.dumps(selections)).status_code==200
    assert get(client,sid)['total_cents']==2800
    bad_batch=selections+[{'customization':{'removed':['Pão']}}]
    assert change(client,sid,'item',product_id=meal,quantity=2,selections_json=json.dumps(bad_batch)).status_code==400
    assert get(client,sid)['total_cents']==2800
    invalid=[{'customization':{'removed':['Pão']}}]
    assert change(client,sid,'item',product_id=meal,quantity=1,selections_json=json.dumps(invalid)).status_code==400
    units=[{'key':'i0u0','product_id':meal,'customization':{'removed':['Tomate']},'options':[{'id':extra}]},{'key':'i0u1','product_id':meal,'customization':{},'options':[]}]
    choices=[{'customization':{'units364':units},'notes':'Caprichar'}]
    assert change(client,sid,'item',product_id=combo,quantity=1,selections_json=json.dumps(choices)).status_code==200
    assert get(client,sid)['total_cents']==7600
    receipt=client.get(f'/painel/checkout/vendas/{sid}/imprimir?cozinha=1')
    assert receipt.status_code==200
    for text in ['Samuel','COMANDA DA COZINHA','Retirar: Tomate','Queijo extra','X-bacon413 1','X-bacon413 2','Composição: Pão','Bem passado']:assert text in receipt.text
    # Changing the catalogue after launch cannot rewrite kitchen instructions.
    with m.db() as c:c.execute("UPDATE products SET customization192='',name='Alterado depois' WHERE id=?",(meal,))
    assert 'Retirar: Tomate' in client.get(f'/painel/checkout/vendas/{sid}/imprimir?cozinha=1').text
    assert client.get('/painel/checkout/produtos/'+str(combo)+'/opcoes').status_code==200
    item_id=get(client,sid)['items'][0]['id']
    assert change(client,sid,'remove_item',item_id=item_id).status_code==200
    with m.db() as c:assert c.execute('SELECT COUNT(*) FROM checkout_item_details413 WHERE item_id=?',(item_id,)).fetchone()[0]==0


def test_optional_costs_allow_explicit_half_price_estimate(checkout):
    m,client,pid,_,foreign=checkout
    from nowup_costs413 import status,effective_cost
    with m.db() as c:
        assert not status(c,pid)['enabled']
        ids=[r[0] for r in c.execute('SELECT id FROM products WHERE professional_id=?',(pid,))]
    r=client.post('/painel/custos/ativar',follow_redirects=False)
    assert 'ok=ativo' in r.headers['location']
    with m.db() as c:
        assert effective_cost(c,pid,ids[0])['estimated']
        assert effective_cost(c,pid,ids[0])['cents'] is not None
    assert client.post('/painel/custos/salvar',data={'cost_'+str(foreign):'1,00'},follow_redirects=False).status_code==404
    assert client.post('/painel/custos/salvar',data={'cost_'+str(ids[0]):'-1'},follow_redirects=False).status_code==400
    assert client.post('/painel/custos/salvar',data={'cost_'+str(i):'1,00' for i in ids},follow_redirects=False).status_code==303
    assert 'ok=ativo' in client.post('/painel/custos/ativar',follow_redirects=False).headers['location']
    data={'name':'Custo completo413','price':'10,00','category':'Geral','extras_mode':'none','available':'1'}
    assert client.post('/painel/cardapio/produtos',data=data,follow_redirects=False).status_code==303
    with m.db() as c:
        created=c.execute('SELECT id FROM products WHERE professional_id=? AND name=?',(pid,data['name'])).fetchone()[0]
        assert effective_cost(c,pid,created)=={'cents':500,'estimated':True}
        c.execute('DELETE FROM products WHERE id=?',(created,))
    data['cost_price413']='4,00'
    assert client.post('/painel/cardapio/produtos',data=data,follow_redirects=False).status_code==303
    with m.db() as c:
        assert status(c,pid)['complete']
        row=c.execute('SELECT pr.price_cents,pc.cost_cents FROM products pr JOIN product_costs413 pc ON pc.product_id=pr.id WHERE pr.professional_id=? AND pr.name=?',(pid,data['name'])).fetchone()
        assert tuple(row)==(1000,400)
    assert client.post('/painel/pratos/publicacao',data={'publish':'1'},follow_redirects=False).status_code==303
    dish={'name':'Prato legado413','price':'15,00'}
    assert client.post('/painel/pratos',data=dish,follow_redirects=False).status_code==303
    with m.db() as c:c.execute('DELETE FROM products WHERE professional_id=? AND name=?',(pid,dish['name']))
    dish['cost_price413']='6,00'
    assert client.post('/painel/pratos',data=dish,follow_redirects=False).status_code==303
    with m.db() as c:assert status(c,pid)['complete']
    assert client.get('/painel/custos').status_code==200
    assert client.post('/painel/custos/salvar',data={'cost_'+str(ids[0]):''},follow_redirects=False).status_code==303
    with m.db() as c:
        assert effective_cost(c,pid,ids[0])['estimated']
        c.execute('UPDATE products SET price_cents=1001,promo_price_cents=0 WHERE id=?',(ids[0],))
        assert effective_cost(c,pid,ids[0])=={'cents':501,'estimated':True}
    assert client.post('/painel/custos/salvar',data={'cost_'+str(ids[0]):'0,00'},follow_redirects=False).status_code==303
    with m.db() as c:assert effective_cost(c,pid,ids[0])=={'cents':0,'estimated':False}
    client.post('/painel/custos/desativar',follow_redirects=False)
    data.pop('cost_price413');data['name']='Sem custo413'
    assert client.post('/painel/cardapio/produtos',data=data,follow_redirects=False).status_code==303
    with m.db() as c:
        assert not status(c,pid)['enabled']
        assert effective_cost(c,pid,ids[0])=={'cents':None,'estimated':False}
