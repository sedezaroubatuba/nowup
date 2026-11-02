"""Reusable ingredient names and optional photos scoped to one merchant."""
from fastapi import Request, Form, File, UploadFile, HTTPException
from fastapi.responses import RedirectResponse


def initialize(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS ingredients320(id INTEGER PRIMARY KEY,professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,name TEXT NOT NULL,image_filename TEXT NOT NULL DEFAULT '')")
    conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS ingredient_name320 ON ingredients320(professional_id,lower(name))')


def catalog(conn, store_id):
    return [dict(row) for row in conn.execute('SELECT * FROM ingredients320 WHERE professional_id=? ORDER BY name,id',(store_id,))]


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


def install(g):
    @g['app'].post('/painel/cardapio/ingredientes320')
    def save(request:Request,name:str=Form(...),ingredient_id:int=Form(0),photo:UploadFile=File(None)):
        user=g['require_user'](request,'professional');conn=g['db']()
        try:
            store=g['require_premium_catalog'](conn,user['id']);name=name.strip()
            if not name or len(name)>100:raise HTTPException(400,'Informe o ingrediente com até 100 caracteres.')
            current=None
            if ingredient_id:
                current=conn.execute('SELECT * FROM ingredients320 WHERE id=? AND professional_id=?',(ingredient_id,store['id'])).fetchone()
                if not current:raise HTTPException(404,'Ingrediente não encontrado.')
            duplicate=conn.execute('SELECT id FROM ingredients320 WHERE professional_id=? AND lower(name)=lower(?) AND id!=?',(store['id'],name,ingredient_id)).fetchone()
            if duplicate:return RedirectResponse('/painel?erro=ingrediente-duplicado#ingredientes320',303)
            image=g['save_image'](photo) if photo and photo.filename else (current['image_filename'] if current else '')
            if current:conn.execute('UPDATE ingredients320 SET name=?,image_filename=? WHERE id=? AND professional_id=?',(name,image,ingredient_id,store['id']))
            else:conn.execute('INSERT INTO ingredients320(professional_id,name,image_filename) VALUES(?,?,?)',(store['id'],name,image))
            conn.commit()
        finally:conn.close()
        return RedirectResponse('/painel?ok=ingrediente#ingredientes320',303)
