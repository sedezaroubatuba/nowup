"""Optional, merchant-maintained catalogue availability, not a reservation ledger."""
from fastapi import HTTPException
from nowup_fashion387 import read

def stock(mode,total,rows,sizes):
 if mode not in ('none','total','sizes'):raise HTTPException(400,'Escolha como controlar o estoque.')
 if mode=='none':return {'mode':'none'}
 def count(value):
  if not str(value).strip().isdigit() or not 0<=int(value)<=99999:raise HTTPException(400,'Use quantidades inteiras de 0 a 99999 no estoque.')
  return int(value)
 if mode=='total':return dict(mode=mode,total=count(total))
 options=[x.strip() for x in sizes.replace(';',',').split(',') if x.strip()]
 if not options:raise HTTPException(400,'Cadastre os tamanhos antes do estoque por tamanho.')
 values={}
 for line in rows.splitlines():
  if not line.strip():continue
  parts=[x.strip() for x in line.split(';')]
  if len(parts)!=2 or parts[0] not in options or parts[0] in values:raise HTTPException(400,'Confira o estoque por tamanho: use Tamanho;Quantidade, sem repetir.')
  values[parts[0]]=count(parts[1])
 return dict(mode=mode,sizes={s:values.get(s,0) for s in options})

def validate(product,raw,qty,counts):
 data=read(product.get('fashion_details387','')).get('stock',{})
 mode=data.get('mode','none')
 if mode=='none':return
 size=(raw.get('groups',{}).get('fashionSize385') or [''])[0]
 key=(product['id'],size if mode=='sizes' else '')
 counts[key]=counts.get(key,0)+qty
 limit=data.get('sizes',{}).get(size,0) if mode=='sizes' else data.get('total',0)
 if counts[key]>limit:raise HTTPException(400,product['name']+(' — '+size if size else '')+': quantidade maior que o estoque informado. Atualize o catálogo ou fale com a loja.')


def seed_colors(g):
 """Add color choices once to untouched illustrative items only."""
 import json
 from contextlib import closing
 with closing(g['db']()) as c,c:
  c.execute('CREATE TABLE IF NOT EXISTS fashion_demo_colors389 (product_id INTEGER PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE)')
  rows=c.execute("SELECT pr.id,pr.name,pr.customization192 FROM products pr JOIN professionals p ON p.id=pr.professional_id WHERE p.slug IN ('nowup-moda-demonstracao','nowup-moda-modelo') AND p.is_demo=1 AND pr.name IN ('Vestido midi roxo','Camiseta roxa básica') AND pr.image_filename IN ('moda386-vestido-1.webp','moda386-camiseta-1.webp')").fetchall()
  for row in rows:
   if c.execute('SELECT 1 FROM fashion_demo_colors389 WHERE product_id=?',(row['id'],)).fetchone():continue
   c.execute('INSERT INTO fashion_demo_colors389(product_id) VALUES(?)',(row['id'],))
   data=read(row['customization192'])
   if any(x.get('id')=='fashionColor385' for x in data.get('groups',[])):continue
   data.setdefault('groups',[]).append(dict(id='fashionColor385',name='Cor',min=1,max=1,options=['Roxo','Preto']))
   c.execute('UPDATE products SET customization192=? WHERE id=?',(json.dumps(data,ensure_ascii=False),row['id']))
