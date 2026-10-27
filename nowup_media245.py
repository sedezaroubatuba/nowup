"""Durable public upload copies. Image recovery never restores business tables."""
import base64
import hashlib
import io
import re
import tempfile
import zipfile
from pathlib import Path
from PIL import Image
from fastapi import HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

NAME = re.compile(r'^[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp|gif)$', re.I)
TABLE = 'nowup_public_media245'
HOST = 'nowup-teste-adm-v227.onrender.com'

def validated(name, data):
    if not NAME.fullmatch(name) or len(data)>8*1024*1024:
        raise ValueError('Imagem fora dos limites')
    with Image.open(io.BytesIO(data)) as image:
        if image.format not in ('JPEG','PNG','WEBP','GIF') or image.width*image.height>24_000_000:
            raise ValueError('Formato de imagem inválido')
        image.verify()
    return hashlib.sha256(data).hexdigest()

def put(conn, name, data):
    digest=validated(name,data)
    conn.execute(f'''INSERT INTO {TABLE}(filename,body,digest) VALUES(?,?,?)
        ON CONFLICT(filename) DO UPDATE SET body=excluded.body,digest=excluded.digest''',
        (name,base64.b64encode(data).decode('ascii'),digest))

def install(app, require_user, db, directory):
    directory=Path(directory)
    def initialize():
        conn=db()
        try:
            from nowup_media247 import initialize as init247
            init247(conn)
            conn.commit()
        finally: conn.close()
    app.router.on_startup.insert(0,initialize)

    class DurableFiles(StaticFiles):
        async def get_response(self,path,scope):
            if NAME.fullmatch(path):
                def deleted():
                    conn=db()
                    try:return bool(conn.execute('SELECT 1 FROM nowup_deleted_media247 WHERE filename=?',(path,)).fetchone())
                    finally:conn.close()
                if await run_in_threadpool(deleted):raise HTTPException(404)
            try:
                response=await super().get_response(path,scope)
                if response.status_code!=404:return response
            except HTTPException as error:
                if error.status_code!=404:raise
            except Exception as error:
                # Starlette raises its base HTTPException for absent files.
                if getattr(error,'status_code',None)!=404:raise
            if not NAME.fullmatch(path):raise HTTPException(404)
            def read():
                conn=db()
                try:return conn.execute(f'SELECT body,digest FROM {TABLE} WHERE filename=?',(path,)).fetchone()
                finally:conn.close()
            row=await run_in_threadpool(read)
            if not row:raise HTTPException(404)
            data=base64.b64decode(row['body'],validate=True)
            if hashlib.sha256(data).hexdigest()!=row['digest']:raise HTTPException(503,'Imagem indisponível')
            kind=Image.open(io.BytesIO(data)).format.lower().replace('jpg','jpeg')
            return Response(data,media_type='image/'+kind,headers={'Cache-Control':'public, max-age=0, must-revalidate','X-Content-Type-Options':'nosniff'})
    for route in app.routes:
        if getattr(route,'path',None)=='/uploads':route.app=DurableFiles(directory=directory)

    def authorize(request):
        if request.url.hostname!=HOST:raise HTTPException(404)
        require_user(request,'admin')
    @app.get('/admin/recuperar-fotos',response_class=HTMLResponse)
    def form(request:Request):
        authorize(request)
        return HTMLResponse('''<!doctype html><html lang="pt-BR"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Recuperar fotos</title><body style="font:18px sans-serif;max-width:600px;margin:30px auto;padding:20px"><h1>Recuperar fotos no teste</h1><p>Selecione o backup completo original (.zip). Somente as imagens serão recuperadas. Lojas, produtos e pedidos não serão importados novamente.</p><form method="post" enctype="multipart/form-data"><input required type="file" name="backup" accept=".zip"><p><button style="padding:18px;background:#7426b9;color:white;border:0;border-radius:12px">Recuperar somente as fotos</button></p></form><p>Aguarde o resultado sem reenviar.</p></body></html>''',headers={'Cache-Control':'no-store'})
    @app.post('/admin/recuperar-fotos')
    def recover(request:Request,backup:UploadFile=File(...)):
        authorize(request)
        if request.headers.get('origin')!='https://'+HOST:raise HTTPException(403,'Origem inválida')
        with tempfile.TemporaryDirectory(prefix='nowup-images245-') as temp:
            archive=Path(temp)/'backup.zip'
            total=0
            with archive.open('wb') as output:
                while chunk:=backup.file.read(1024*1024):
                    total+=len(chunk)
                    if total>64*1024*1024:raise HTTPException(413,'Backup maior que 64 MB')
                    output.write(chunk)
            try:
                with zipfile.ZipFile(archive) as z:
                    if len(z.infolist())>5000 or sum(i.file_size for i in z.infolist())>256*1024*1024:raise ValueError('ZIP fora dos limites')
                from restore_backup import stage_backup
                staged=Path(temp)/'staged';stage_backup(archive,staged)
                photos=list((staged/'uploads').rglob('*'))
                photos=[p for p in photos if p.is_file()]
                demos={'demo-burger.svg','demo-caicara.svg','demo-quiosque.svg','demo-pizza.svg'}
                photos=[p for p in photos if p.name not in demos]
                # Reject unknown/nested files rather than publish arbitrary backup content.
                for p in photos:
                    if p.parent!=staged/'uploads':raise ValueError('Caminho inválido')
                    validated(p.name,p.read_bytes())
            except Exception:raise HTTPException(400,'Backup inválido ou contém arquivo que não é imagem pública. Nenhum dado importado.')
            conn=db()
            try:
                for p in photos:
                    data=p.read_bytes();digest=validated(p.name,data)
                    old=conn.execute(f'SELECT digest FROM {TABLE} WHERE filename=?',(p.name,)).fetchone()
                    if old and old['digest']!=digest:raise HTTPException(409,'Foto existente diferente do backup. Nenhuma alteração realizada.')
                    local=directory/p.name
                    if local.exists() and (local.is_symlink() or hashlib.sha256(local.read_bytes()).hexdigest()!=digest):raise HTTPException(409,'Foto local diferente do backup. Nenhuma alteração realizada.')
                    put(conn,p.name,data)
                    conn.execute('DELETE FROM nowup_deleted_media247 WHERE filename=?',(p.name,))
                conn.commit()
            except Exception:conn.rollback();raise
            finally:conn.close()
            return {'fotos_recuperadas':len(photos),'dados_de_lojas_e_pedidos_alterados':False,'message':'Fotos guardadas no banco. Volte à loja e atualize a página.'}
