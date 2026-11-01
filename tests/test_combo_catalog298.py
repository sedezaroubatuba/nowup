import sqlite3
import pytest
from fastapi import HTTPException
from nowup_custom192 import parse_config, bind_combo_products

@pytest.fixture
def db():
    conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row
    conn.execute('CREATE TABLE products(id INTEGER,professional_id INTEGER,name TEXT,available INTEGER,is_combo256 INTEGER,category TEXT)')
    conn.executemany('INSERT INTO products VALUES(?,?,?,?,?,?)',[(1,10,'Red Bull',1,0,'Bebidas'),(2,10,'Gelo de coco',1,0,'Gelo'),(3,20,'Outra loja',1,0,'Bebidas'),(4,10,'Indisponível',0,0,'Bebidas'),(5,10,'Combo',1,1,'Combos')])
    yield conn
    conn.close()

def config(ref=1):
    return parse_config({'combo_items':[{'product_id':ref,'name':'Nome adulterado','quantity':4}],'groups':[{'id':'gelo','name':'Escolha o gelo','min':1,'max':1,'options':['Falso'],'product_ids':[2]}]})

def test_owned_ids_and_server_names_round_trip(db):
    result=bind_combo_products(db,10,config())
    assert result['combo_items']==[{'product_id':1,'name':'Red Bull','quantity':4}]
    assert result['groups'][0]['options']==['Gelo de coco']
    assert parse_config(result)==result

@pytest.mark.parametrize('ref',[3,4,5,999])
def test_reject_foreign_unavailable_combo_and_deleted_product(db,ref):
    with pytest.raises(HTTPException):bind_combo_products(db,10,config(ref))

def test_cannot_reference_self_or_foreign_swap(db):
    with pytest.raises(HTTPException):bind_combo_products(db,10,config(),1)
    value=config();value['groups'][0]['product_ids']=[3]
    with pytest.raises(HTTPException):bind_combo_products(db,10,value)

def test_legacy_names_require_exact_unambiguous_owned_match(db):
    value=parse_config({'combo_items':[{'name':'Red Bull','quantity':2}]})
    assert bind_combo_products(db,10,value)['combo_items'][0]['product_id']==1
    for name in ['Copo','Outra loja','Produto inventado']:
        with pytest.raises(HTTPException):bind_combo_products(db,10,parse_config({'combo_items':[{'name':name,'quantity':1}]}))
    db.execute("INSERT INTO products VALUES(6,10,'Red Bull',1,0,'Bebidas')")
    with pytest.raises(HTTPException):bind_combo_products(db,10,parse_config({'combo_items':[{'name':'Red Bull','quantity':1}]}))

def test_quantity_refs_and_empty_combo_validation(db):
    for ref in [True,0,-1,'1']:
        with pytest.raises(HTTPException):config(ref)
    for qty in [0,100,True]:
        with pytest.raises(HTTPException):parse_config({'combo_items':[{'product_id':1,'name':'Red Bull','quantity':qty}]})
    with pytest.raises(HTTPException):bind_combo_products(db,10,parse_config({}))
    value=config();value['combo_items']*=2
    with pytest.raises(HTTPException):bind_combo_products(db,10,value)

def test_regular_food_choices_unchanged():
    value=parse_config({'groups':[{'id':'ponto','name':'Ponto','min':1,'max':1,'options':['Bem passado','Ao ponto']}]})
    assert 'product_ids' not in value['groups'][0]
