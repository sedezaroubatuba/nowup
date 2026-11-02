"""One-time, guarded retirement of the six legacy options Samuel identified."""
import json

KEY = 'retired_sede_zero_options331'
EXPECTED = {1:'Bacon',2:'Carne',3:'Queijo',4:'Linguiça',5:'Parmesão',6:'Salada'}


def apply(conn):
    if conn.execute('SELECT 1 FROM site_settings WHERE key=?',(KEY,)).fetchone():return 0
    rows=conn.execute('''SELECT po.*,p.extras_mode FROM product_options po
        JOIN products p ON p.id=po.product_id JOIN professionals pro ON pro.id=p.professional_id
        WHERE pro.slug=? AND p.id=? AND po.id IN (1,2,3,4,5,6)''',('samuel-dos-santos-silva',115)).fetchall()
    if len(rows)!=6 or any(row['name']!=EXPECTED[row['id']] or row['price_cents']!=500 for row in rows):return 0
    # Keep a restorable record, the registry and historical orders unchanged.
    previous={'product_id':115,'extras_mode':rows[0]['extras_mode'],'options':[dict(row) for row in rows]}
    conn.execute('INSERT INTO site_settings(key,value) VALUES(?,?)',(KEY,json.dumps(previous,ensure_ascii=False)))
    conn.execute('UPDATE product_options SET available=0,shared_selected155=0 WHERE product_id=115 AND id IN (1,2,3,4,5,6)')
    if not conn.execute('SELECT 1 FROM product_options WHERE product_id=115 AND available=1').fetchone():
        conn.execute("UPDATE products SET extras_mode='none' WHERE id=115")
    return 6
