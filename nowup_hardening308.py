"""Public asset boundaries, safe photo writes and non-sensitive storage diagnostics."""
import io
import json
import logging
import os
import secrets
import shutil
from pathlib import Path
from fastapi import HTTPException
from starlette.staticfiles import StaticFiles
from PIL import Image, ImageOps
from starlette.responses import JSONResponse

class RequestLimit308:
    """Bound multipart/JSON uploads, including requests without Content-Length."""
    def __init__(self,app,limit=25*1024*1024):self.app=app;self.limit=limit
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        headers=dict(scope.get('headers',[]))
        try:length=int(headers.get(b'content-length',b'0'))
        except ValueError:length=-1
        if length<0 or length>self.limit:
            return await JSONResponse({'detail':'Envio acima do limite permitido.'},status_code=413,headers={'Cache-Control':'no-store'})(scope,receive,send)
        total=0
        async def bounded():
            nonlocal total
            message=await receive();total+=len(message.get('body',b''))
            if total>self.limit:raise HTTPException(413,'Envio acima do limite permitido.')
            return message
        return await self.app(scope,bounded,send)

class PublicFiles(StaticFiles):
    def __init__(self,*args,images_only=False,**kwargs):
        super().__init__(*args,**kwargs);self.images_only=images_only

    async def get_response(self,path,scope):
        parts=Path(path).parts
        extensions={'.jpg','.jpeg','.png','.webp','.gif','.ico','.svg'}
        if not self.images_only:extensions|={'.js','.css','.html','.json','.webmanifest','.woff','.woff2','.ttf','.mp3','.wav','.ogg','.mp4'}
        if any(p.startswith('.') or p=='__pycache__' for p in parts) or Path(path).suffix.lower() not in extensions:
            raise HTTPException(404,'Arquivo não encontrado')
        return await super().get_response(path,scope)

def save_photo(upload,directory,limit=5*1024*1024):
    if upload.content_type not in {'image/jpeg','image/png','image/webp'}:raise HTTPException(400,'Formato inválido. Use JPG, PNG ou WebP')
    data=upload.file.read(limit+1)
    if len(data)>limit:raise HTTPException(413,'Imagem maior que 5 MB')
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.format not in ('JPEG','PNG','WEBP') or source.width*source.height>24_000_000:raise ValueError()
            image=ImageOps.exif_transpose(source).convert('RGB');image.thumbnail((1600,1600))
        # Re-encoding strips EXIF/location data. A partial write never becomes public.
        output=io.BytesIO();image.save(output,'JPEG',quality=86,optimize=True)
    except (OSError,ValueError,Image.DecompressionBombError):raise HTTPException(400,'Arquivo não é uma imagem válida ou excede a resolução permitida')
    directory=Path(directory);name=secrets.token_hex(16)+'.jpg';temporary=directory/('.'+name+'.tmp')
    try:
        with temporary.open('xb') as stream:
            stream.write(output.getvalue());stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,directory/name)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise HTTPException(503,'Não foi possível salvar a foto. A imagem anterior foi mantida. Tente novamente.')
    return name

def image_references(conn):
    refs=set()
    for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        table=row[0]
        # Receipts/documents live inside the database, never in public uploads.
        if table in ('order_receipts206','merchant_documents257'):continue
        quoted='"'+table.replace('"','""')+'"'
        columns=[r[1] for r in conn.execute('PRAGMA table_info('+quoted+')') if 'filename' in r[1] or r[1] in ('image','photo')]
        for column in columns:
            field='"'+column.replace('"','""')+'"'
            for value in conn.execute('SELECT '+field+' FROM '+quoted):
                if value[0]:refs.add(str(value[0]).removeprefix('/uploads/'))
    for table,query in [('site_settings',"SELECT value FROM site_settings WHERE key LIKE '%image%filename%'"),('adm227_entities',"SELECT data FROM adm227_entities")]:
        if conn.execute('SELECT 1 FROM sqlite_master WHERE type=\'table\' AND name=?',(table,)).fetchone():
            for row in conn.execute(query):
                if table=='site_settings':
                    if row[0]:refs.add(str(row[0]).removeprefix('/uploads/'))
                else:
                    import re
                    refs.update(re.findall(r'(?:/uploads/)?([A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp))',row[0] or '',re.I))
    return refs

def retire_photos(database,directory,names):
    """Call only after commit. Preserve shared images and fail closed on inspection errors."""
    names={n for n in names if n}
    if not names:return
    conn=database()
    try:
        conn.execute('BEGIN IMMEDIATE')
        refs=image_references(conn)
        for name in names-refs:
            path=Path(directory)/name
            if Path(name).name==name and not path.is_symlink():path.unlink(missing_ok=True)
        conn.commit()
    except Exception:logging.getLogger(__name__).warning('Photo cleanup deferred; files preserved')
    finally:conn.close()

def storage_status(database,directory):
    conn=database()
    try:
        refs=image_references(conn);root=Path(directory)
        missing=sum(not (root/name).is_file() for name in refs)
        space=shutil.disk_usage(root)
        return {'referenced_photos':len(refs),'missing_photos':missing,'uploads_on_persistent_disk':root.resolve().is_relative_to('/app/persist'),
            'database_on_persistent_disk':Path(conn.execute('PRAGMA database_list').fetchone()[2]).resolve().is_relative_to('/app/persist'),
            'free_mb':space.free//1048576,'database_ok':conn.execute('PRAGMA quick_check').fetchone()[0]=='ok'}
    finally:conn.close()

def log_storage(database,directory):
    try:
        import nowup_backup
        status=storage_status(database,directory);backup=nowup_backup.state()
        status.update(backup_configured=not nowup_backup.missing_config(),backup_automatic=nowup_backup.automatic_enabled(),backup_last_success=backup.get('last_external',''),backup_error=bool(backup.get('error')),backup_running=bool(backup.get('running')))
        logging.getLogger('uvicorn.error').info('NowUp storage audit308 %s',json.dumps(status))
    except Exception:logging.getLogger('uvicorn.error').warning('NowUp storage audit308 unavailable')
