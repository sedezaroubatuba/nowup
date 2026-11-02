"""Reusable ingredient names and optional photos scoped to one merchant."""
from fastapi import Request, Form, File, UploadFile, HTTPException
from fastapi.responses import RedirectResponse


def initialize(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS ingredients320(id INTEGER PRIMARY KEY,professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,name TEXT NOT NULL,image_filename TEXT NOT NULL DEFAULT '')")
    columns={r['name'] for r in conn.execute('PRAGMA table_info(ingredients320)')}
    for name,definition in [('deleted327','INTEGER NOT NULL DEFAULT 0'),('price_cents','INTEGER'),('extra_id325','INTEGER NOT NULL DEFAULT 0')]:
        if name not in columns:conn.execute(f'ALTER TABLE ingredients320 ADD COLUMN {name} {definition}')
    tables={r['name'] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'shared_extras155' in tables:
        conn.execute("INSERT INTO ingredients320(professional_id,name,price_cents,extra_id325) SELECT e.professional_id,e.name,e.price_cents,e.id FROM shared_extras155 e WHERE e.id=(SELECT MIN(e2.id) FROM shared_extras155 e2 WHERE e2.professional_id=e.professional_id AND lower(e2.name)=lower(e.name)) AND NOT EXISTS(SELECT 1 FROM ingredients320 i WHERE i.professional_id=e.professional_id AND lower(i.name)=lower(e.name))")
        conn.execute("UPDATE ingredients320 SET extra_id325=(SELECT e.id FROM shared_extras155 e WHERE e.professional_id=ingredients320.professional_id AND lower(e.name)=lower(ingredients320.name) ORDER BY e.id LIMIT 1),price_cents=(SELECT e.price_cents FROM shared_extras155 e WHERE e.professional_id=ingredients320.professional_id AND lower(e.name)=lower(ingredients320.name) ORDER BY e.id LIMIT 1) WHERE deleted327=0 AND extra_id325=0 AND EXISTS(SELECT 1 FROM shared_extras155 e WHERE e.professional_id=ingredients320.professional_id AND lower(e.name)=lower(ingredients320.name))")
    if 'included_choices195' in tables:
        conn.execute("INSERT INTO ingredients320(professional_id,name) SELECT c.professional_id,c.name FROM included_choices195 c WHERE c.kind='side' AND NOT EXISTS(SELECT 1 FROM ingredients320 i WHERE i.professional_id=c.professional_id AND lower(i.name)=lower(c.name)) GROUP BY c.professional_id,lower(c.name)")
    conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS ingredient_name320 ON ingredients320(professional_id,lower(name))')


def catalog(conn, store_id):
    return [dict(row) for row in conn.execute('SELECT * FROM ingredients320 WHERE professional_id=? AND deleted327=0 ORDER BY name,id',(store_id,))]


def bind(conn, store_id, config):
    for ingredient in config.get('ingredients',[]):
        ref=ingredient.get('ingredient_id320')
        ingredient.pop('image_filename',None)
        if ref:
            row=conn.execute('SELECT name,image_filename FROM ingredients320 WHERE id=? AND professional_id=?',(ref,store_id)).fetchone()
            if not row:raise HTTPException(400,'Selecione um ingrediente cadastrado na sua própria loja.')
            ingredient['name']=row['name']
            if row['image_filename']:ingredient['image_filename']=row['image_filename']
    names=[i['name'].casefold() for i in config.get('ingredients',[])]
    if len(names)!=len(set(names)):raise HTTPException(400,'Não repita ingredientes na refeição.')
    return config


def attach_photos329(config, items):
    """Refresh linked ingredient photos and match legacy names within this store only."""
    by_id={item['id']:item for item in items}
    by_name={}
    normalize=lambda name:' '.join(name.casefold().split())
    for item in items:
        by_name.setdefault(normalize(item['name']),[]).append(item)
    for ingredient in config.get('ingredients',[]):
        ref=ingredient.get('ingredient_id320')
        matches=by_name.get(normalize(ingredient['name']),[])
        item=by_id.get(ref) if ref else (matches[0] if len(matches)==1 else None)
        if item:
            ingredient.pop('image_filename',None)
            if item.get('image_filename'):ingredient['image_filename']=item['image_filename']
    return config


def install(g):
    @g['app'].post('/painel/cardapio/ingredientes320')
    def save(request:Request,name:str=Form(...),ingredient_id:int=Form(0),photo:UploadFile=File(None),price:str=Form("")):
        user=g['require_user'](request,'professional');conn=g['db']()
        try:
            store=g['require_premium_catalog'](conn,user['id']);name=name.strip()
            if not name or len(name)>100:raise HTTPException(400,'Informe o ingrediente com até 100 caracteres.')
            current=None
            if ingredient_id:
                current=conn.execute('SELECT * FROM ingredients320 WHERE id=? AND professional_id=?',(ingredient_id,store['id'])).fetchone()
                if not current or current['deleted327']:raise HTTPException(404,'Ingrediente não encontrado.')
            if not ingredient_id:
                archived=conn.execute('SELECT * FROM ingredients320 WHERE professional_id=? AND lower(name)=lower(?) AND deleted327=1',(store['id'],name)).fetchone()
                if archived:current=archived;ingredient_id=archived['id']
            duplicate=conn.execute('SELECT id FROM ingredients320 WHERE professional_id=? AND lower(name)=lower(?) AND id!=?',(store['id'],name,ingredient_id)).fetchone()
            if duplicate:return RedirectResponse('/painel?erro=ingrediente-duplicado#ingredientes320',303)
            cents=g['price_to_cents'](price) if price.strip() else None
            if cents is not None and cents<0:raise HTTPException(400,'Informe um preço válido para o adicional.')
            extra_id=current['extra_id325'] if current else 0
            if cents is not None:
                if not extra_id:
                    existing=conn.execute('SELECT id FROM shared_extras155 WHERE professional_id=? AND lower(name)=lower(?) ORDER BY id LIMIT 1',(store['id'],name)).fetchone()
                    if existing:extra_id=existing['id']
                if extra_id:conn.execute('UPDATE shared_extras155 SET name=?,price_cents=?,available=1 WHERE id=? AND professional_id=?',(name,cents,extra_id,store['id']))
                else:extra_id=conn.execute('INSERT INTO shared_extras155(professional_id,name,price_cents,available) VALUES(?,?,?,1)',(store['id'],name,cents)).lastrowid
            elif extra_id:
                conn.execute('UPDATE shared_extras155 SET name=?,available=0 WHERE id=? AND professional_id=?',(name,extra_id,store['id']))
            image=g['save_image'](photo) if photo and photo.filename else (current['image_filename'] if current else '')
            if current:conn.execute('UPDATE ingredients320 SET name=?,image_filename=?,price_cents=?,extra_id325=?,deleted327=0 WHERE id=? AND professional_id=?',(name,image,cents,extra_id,ingredient_id,store['id']))
            else:conn.execute('INSERT INTO ingredients320(professional_id,name,image_filename,price_cents,extra_id325) VALUES(?,?,?,?,?)',(store['id'],name,image,cents,extra_id))
            if extra_id:g['sync_shared155'](conn,store['id'])
            conn.commit()
        finally:conn.close()
        return g['catalog_return328'](request,'/painel?ok=ingrediente#ingredientes320')

    @g['app'].post('/painel/cardapio/ingredientes320/{ingredient_id}/excluir')
    def delete(request:Request,ingredient_id:int):
        user=g['require_user'](request,'professional');conn=g['db']()
        try:
            store=g['require_premium_catalog'](conn,user['id'])
            item=conn.execute('SELECT * FROM ingredients320 WHERE id=? AND professional_id=? AND deleted327=0',(ingredient_id,store['id'])).fetchone()
            if not item:raise HTTPException(404,'Item não encontrado.')
            conn.execute('UPDATE ingredients320 SET deleted327=1 WHERE id=? AND professional_id=?',(ingredient_id,store['id']))
            if item['extra_id325']:
                conn.execute('UPDATE shared_extras155 SET available=0 WHERE id=? AND professional_id=?',(item['extra_id325'],store['id']))
                g['sync_shared155'](conn,store['id'])
            conn.execute("UPDATE included_choices195 SET available=0 WHERE professional_id=? AND kind='side' AND lower(name)=lower(?)",(store['id'],item['name']))
            conn.commit()
        finally:conn.close()
        return RedirectResponse('/painel?ok=item-excluido#ingredientes320',303)
