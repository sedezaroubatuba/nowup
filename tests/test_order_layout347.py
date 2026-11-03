import json
from bs4 import BeautifulSoup
from jinja2 import Environment,FileSystemLoader
from nowup_combo_pack305 import read_pack
from nowup_order_layout347 import local_time,note_lines
from test_merchant228 import env


def template_env():
    e=Environment(loader=FileSystemLoader('templates'),autoescape=True)
    e.filters['combo_pack305']=read_pack;e.filters['order_notes347']=note_lines;e.filters['order_datetime347']=local_time
    return e


def test_notes_are_separate_and_original_instructions_are_preserved():
    e=template_env();item={'quantity':1,'product_name':'X frango egg','unit_price_cents':5490,'notes':'Bem passado · Retirar: Salada, Queijo · Bebida: 1 × Coca zero\n<sem molho>','combo_pack305':''}
    rendered=e.get_template('order_line347.html').module.line(item,[{'option_name':'Bacon'},{'option_name':'Carne'},{'option_name':'Queijo'}],True)
    soup=BeautifulSoup(str(rendered),'html.parser')
    assert soup.h3.text=='X frango egg' and soup.select_one('.nu347-item-price').text=='R$ 54,90'
    assert [x.text for x in soup.select('.nu347-extras li')]==['Bacon','Carne','Queijo']
    assert [x.text for x in soup.select('.nu347-observations li')]==['Bem passado','Retirar: Salada, Queijo','Bebida: 1 × Coca zero','<sem molho>']
    assert '&lt;sem molho&gt;' in str(rendered)


def test_combo_snapshot_is_a_per_unit_picking_list_not_a_long_note():
    pack={'version':1,'items':[{'name':'Whisky maçã verde 1 litro','quantity':1,'role':'principal'},{'name':'Red bull tradicional 250ml','quantity':2,'role':'included','group':'Energéticos'},{'name':'Copão 700ml','quantity':4,'role':'manual'}],'note':'Sem sacola'}
    item={'quantity':2,'product_name':'Combo Jack Daniel','unit_price_cents':25990,'combo_pack305':json.dumps(pack),'notes':'Texto legado duplicado'}
    rendered=template_env().get_template('order_line347.html').module.line(item,[],True)
    soup=BeautifulSoup(str(rendered),'html.parser')
    assert len(soup.select('.nu305-pack-unit'))==2
    assert soup.select_one('.nu347-item-price').text=='R$ 519,80'
    assert 'Combo 1 de 2' in soup.text and 'Combo 2 de 2' in soup.text
    assert soup.text.count('Red bull tradicional 250ml')==2 and 'Texto legado duplicado' not in soup.text
    assert 'Sem sacola' in soup.text


def test_tracking_renders_four_separate_products_totals_and_local_dates(env):
    m,client,_,pid,_=env
    with m.db() as c:
        stamp='2026-11-03T15:59:00+00:00'
        oid=c.execute("INSERT INTO orders(professional_id,customer_name,status,subtotal_cents,delivery_fee_cents,total_cents,created_at,updated_at,tracking_token,order_code) VALUES(?,'Cliente teste347','new',40189,400,40589,?,?,?,?)",(pid,stamp,stamp,'layout347-public-test','NU-347')).lastrowid
        for name,price,notes in [('X frango egg',5490,'Bem passado · Retirar: Salada'),('Combo jack deniel apple 1litro red bull',25990,'Energéticos: 4 × Red bull · Copão: 4 × Copão'),('Bom bom garoto 250g',1519,''),('Heineken 350ml fd/12',7190,'Talheres: não')]:
            c.execute('INSERT INTO order_items(order_id,product_name,quantity,unit_price_cents,notes) VALUES(?,?,1,?,?)',(oid,name,price,notes))
        c.execute('INSERT INTO order_status_history(order_id,status,created_at) VALUES(?,?,?)',(oid,'new',stamp));c.commit()
    response=client.get('/pedido/layout347-public-test');assert response.status_code==200,response.text
    soup=BeautifulSoup(response.text,'html.parser')
    assert len(soup.select('.nu347-lines .nu347-line'))==4
    assert len(soup.select('.nu347-order-totals>div'))==3
    assert '405,89' in soup.select_one('.nu347-grand-total').text
    assert '03/11/2026 às 12:59' in soup.select_one('.order-timeline time').text
    assert soup.select_one('link[href="/static/order-layout347.css?v=348"]')


def test_time_and_legacy_notes_helpers():
    assert local_time('2026-11-03T15:59:00Z')=='03/11/2026 às 12:59'
    assert local_time('2026-11-03T15:59:00')=='03/11/2026 às 12:59'
    assert local_time('invalid')=='invalid'
    assert note_lines('A · B\r\nC')==['A','B','C']
