import json
import sqlite3
import pytest
from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader
from nowup_custom192 import parse_config, validate_customization
from nowup_combo_pack305 import build_pack, read_pack
from nowup_storeapp257 import validate

def config():
 return parse_config({'combo_items':[{'product_id':1,'name':'Whisky','quantity':1,'principal':True},{'product_id':2,'name':'Red Bull','quantity':4,'group_id301':'drink'}],'groups':[{'id':'drink','name':'Energéticos','min':4,'max':4,'quantity_mode':True,'options':['Red Bull','Zero'],'product_ids':[2,3]}],'combo_manual':[{'name':'Canudo','quantity':4}],'notes':True})

def choices():return {'groups':{'drink':['Red Bull']*2+['Zero']*2}}

def test_principal_validation():
 c=config();assert c['combo_items'][0]['principal'] is True
 assert 'Produto principal: 1 × Whisky' in validate_customization(c,choices(),'',False)
 c['combo_items'][1]['principal']=True
 with pytest.raises(HTTPException):parse_config(c)

def test_snapshot_and_separate_units():
 c=config();saved=build_pack(c,choices(),'<sem sacola>');c['combo_items'][0]['name']='Alterado'
 pack=read_pack(saved);assert pack['items'][0]['name']=='Whisky'
 assert [(r['name'],r['quantity']) for r in pack['items']]==[('Whisky',1),('Red Bull',2),('Zero',2),('Canudo',4)]
 env=Environment(loader=FileSystemLoader('templates'),autoescape=True);env.filters['combo_pack305']=read_pack
 html=env.get_template('combo_pack305.html').module.picking({'quantity':2,'combo_pack305':saved})
 assert 'Combo 1 de 2' in html and 'Combo 2 de 2' in html
 assert html.count('2 ×</strong> Red Bull')==2
 assert '4 ×</strong> Red Bull' not in html and '&lt;sem sacola&gt;' in html
 assert read_pack('legacy notes') is None

def test_checkout_keeps_snapshot_per_unit_and_price():
 conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row
 conn.execute('CREATE TABLE products(id,professional_id,available,category,max_quantity,customization192,is_combo256,promo_price_cents,price_cents,name)')
 conn.execute('CREATE TABLE product_categories(professional_id,name,active)')
 conn.execute('INSERT INTO products VALUES(100,10,1,?,99,?,1,0,15000,?)',('Whisky',json.dumps(config()),'Combo whisky'))
 g={'shop_status':lambda p:{'open':True},'options_single158':lambda *a:([],0),'validate_customization':validate_customization,'parse_config':parse_config,'validate_choices89':lambda *a:None}
 p={'id':10,'allows_pickup':1,'minimum_order_cents':0}
 rows,subtotal,*_=validate(g,conn,p,json.dumps([{'id':100,'quantity':2,'customization':choices(),'notes':'Sem sacola'}]),'pickup','pix','','','')
 assert subtotal==30000 and rows[0][4]==15000
 pack=read_pack(rows[0][0]['combo_pack305']);assert pack['items'][0]['quantity']==1 and pack['note']=='Sem sacola'
 assert pack['items'][1]['quantity']==2
