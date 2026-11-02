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
