import sqlite3
import pytest
from fastapi import HTTPException
from nowup_custom192 import parse_config, validate_customization
from nowup_included195 import resolve

@pytest.fixture
def conn():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.execute('CREATE TABLE products(id INTEGER PRIMARY KEY,professional_id,name,available,is_combo256)')
    c.executemany('INSERT INTO products VALUES(?,?,?,?,?)',[(1,10,'Coca-Cola',1,0),(2,10,'Guaraná',1,0),(3,10,'Mandioca',1,0),(4,10,'Legumes',1,0),(5,20,'Outra loja',1,0),(6,10,'Indisponível',0,0),(7,10,'Outro combo',1,1)])
    yield c;c.close()

def config():
    return parse_config({'is_meal317':True,'meal_groups324':True,'meal_combo324':True,'notes':True,'ingredients':[{'name':'Sal','removable':True},{'name':'Costela','removable':False}], 'groups':[{'id':'bebida','name':'Bebidas','min':4,'max':4,'quantity_mode':True,'options':['Nome não confiável 1','Nome não confiável 2'],'product_ids':[1,2]},{'id':'acomp','name':'Acompanhamento','min':1,'max':1,'quantity_mode':True,'options':['Mandioca','Legumes'],'product_ids':[3,4]}]})

def test_independent_quantities_and_repeat_products(conn):
    c=resolve(conn,10,config());assert c['groups'][0]['options']==['Coca-Cola','Guaraná']
    raw={'removed':['Sal'],'groups':{'bebida':['Coca-Cola']*4,'acomp':['Legumes']}}
    note=validate_customization(c,raw,'Sem cebola, por favor',False)
    assert '4 × Coca-Cola' in note and '1 × Legumes' in note and 'Sem cebola' in note and 'Retirar: Sal' in note
    for drinks,sides in [(5,0),(3,2),(4,0),(4,2),(0,1)]:
        with pytest.raises(HTTPException):validate_customization(c,{'groups':{'bebida':['Coca-Cola']*drinks,'acomp':['Mandioca']*sides}},'',False)
    with pytest.raises(HTTPException):validate_customization(c,{**raw,'removed':['Costela']},'',False)

@pytest.mark.parametrize('ref',[5,6,7,999])
def test_reject_products_from_other_stores_or_unavailable(conn,ref):
    c=config();c['groups'][0]['product_ids'][0]=ref
    with pytest.raises(HTTPException):resolve(conn,10,c)

def test_exact_counts_configuration_and_description_only(conn):
    c=config();c['groups'][0]['min']=0
    with pytest.raises(HTTPException):resolve(conn,10,c)
    c=config();c['groups'][0]['product_ids']=[1,1]
    with pytest.raises(HTTPException):resolve(conn,10,c)
    c=config();c['groups'][0].pop('product_ids')
    with pytest.raises(HTTPException):resolve(conn,10,c)
    with pytest.raises(HTTPException):parse_config({'meal_groups324':'yes'})
    c=parse_config({'is_meal317':True,'meal_groups324':True,'meal_combo324':False,'ingredients':[],'notes':True})
    c=resolve(conn,10,c);assert c['groups']==[]
    assert 'Sem tomate' in validate_customization(c,{},'Sem tomate',False)
    c['meal_combo324']=True
    with pytest.raises(HTTPException):resolve(conn,10,c)
