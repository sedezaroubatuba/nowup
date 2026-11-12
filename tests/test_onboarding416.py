import pytest,json
from test_merchant228 import env
from test_checkout411 import checkout

def test_practice_requires_prerequisites_and_never_publishes_products(checkout):
    m,client,pid,_,_=checkout
    def save(task,**data):return client.post('/painel/primeiros-passos/exercicio/'+task,json=data)
    with m.db() as c:before=c.execute('SELECT COUNT(*) FROM products WHERE professional_id=?',(pid,)).fetchone()[0]
    assert client.get('/painel/primeiros-passos').status_code==200
    assert save('combo',name='Combo',price='40',items=[{'id':'burger','quantity':2}]).status_code==409
    assert save('category',name='Categoria teste').status_code==200
    bases=dict(name='Bases teste',ingredients='Pão, carne, queijo',accompaniment='Batata',extra='Bacon',extra_price='')
    assert save('bases',**bases).status_code==400
    bases['extra_price']='0'
    assert save('bases',**bases).status_code==400
    bases['extra_price']='3,00'
    assert save('bases',**bases).status_code==200
    assert save('normal',name='Produto teste',price='5').status_code==200
    assert save('meal',name='Lanche teste',price='20',ingredients='Pão, carne',removable='Tomate',max_extras=2,extra='Bacon',extra_price='3').status_code==200
    assert save('weight',name='Queijo teste',price='40',grams=250).json()['practice']['weight']['estimate_cents']==1000
    assert save('combo',name='Whisky com gelo',price='80',items=[{'id':'whisky','quantity':1},{'id':'ice','quantity':4}]).status_code==200
    assert save('layout',layout='pair').status_code==200
    with m.db() as c:
        assert c.execute('SELECT COUNT(*) FROM products WHERE professional_id=?',(pid,)).fetchone()[0]==before
        assert c.execute('SELECT carousel_layout235 FROM professionals WHERE id=?',(pid,)).fetchone()[0]=='pair'
    assert client.post('/painel/primeiros-passos/preferencia',data={'hidden':'1'}).status_code==400
    with m.db() as c:
        c.execute("UPDATE professionals SET display_name='Treino',whatsapp='12999999999',description='Loja',services='Alimentos',city='Ubatuba',neighborhood='Centro',avatar_filename='logo.jpg',cover_filename='capa.jpg',service_area='Centro',opening_hours='9h às 18h' WHERE id=?",(pid,))
        c.execute("INSERT INTO store_banners207(professional_id,title,image,mode,product_ids,active) VALUES(?,'Slide oficial','/uploads/slide.jpg','none','[]',1)",(pid,))
    state=client.get('/painel/primeiros-passos/estado').json()
    assert state['percent']==100 and state['profile_percent']==100 and state['complete']
    assert client.post('/painel/primeiros-passos/preferencia',data={'hidden':'1'},follow_redirects=False).status_code==303
    assert client.get('/painel/primeiros-passos/estado').json()['hidden']
    assert client.post('/painel/primeiros-passos/preferencia',data={'hidden':'0'},follow_redirects=False).status_code==303
    assert not client.get('/painel/primeiros-passos/estado').json()['hidden']
    client.post('/painel/primeiros-passos/apagar-testes',follow_redirects=False)
    state=client.get('/painel/primeiros-passos/estado').json()
    assert state['complete'] and state['practice']=={}
    with m.db() as c:assert c.execute('SELECT cover_filename FROM professionals WHERE id=?',(pid,)).fetchone()[0]=='capa.jpg'

def test_invalid_inputs_and_store_isolation(checkout):
    m,client,pid,_,foreign=checkout
    assert client.post('/painel/primeiros-passos/exercicio/unknown',json={}).status_code==400
    assert client.post('/painel/primeiros-passos/exercicio/category',json={'name':''}).status_code==400
    assert client.post('/painel/primeiros-passos/exercicio/category',json={'name':'Teste'},headers={'Origin':'https://foreign.test'}).status_code==403
    client.post('/painel/primeiros-passos/exercicio/category',json={'name':'Minha categoria'})
    with m.db() as c:
        other=c.execute('SELECT professional_id FROM products WHERE id=?',(foreign,)).fetchone()[0]
        assert not c.execute('SELECT 1 FROM onboarding416 WHERE professional_id=?',(other,)).fetchone()


def test_new_stores_start_guided_and_existing_store_is_not_forced(checkout):
    m,client,pid,_,_=checkout
    with m.db() as c:
        c.execute('DELETE FROM onboarding416 WHERE professional_id=?',(pid,))
        c.execute("UPDATE professionals SET created_at='2000-01-01T00:00:00+00:00' WHERE id=?",(pid,))
    assert not client.get('/painel/primeiros-passos/estado').json()['required']
    with m.db() as c:c.execute("UPDATE professionals SET plan_active='cardapio',business_type='general',created_at='2090-01-01T00:00:00+00:00' WHERE id=?",(pid,))
    assert client.get('/painel/primeiros-passos/estado').json()['required']
