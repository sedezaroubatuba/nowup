import json
import sqlite3
import pytest
from nowup_combos303 import combo_kind,current_price,attach_prices

@pytest.mark.parametrize('category,flag,expected',[('Combos de whisky','1',True),('Lanches','1',True),('Combos de vodka','0',False),('Combos','0',False),('Combos',None,True),('Lanches',None,False)])
def test_type_does_not_change_category(category,flag,expected):
 enabled,saved=combo_kind(category,flag)
 assert enabled is expected and saved==category

def test_legacy_category_compatibility():assert combo_kind('__combos256',None)==(True,'Combos')

def test_prices_are_current_own_available_and_use_standalone_sale():
 c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
 from nowup_ingredients320 import initialize
 c.execute('CREATE TABLE professionals(id INTEGER PRIMARY KEY)')
 initialize(c)
 c.execute("CREATE TABLE products(id INTEGER,professional_id INTEGER,price_cents INTEGER,promo_price_cents INTEGER,available INTEGER,is_combo256 INTEGER,image_filename TEXT DEFAULT '')")
 c.executemany('INSERT INTO products(id,professional_id,price_cents,promo_price_cents,available,is_combo256) VALUES(?,?,?,?,?,?)',[(1,10,10000,0,1,0),(2,10,1200,1000,1,0),(3,20,500,0,1,0),(4,10,500,0,0,0),(5,10,500,0,1,1)])
 config={'combo_items':[{'product_id':1,'name':'Whisky','quantity':1},{'product_id':2,'name':'Red Bull','quantity':4}],'groups':[{'id':'ice','name':'Gelo','min':1,'max':1,'options':['Outra loja','Esgotado','Combo'],'product_ids':[3,4,5]}],'combo_manual':[{'name':'Canudo','quantity':100}]}
 # Prices come only from the store query; invalid/foreign refs never leak into comparison.
 product={'id':100,'is_combo256':1,'customization192':json.dumps({**config,'combo_manual':[]})}
 result=attach_prices(c,10,[product])[0]
 assert result['combo_prices303']=={'1':10000,'2':1000}
 c.execute('UPDATE products SET price_cents=11000 WHERE id=1')
 assert attach_prices(c,10,[product])[0]['combo_prices303']['1']==11000
 assert current_price({'price_cents':1000,'promo_price_cents':1200})==1000
 c.close()
