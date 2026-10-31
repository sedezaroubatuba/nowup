import json
import sqlite3
import unittest
from nowup_food91 import register_food_feed

class HomeFeedTests(unittest.TestCase):
    def test_promotions_and_combos_keep_public_store_and_availability_filters(self):
        class Conn(sqlite3.Connection):
            def close(self): pass
        conn=sqlite3.connect(':memory:',factory=Conn);conn.row_factory=sqlite3.Row
        conn.executescript('''CREATE TABLE professionals(id INTEGER,blocked INTEGER,admission_status TEXT,is_premium INTEGER,offer_mode TEXT,city TEXT,display_name TEXT,slug TEXT);
        CREATE TABLE products(id INTEGER,professional_id INTEGER,available INTEGER,max_quantity INTEGER,image_filename TEXT,category TEXT,price_cents INTEGER,promo_price_cents INTEGER,name TEXT,is_combo256 INTEGER);
        CREATE TABLE product_categories(professional_id INTEGER,name TEXT,active INTEGER);
        INSERT INTO professionals VALUES(1,0,'approved',1,'menu','Ubatuba','Loja A','loja-a'),(2,1,'approved',1,'menu','Ubatuba','Bloqueada','bloqueada');
        INSERT INTO products VALUES(1,1,1,99,'a.jpg','Bebidas',1000,850,'Oferta',0),(2,1,1,99,'b.jpg','Combos',2500,0,'Combo',1),(3,1,0,99,'c.jpg','Bebidas',1000,700,'Indisponível',0),(4,2,1,99,'d.jpg','Bebidas',1000,500,'Bloqueada',0),(5,1,1,0,'e.jpg','Combos',2000,0,'Sem estoque',1);''')
        class App:
            def get(self,path):
                def register(fn): self.feed=fn;return fn
                return register
        app=App();register_food_feed(app,lambda:conn,lambda c:{},lambda s:['Ubatuba'],lambda s:{'open':True},lambda:'1=1')
        promo=json.loads(app.feed(kind='promotions').body)['items'];combo=json.loads(app.feed(kind='combos').body)['items']
        self.assertEqual([p['id'] for p in promo],[1]);self.assertEqual(promo[0]['regular_price_cents'],1000);self.assertEqual(promo[0]['discount_percent'],15)
        self.assertEqual([p['id'] for p in combo],[2]);self.assertIn('produto=2',combo[0]['url'])
        self.assertEqual(json.loads(app.feed(city='Outra cidade',kind='combos').body)['items'],[])
        sqlite3.Connection.close(conn)
