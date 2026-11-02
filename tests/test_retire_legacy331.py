import sqlite3
from nowup_retire_legacy331 import apply,EXPECTED,KEY


def database(slug='samuel-dos-santos-silva'):
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.executescript('CREATE TABLE site_settings(key TEXT PRIMARY KEY,value);CREATE TABLE professionals(id,slug);CREATE TABLE products(id,professional_id,extras_mode);CREATE TABLE product_options(id,product_id,name,price_cents,available,shared_selected155);CREATE TABLE ingredients320(id,name,price_cents);CREATE TABLE order_item_options(option_id,option_name,price_cents);')
    c.execute('INSERT INTO professionals VALUES(10,?)',(slug,));c.execute("INSERT INTO products VALUES(115,10,'legacy')")
    c.executemany('INSERT INTO product_options VALUES(?,115,?,500,1,1)',EXPECTED.items())
    c.execute("INSERT INTO products VALUES(403,10,'selected')");c.execute("INSERT INTO product_options VALUES(10,403,'Bacon',500,1,1)")
    c.execute("INSERT INTO ingredients320 VALUES(10,'Bacon',500)");c.execute("INSERT INTO order_item_options VALUES(1,'Bacon',500)")
    return c


def test_only_identified_links_retire_and_do_not_repeat():
    c=database();assert apply(c)==6;assert apply(c)==0
    assert not c.execute('SELECT id FROM product_options WHERE product_id=115 AND available=1').fetchall()
    assert c.execute('SELECT available FROM product_options WHERE id=10').fetchone()[0]==1
    assert c.execute('SELECT count(*) FROM ingredients320').fetchone()[0]==1
    assert c.execute('SELECT count(*) FROM order_item_options').fetchone()[0]==1
    assert c.execute('SELECT value FROM site_settings WHERE key=?',(KEY,)).fetchone()
    assert c.execute('SELECT extras_mode FROM products WHERE id=115').fetchone()[0]=='none'


def test_wrong_store_or_changed_price_never_modified():
    c=database('other-store');assert apply(c)==0
    c=database();c.execute('UPDATE product_options SET price_cents=600 WHERE id=1');assert apply(c)==0
    assert c.execute('SELECT sum(available) FROM product_options').fetchone()[0]==7
