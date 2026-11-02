import sqlite3
import pytest
from fastapi import HTTPException
from nowup_ingredients320 import initialize, catalog, bind
from nowup_custom192 import parse_config, validate_customization

@pytest.fixture
def conn():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.execute('CREATE TABLE professionals(id INTEGER PRIMARY KEY)');initialize(c)
    c.executemany('INSERT INTO ingredients320(id,professional_id,name,image_filename) VALUES(?,?,?,?)',[(1,10,'Pão',''),(2,10,'Alface','lettuce.jpg'),(3,11,'Queijo','other.jpg')]);return c

def test_registry_optional_photos_and_mandatory_ingredients(conn):
    assert catalog(conn,10)[0]['name']=='Alface'
    c=parse_config({'is_meal317':True,'ingredients':[{'name':'Pão','removable':False,'ingredient_id320':1},{'name':'Alface','removable':True,'ingredient_id320':2}]})
    c=bind(conn,10,c)
    assert 'image_filename' not in c['ingredients'][0]
    assert c['ingredients'][1]['image_filename']=='lettuce.jpg'
    assert 'Retirar: Alface' in validate_customization(c,{'removed':['Alface']},'',False)
    with pytest.raises(HTTPException):validate_customization(c,{'removed':['Pão']},'',False)

def test_server_resolves_own_store_name_and_photo(conn):
    c=bind(conn,10,parse_config({'ingredients':[{'name':'Falso','ingredient_id320':2,'image_filename':'fake.jpg'}]}))
    assert c['ingredients'][0]['name']=='Alface' and c['ingredients'][0]['image_filename']=='lettuce.jpg'
    for ref in [3,999]:
        with pytest.raises(HTTPException):bind(conn,10,parse_config({'ingredients':[{'name':'Queijo','ingredient_id320':ref}]}))
    manual=bind(conn,10,parse_config({'ingredients':[{'name':'Tomate','image_filename':'untrusted.jpg'}]}))
    assert 'image_filename' not in manual['ingredients'][0]

from test_merchant228 import env

def test_authenticated_registry_create_optional_photo_and_store_scope(env):
    import io
    from PIL import Image
    m,client,_,store_id,other_store=env
    response=client.post('/painel/cardapio/ingredientes320',data={'name':'Arroz'},follow_redirects=False)
    assert response.status_code==303
    with m.db() as c:
        row=c.execute('SELECT * FROM ingredients320 WHERE professional_id=? AND name=?',(store_id,'Arroz')).fetchone()
        assert row['image_filename']==''
        c.execute('INSERT INTO ingredients320(professional_id,name,image_filename) VALUES(?,?,?)',(other_store,'Ingrediente privado',''))
        foreign=c.execute('SELECT id FROM ingredients320 WHERE professional_id=?',(other_store,)).fetchone()['id'];c.commit()
    png=io.BytesIO();Image.new('RGB',(24,24),'green').save(png,format='PNG')
    response=client.post('/painel/cardapio/ingredientes320',data={'name':'Alface'},files={'photo':('alface.png',png.getvalue(),'image/png')},follow_redirects=False)
    assert response.status_code==303
    with m.db() as c:
        photo=c.execute('SELECT * FROM ingredients320 WHERE professional_id=? AND name=?',(store_id,'Alface')).fetchone()
        assert photo['image_filename']
    assert client.post('/painel/cardapio/ingredientes320',data={'name':'Tentativa','ingredient_id':foreign},follow_redirects=False).status_code==404
    duplicate=client.post('/painel/cardapio/ingredientes320',data={'name':'Arroz'},follow_redirects=False)
    assert 'ingrediente-duplicado' in duplicate.headers['location']
    panel=client.get('/painel');assert panel.status_code==200 and 'Cadastrar ingredientes' in panel.text

