"""One-time owner-authorized cover and second sharing slide for Sede Zero."""
from pathlib import Path
import shutil

def apply(g):
    filename='sede-zero-capa403.webp'
    target=Path(g['UPLOAD_DIR'])/filename
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():shutil.copyfile(Path(g['BASE'])/'static'/filename,target)
    with g['db']() as c:
        c.execute('BEGIN IMMEDIATE')
        c.execute('CREATE TABLE IF NOT EXISTS nowup_migrations352(name TEXT PRIMARY KEY)')
        key='sede-zero-cover-sharing403'
        if c.execute('SELECT 1 FROM nowup_migrations352 WHERE name=?',(key,)).fetchone():return
        p=c.execute("SELECT id,slug FROM professionals WHERE slug='adega-sede-zero' AND is_demo=0 AND upper(trim(display_name))='ADEGA SEDE ZERO'").fetchone()
        if not p:return
        banners=[dict(b) for b in c.execute('SELECT * FROM store_banners207 WHERE professional_id=? ORDER BY sort_order,id',(p['id'],))]
        matches=[b for b in banners if 'compartilh' in b['title'].lower() or b['image']=='ecac76a07c45157a9baabd7c03f266c0.jpg']
        chosen=matches[0]['id'] if matches else None
        if chosen is None:
            chosen=c.execute("INSERT INTO store_banners207(professional_id,title,image,mode,product_ids,active,link,sort_order) VALUES(?,?,?,'link','[]',1,?,1)",(p['id'],'Compartilhe o cardápio da Sede Zero',filename,'/p/'+p['slug']+'/menu?compartilhar=1')).lastrowid
        else:
            c.execute("UPDATE store_banners207 SET title=?,image=?,mode='link',product_ids='[]',active=1,link=? WHERE id=?",('Compartilhe o cardápio da Sede Zero',filename,'/p/'+p['slug']+'/menu?compartilhar=1',chosen))
        for b in matches[1:]:c.execute('UPDATE store_banners207 SET active=0 WHERE id=?',(b['id'],))
        banners.sort(key=lambda b:not b['active'])
        rest=[b['id'] for b in banners if b['id']!=chosen and b['id'] not in {x['id'] for x in matches[1:]}]
        rest.insert(min(1,len(rest)),chosen)
        for position,bid in enumerate(rest):c.execute('UPDATE store_banners207 SET sort_order=? WHERE id=?',(position,bid))
        c.execute('UPDATE professionals SET cover_filename=? WHERE id=?',(filename,p['id']))
        c.execute('INSERT INTO nowup_migrations352(name) VALUES(?)',(key,));c.commit()

def install(g):
    def startup403():apply(g)
    g['app'].router.add_event_handler('startup',startup403)
