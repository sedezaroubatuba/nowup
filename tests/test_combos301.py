import sqlite3
import pytest
from fastapi import HTTPException
from nowup_custom192 import parse_config, bind_combo_products, validate_customization

@pytest.fixture
def db():
 c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
 c.execute('CREATE TABLE products(id INTEGER,professional_id INTEGER,name TEXT,available INTEGER,is_combo256 INTEGER,category TEXT)')
 c.executemany('INSERT INTO products VALUES(?,?,?,?,?,?)',[(1,10,'Red Bull',1,0,'Bebidas'),(2,10,'Red Bull sem açúcar',1,0,'Bebidas'),(3,10,'Gelo de coco',1,0,'Gelo'),(4,10,'Gelo de coco morango',1,0,'Gelo'),(5,20,'Outra loja',1,0,'Bebidas')]);yield c;c.close()

def cfg():
 return parse_config({'combo_items':[{'product_id':1,'name':'Red Bull','quantity':4,'group_id301':'bebidas'},{'product_id':3,'name':'Gelo de coco','quantity':4,'group_id301':'gelo'}], 'groups':[{'id':'bebidas','name':'Energéticos','min':4,'max':4,'options':['Red Bull','Red Bull sem açúcar'],'product_ids':[1,2],'quantity_mode':True},{'id':'gelo','name':'Gelos','min':4,'max':4,'options':['Gelo de coco','Gelo de coco morango'],'product_ids':[3,4],'quantity_mode':True}], 'combo_manual':[{'name':'Copo','quantity':4},{'name':'Canudo','quantity':4}],'notes':True,'utensils':False})

def selection():return {'groups':{'bebidas':['Red Bull']*2+['Red Bull sem açúcar']*2,'gelo':['Gelo de coco']*4}}

def test_four_drinks_four_ice_and_manual(db):
 config=bind_combo_products(db,10,cfg());notes=validate_customization(config,selection(),'',False)
 assert '2 × Red Bull' in notes and '4 × Gelo de coco' in notes
 assert config['combo_manual']==[{'name':'Copo','quantity':4},{'name':'Canudo','quantity':4}]
 assert parse_config(config)==config

@pytest.mark.parametrize('n',[0,3,5,99,100])
def test_reject_wrong_total(n):
 raw=selection();raw['groups']['bebidas']=['Red Bull']*n
 with pytest.raises(HTTPException):validate_customization(cfg(),raw,'',False)

def test_reject_forged_products_and_changed_linked_quantity(db):
 value=cfg();value['groups'][0]['product_ids'][1]=5
 with pytest.raises(HTTPException):bind_combo_products(db,10,value)
 value=cfg();value['combo_items'][0]['quantity']=3
 with pytest.raises(HTTPException):bind_combo_products(db,10,value)
 raw=selection();raw['groups']['bebidas']=['Outra loja']*4
 with pytest.raises(HTTPException):validate_customization(cfg(),raw,'',False)

def test_single_product_can_have_four_units_and_old_choices_stay_unique():
 value=cfg();value['groups'][0]['options']=['Red Bull'];value['groups'][0]['product_ids']=[1]
 assert parse_config(value)['groups'][0]['max']==4
 old=parse_config({'groups':[{'id':'ponto','name':'Ponto','min':1,'max':2,'options':['Ao ponto','Bem passado']}]})
 with pytest.raises(HTTPException):validate_customization(old,{'groups':{'ponto':['Ao ponto','Ao ponto']}},'',False)

def test_manual_quantity_must_be_positive():
 for q in [0,100,True]:
  value=cfg();value['combo_manual'][0]['quantity']=q
  with pytest.raises(HTTPException):parse_config(value)