def test_unified_item_price_and_included_use(env):
    m,client,_,store_id,other_store=env
    assert client.post('/painel/cardapio/ingredientes320',data={'name':'Bacon unificado','price':'5,00'},follow_redirects=False).status_code==303
    with m.db() as c:
        item=c.execute('SELECT * FROM ingredients320 WHERE professional_id=? AND name=?',(store_id,'Bacon unificado')).fetchone()
        extra=c.execute('SELECT * FROM shared_extras155 WHERE id=?',(item['extra_id325'],)).fetchone()
        assert item['price_cents']==extra['price_cents']==500
        assert bind(c,store_id,parse_config({'ingredients':[{'name':'Bacon unificado','ingredient_id320':item['id']}]}))['ingredients'][0]['name']=='Bacon unificado'
    response=client.post('/painel/cardapio/ingredientes320',data={'name':'Bacon unificado','ingredient_id':item['id'],'price':''},follow_redirects=False)
    assert response.status_code==303
    with m.db() as c:
        assert c.execute('SELECT price_cents FROM ingredients320 WHERE id=?',(item['id'],)).fetchone()[0] is None
        assert c.execute('SELECT available FROM shared_extras155 WHERE id=?',(extra['id'],)).fetchone()[0]==0
    assert client.post('/painel/cardapio/ingredientes320',data={'name':'Arroz simples'},follow_redirects=False).status_code==303
    with m.db() as c:
        assert c.execute('SELECT extra_id325 FROM ingredients320 WHERE professional_id=? AND name=?',(store_id,'Arroz simples')).fetchone()[0]==0

def test_existing_registries_merge_idempotently(conn):
    conn.execute('CREATE TABLE shared_extras155(id INTEGER PRIMARY KEY,professional_id,name,price_cents,available)')
    conn.execute('CREATE TABLE included_choices195(id INTEGER PRIMARY KEY,professional_id,kind,name,available)')
    conn.executemany('INSERT INTO shared_extras155 VALUES(?,?,?,?,?)',[(7,10,'Pão',200,1),(8,10,'Bacon',500,1)])
    conn.executemany('INSERT INTO included_choices195 VALUES(?,?,?,?,?)',[(9,10,'side','Bacon',1),(10,10,'side','Legumes',1)])
    initialize(conn);initialize(conn)
    rows=catalog(conn,10)
    assert len(rows)==4
    bread=next(r for r in rows if r['name']=='Pão')
    assert bread['extra_id325']==7 and bread['price_cents']==200
    assert next(r for r in rows if r['name']=='Bacon')['extra_id325']==8

def test_delete_owned_item_preserves_history_and_survives_initialize(env):
    m,client,_,store_id,other_store=env
    assert client.post('/painel/cardapio/ingredientes320',data={'name':'Excluir teste','price':'2,00'},follow_redirects=False).status_code==303
    with m.db() as c:
        item=dict(c.execute('SELECT * FROM ingredients320 WHERE professional_id=? AND name=?',(store_id,'Excluir teste')).fetchone())
        foreign=c.execute('INSERT INTO ingredients320(professional_id,name) VALUES(?,?)',(other_store,'Privado excluir')).lastrowid
        c.commit()
    assert client.post(f'/painel/cardapio/ingredientes320/{foreign}/excluir',follow_redirects=False).status_code==404
    response=client.post(f'/painel/cardapio/ingredientes320/{item["id"]}/excluir',follow_redirects=False)
    assert response.status_code==303 and 'item-excluido' in response.headers['location']
    with m.db() as c:
        initialize(c);initialize(c)
        assert item['id'] not in [r['id'] for r in catalog(c,store_id)]
        assert c.execute('SELECT available FROM shared_extras155 WHERE id=?',(item['extra_id325'],)).fetchone()[0]==0
        assert c.execute('SELECT image_filename FROM ingredients320 WHERE id=?',(item['id'],)).fetchone() is not None
    assert client.post('/painel/cardapio/ingredientes320',data={'name':'Excluir teste','price':'3,00'},follow_redirects=False).status_code==303
    with m.db() as c:
        restored=next(r for r in catalog(c,store_id) if r['name']=='Excluir teste')
        assert restored['price_cents']==300
    panel=client.get('/painel');assert 'Excluir item' in panel.text and 'Salvar alterações' in panel.text
