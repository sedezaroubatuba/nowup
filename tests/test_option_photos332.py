import sqlite3
from nowup_ingredients320 import initialize,option_photos332
from test_merchant228 import env


def test_option_photos_scoped_and_price_unchanged():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.execute('CREATE TABLE professionals(id)');initialize(c)
    c.executemany('INSERT INTO ingredients320(id,professional_id,name,image_filename,extra_id325) VALUES(?,?,?,?,?)',[(1,10,'Bacon','bacon.jpg',5),(2,10,'Ovo','',6),(3,20,'Queijo','private.jpg',7)])
    options=[{'id':1,'name':'Bacon','price_cents':500,'shared_extra_id':5},{'id':2,'name':'Ovo','price_cents':300,'shared_extra_id':6},{'id':3,'name':'Queijo','price_cents':500,'shared_extra_id':7},{'id':4,'name':' BACON ','price_cents':500,'shared_extra_id':0}]
    result=option_photos332(c,10,options)
    assert [item['image_filename'] for item in result]==['bacon.jpg','','','bacon.jpg']
    assert [item['price_cents'] for item in result]==[500,300,500,500]
    assert all('image_filename' not in item for item in options)


def test_photos_render_in_store_and_menu_without_placeholder(env):
    from bs4 import BeautifulSoup
    m,client,_,store_id,_=env
    with m.db() as c:
        # Photo coverage uses a currently supported standalone-menu plan.
        c.execute("UPDATE professionals SET plan_active='completo' WHERE id=?",(store_id,))
        c.execute('INSERT INTO shared_extras155(professional_id,name,price_cents,available) VALUES(?,?,500,1)',(store_id,'Bacon foto 332'))
        eid=c.execute('SELECT id FROM shared_extras155 WHERE professional_id=? AND name=?',(store_id,'Bacon foto 332')).fetchone()[0]
        c.execute('INSERT INTO ingredients320(professional_id,name,image_filename,price_cents,extra_id325) VALUES(?,?,?,500,?)',(store_id,'Bacon foto 332','bacon332.jpg',eid))
        stamp=m.now_iso()
        pid=c.execute('INSERT INTO products(professional_id,name,category,price_cents,available,created_at,updated_at,is_dish,extras_mode) VALUES(?,?,?,2500,1,?,?,1,?)',(store_id,'Lanche 332','Lanches',stamp,stamp,'selected')).lastrowid
        m.configure_shared155(c,store_id,pid,'selected',[eid],3)
        slug=c.execute('SELECT slug FROM professionals WHERE id=?',(store_id,)).fetchone()[0];c.commit()
    for path in [f'/p/{slug}',f'/p/{slug}/cardapio']:
        response=client.get(path);assert response.status_code==200
        soup=BeautifulSoup(response.text,'html.parser')
        card=soup.select_one(f'[data-product][data-id="{pid}"]')
        photo=card.select_one('.product-options img.nu332-extra-photo')
        assert photo and photo['src']=='/uploads/bacon332.jpg'
        assert 'Bacon foto 332' in photo.parent.get_text() and '5,00' in photo.parent.get_text()
