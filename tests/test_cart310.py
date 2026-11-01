import json
from test_merchant228 import env

def test_regular_product_can_be_highlighted_without_discount_or_relationship(env):
 m,client,_,pid,other=env
 form={'name':'Amendoim destaque','category':'Petiscos','price':'6,90','available':'1','recommend256':'1','recommend_config310':'1'}
 r=client.post('/painel/cardapio/produtos',data=form,follow_redirects=False);assert r.status_code==303,r.text
 with m.db() as c:
  product=c.execute("SELECT * FROM products WHERE professional_id=? AND name='Amendoim destaque'",(pid,)).fetchone()
  assert product['recommend256']==1 and product['is_combo256']==0 and product['promo_price_cents']==0 and product['related256']==''
  oid=c.execute("INSERT INTO products(professional_id,name,price_cents,created_at,updated_at) VALUES(?,'Outra loja',100,?,?)",(other,m.now_iso(),m.now_iso())).lastrowid
 assert client.post('/painel/cardapio/produtos/'+str(oid),data=form,follow_redirects=False).status_code==404
 form.pop('recommend256');assert client.post('/painel/cardapio/produtos/'+str(product['id']),data=form,follow_redirects=False).status_code==303
 with m.db() as c:assert c.execute('SELECT recommend256 FROM products WHERE id=?',(product['id'],)).fetchone()[0]==0

def test_combo_editor_can_change_highlight_without_losing_old_relationships(env):
 m,client,_,pid,_=env
 with m.db() as c:
  component=c.execute('SELECT id,name FROM products WHERE professional_id=? AND is_combo256=0 ORDER BY id LIMIT 1',(pid,)).fetchone()
 config=json.dumps({'combo_items':[{'product_id':component['id'],'name':component['name'],'quantity':1}]})
 form={'name':'Combo destaque','category':'Combos','price':'25,00','is_combo256':'1','available':'1','customization192':config,'combo_editor301':'1','recommend_config310':'1','recommend256':'1','related256':component['id']}
 assert client.post('/painel/cardapio/produtos',data=form,follow_redirects=False).status_code==303
 with m.db() as c:product=c.execute("SELECT * FROM products WHERE professional_id=? AND name='Combo destaque'",(pid,)).fetchone()
 form.pop('recommend256');form.pop('related256')
 assert client.post('/painel/cardapio/produtos/'+str(product['id']),data=form,follow_redirects=False).status_code==303
 with m.db() as c:
  row=c.execute('SELECT * FROM products WHERE id=?',(product['id'],)).fetchone()
  assert row['recommend256']==0 and row['related256']==str(component['id'])
 page=client.get('/painel');assert page.status_code==200
 assert 'Destacar este produto no carrinho' in page.text and 'até 5 sugestões' in page.text
