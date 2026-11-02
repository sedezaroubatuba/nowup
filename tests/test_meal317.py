import sqlite3
import pytest
from fastapi import HTTPException
from nowup_custom192 import parse_config, validate_customization
from nowup_included195 import resolve, initialize

def test_meal_removals_and_fixed_ingredients():
    c=parse_config({'is_meal317':True,'ingredients':[{'name':'Alface','removable':True},{'name':'Carne','removable':False}]})
    assert c['is_meal317']
    assert 'Retirar: Alface' in validate_customization(c,{'removed':['Alface']},'',False)
    with pytest.raises(HTTPException):validate_customization(c,{'removed':['Carne']},'',False)

def test_drinks_are_resolved_from_own_store_and_keep_names():
    conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row
    conn.executescript('CREATE TABLE professionals(id INTEGER PRIMARY KEY); CREATE TABLE products(id INTEGER PRIMARY KEY,professional_id,name,available,is_combo256);')
    initialize(conn)
    conn.executemany('INSERT INTO products VALUES(?,?,?,?,?)',[(1,10,'Coca-Cola',1,0),(2,11,'Outra loja',1,0),(3,10,'Indisponível',0,0)])
    def config(ids):return parse_config({'is_meal317':True,'included195':{'is_combo':True,'drink_product_ids':ids}})
    c=resolve(conn,10,config([1]));assert c['groups'][0]['options']==['Coca-Cola'];assert c['included195']['drink_product_ids']==[1]
    for ids in [[2],[3],[999],[True],[1,1]]:
        with pytest.raises(HTTPException):resolve(conn,10,config(ids))


def test_description_only_meal_opens_personalization_and_accepts_notes():
    from nowup_custom192 import save_config
    conn=sqlite3.connect(':memory:')
    conn.execute("CREATE TABLE products(id INTEGER PRIMARY KEY,customization192 TEXT,is_dish INTEGER DEFAULT 0)")
    conn.execute("INSERT INTO products(id) VALUES(1)")
    config=parse_config({'is_meal317':True,'ingredients':[],'notes':True})
    save_config(conn,1,config)
    assert conn.execute('SELECT is_dish FROM products WHERE id=1').fetchone()[0]==1
    assert 'Sem tomate' in validate_customization(config,{},'Sem tomate',False)
    conn.close()
