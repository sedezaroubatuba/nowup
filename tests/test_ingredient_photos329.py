import json
import sqlite3
from nowup_ingredients320 import initialize
from nowup_combos303 import attach_prices


def test_current_photos_for_imported_and_legacy_ingredients():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.execute('CREATE TABLE professionals(id INTEGER PRIMARY KEY)');initialize(c)
    c.execute('CREATE TABLE products(id,professional_id,price_cents,promo_price_cents,image_filename,available,is_combo256)')
    c.executemany('INSERT INTO ingredients320(id,professional_id,name,image_filename,deleted327) VALUES(?,?,?,?,?)',[(1,10,'Queijo','queijo.jpg',0),(2,10,'Alface','alface.jpg',0),(3,20,'Bacon','privado.jpg',0),(4,10,'Pão','',0),(5,10,'Antigo','deleted.jpg',1)])
    config={'ingredients':[{'name':'Queijo','ingredient_id320':1,'image_filename':'old.jpg','removable':True},{'name':' ALFACE ','removable':True},{'name':'Bacon','removable':True},{'name':'Pão','removable':False},{'name':'Antigo'}]}
    original=json.dumps(config)
    result=attach_prices(c,10,[{'customization192':original,'is_combo256':0}])[0]
    items=json.loads(result['customization192'])['ingredients']
    assert items[0]['image_filename']=='queijo.jpg'
    assert items[1]['image_filename']=='alface.jpg'
    assert all('image_filename' not in item for item in items[2:])
    assert items[3]['removable'] is False
    assert config['ingredients'][0]['image_filename']=='old.jpg'
