"""Private, encrypted off-site backups. No production restore endpoint."""
from __future__ import annotations
import base64, hashlib, json, os, shutil, sqlite3, tempfile, threading, time, zipfile, fcntl
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

router = APIRouter()
_stop = threading.Event()
_thread = None
_auth = None
_db = None
_uploads = None
_local = threading.Lock()
ZONE = ZoneInfo('America/Sao_Paulo')
MAGIC = b'NOWUP71\x00'

def configure(authorize, database, uploads):
    global _auth, _db, _uploads
    _auth, _db, _uploads = authorize, Path(database), Path(uploads)

def storage_dir():
    p = Path(os.getenv('NOWUP_BACKUP_STATE_DIR', str(_db.parent / 'backup-control')))
    p.mkdir(parents=True, exist_ok=True, mode=0o700)
    return p

def state():
    try:
        return json.loads((storage_dir() / 'status.json').read_text())
    except (OSError, ValueError):
        return {}

def save_state(**values):
    data = state(); data.update(values)
    p = storage_dir() / 'status.json'
    temporary = p.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False))
    os.chmod(temporary, 0o600); os.replace(temporary, p)

@contextmanager
def backup_lock():
    if not _local.acquire(blocking=False):
        raise RuntimeError('Já existe um backup em andamento.')
    try:
        with (storage_dir() / 'backup.lock').open('a') as lock:
            try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise RuntimeError('Já existe um backup em andamento.')
            try: yield
            finally: fcntl.flock(lock, fcntl.LOCK_UN)
    finally: _local.release()

def encryption_key():
    try: key = base64.b64decode(os.environ['NOWUP_BACKUP_ENCRYPTION_KEY'], validate=True)
    except (KeyError, ValueError): raise RuntimeError('Configure uma chave de criptografia válida.')
    if len(key) != 32: raise RuntimeError('A chave de criptografia deve ter 32 bytes.')
    return key

def missing_config():
    keys = ['NOWUP_BACKUP_S3_ENDPOINT','NOWUP_BACKUP_S3_BUCKET','NOWUP_BACKUP_S3_ACCESS_KEY','NOWUP_BACKUP_S3_SECRET_KEY','NOWUP_BACKUP_ENCRYPTION_KEY']
    return [key for key in keys if not os.getenv(key)]

def s3_client():
    if missing_config(): raise RuntimeError('Armazenamento externo ainda não configurado.')
    encryption_key()
    endpoint = os.environ['NOWUP_BACKUP_S3_ENDPOINT']
    parsed = urlparse(endpoint)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise RuntimeError('O endereço do armazenamento deve usar HTTPS.')
    import boto3
    from botocore.config import Config
    return boto3.client('s3', endpoint_url=endpoint,
        aws_access_key_id=os.environ['NOWUP_BACKUP_S3_ACCESS_KEY'],
        aws_secret_access_key=os.environ['NOWUP_BACKUP_S3_SECRET_KEY'],
        region_name=os.getenv('NOWUP_BACKUP_S3_REGION','auto'),
        config=Config(connect_timeout=15,read_timeout=90,retries={'max_attempts':3,'mode':'standard'}))

def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''): digest.update(chunk)
    return digest.hexdigest()

def create_archive(directory):
    directory=Path(directory)
    if not _db.is_file() or not _uploads.is_dir():
        raise RuntimeError('Banco de dados ou pasta de fotos não encontrados. Confira os caminhos.')
    snapshot=directory/'nowup.db'
    source=sqlite3.connect(_db.resolve().as_uri()+'?mode=ro',uri=True,timeout=30)
    destination=sqlite3.connect(snapshot)
    try:
        deadline=time.monotonic()+180
        def progress(*_):
            if time.monotonic()>deadline: raise RuntimeError('Tempo de cópia do banco excedido.')
        source.backup(destination,pages=256,progress=progress,sleep=0.05)
        if destination.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise RuntimeError('A cópia do banco não passou na verificação de integridade.')
        # All upload filename columns in the DB snapshot must be present.
        referenced=set()
        tables=[r[0] for r in destination.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for table in tables:
            quoted='"'+table.replace('"','""')+'"'
            columns=[r[1] for r in destination.execute('PRAGMA table_info('+quoted+')') if 'filename' in r[1]]
            for column in columns:
                col='"'+column.replace('"','""')+'"'
                referenced.update(str(r[0]) for r in destination.execute('SELECT '+col+' FROM '+quoted) if r[0])
    finally: destination.close(); source.close()
    files={}
    for name in referenced:
        p=_uploads/name
        if Path(name).is_absolute() or '..' in Path(name).parts or p.is_symlink() or not p.is_file():
            raise RuntimeError('Há uma imagem cadastrada ausente ou inválida; backup completo não confirmado.')
    for p in _uploads.rglob('*'):
        if p.is_symlink(): raise RuntimeError('A pasta de fotos contém um link simbólico não permitido.')
        if p.is_file(): files[p.relative_to(_uploads).as_posix()]=p
    archive=directory/'nowup-backup.zip'
    manifest={'format':'nowup-backup-v1','created_at':datetime.now(timezone.utc).isoformat(),'database':'database/nowup.db','files':{}}
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,allowZip64=True) as z:
        z.write(snapshot,'database/nowup.db');manifest['files']['database/nowup.db']=sha256(snapshot)
        for name,p in sorted(files.items()):
            entry='uploads/'+name
            before=p.stat()
            # Copy stable bytes once, hash exactly the bytes placed in the archive.
            digest=hashlib.sha256()
            fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
            with os.fdopen(fd,'rb') as src, z.open(entry,'w',force_zip64=True) as dst:
                for chunk in iter(lambda:src.read(1024*1024),b''):digest.update(chunk);dst.write(chunk)
            after=p.stat()
            if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):
                raise RuntimeError('Uma foto mudou durante a cópia. Tente novamente.')
            manifest['files'][entry]=digest.hexdigest()
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False))
    os.chmod(archive,0o600)
    with zipfile.ZipFile(archive) as z:
        if z.testzip(): raise RuntimeError('Arquivo de backup inválido.')
    return archive

def encrypt_archive(source,target,key):
    from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
    nonce=os.urandom(12);header=MAGIC+nonce
    encryptor=Cipher(algorithms.AES(key),modes.GCM(nonce)).encryptor()
    encryptor.authenticate_additional_data(header)
    with Path(source).open('rb') as src,Path(target).open('wb') as dst:
        dst.write(header)
        for chunk in iter(lambda:src.read(1024*1024),b''):dst.write(encryptor.update(chunk))
        dst.write(encryptor.finalize());dst.write(encryptor.tag)
    os.chmod(target,0o600)

def decrypt_archive(source,target,key):
    from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
    size=Path(source).stat().st_size
    if size<len(MAGIC)+12+16: raise ValueError('Backup incompleto.')
    try:
        with Path(source).open('rb') as src,Path(target).open('wb') as dst:
            header=src.read(len(MAGIC)+12)
            if not header.startswith(MAGIC):raise ValueError('Formato de backup desconhecido.')
            src.seek(-16,2);tag=src.read(16);src.seek(len(header))
            decryptor=Cipher(algorithms.AES(key),modes.GCM(header[len(MAGIC):],tag)).decryptor()
            decryptor.authenticate_additional_data(header)
            remaining=size-len(header)-16
            while remaining:
                chunk=src.read(min(1024*1024,remaining));remaining-=len(chunk);dst.write(decryptor.update(chunk))
            dst.write(decryptor.finalize())
        os.chmod(target,0o600)
    except Exception:
        Path(target).unlink(missing_ok=True);raise

def prefix():
    value=os.getenv('NOWUP_BACKUP_S3_PREFIX','nowup-backups').strip('/')
    if not value or '..' in value.split('/'):raise RuntimeError('Prefixo de backup inválido.')
    return value

def prune_remote(client,bucket,category,keep):
    base=prefix()+'/'+category+'/'
    objects=[]
    for page in client.get_paginator('list_objects_v2').paginate(Bucket=bucket,Prefix=base):
        objects.extend(obj for obj in page.get('Contents',[]) if obj['Key'].endswith('.zip.enc'))
    objects.sort(key=lambda obj:obj['Key'],reverse=True)
    for obj in objects[keep:]:client.delete_object(Bucket=bucket,Key=obj['Key'])

def upload_backup(client,bucket,path,key):
    digest=sha256(path)
    client.upload_file(str(path),bucket,key,ExtraArgs={'ContentType':'application/octet-stream','Metadata':{'sha256':digest}})
    remote=client.head_object(Bucket=bucket,Key=key)
    if remote['ContentLength']!=path.stat().st_size or remote.get('Metadata',{}).get('sha256')!=digest:
        raise RuntimeError('Não foi possível confirmar o envio do backup.')

def external_backup():
    with backup_lock():
        save_state(running=True,last_attempt=datetime.now(timezone.utc).isoformat(),error='')
        try:
            client=s3_client();bucket=os.environ['NOWUP_BACKUP_S3_BUCKET'];now=datetime.now(ZONE)
            with tempfile.TemporaryDirectory(prefix='nowup-backup-') as directory:
                archive=create_archive(directory);encrypted=Path(directory)/'backup.zip.enc'
                encrypt_archive(archive,encrypted,encryption_key())
                key=prefix()+'/daily/'+now.strftime('%Y-%m-%d')+'.zip.enc'
                upload_backup(client,bucket,encrypted,key)
                week=now.strftime('%G-W%V')
                if state().get('last_week')!=week:
                    upload_backup(client,bucket,encrypted,prefix()+'/weekly/'+week+'.zip.enc')
                save_state(last_external=now.isoformat(),last_daily=now.date().isoformat(),last_week=week,external_key=key,bytes=encrypted.stat().st_size)
            # Retention only follows successful upload confirmation.
            try:prune_remote(client,bucket,'daily',7);prune_remote(client,bucket,'weekly',4)
            except Exception:save_state(warning='Cópia enviada, mas a limpeza de versões antigas falhou.')
            else:save_state(warning='')
        except Exception:
            # No provider credentials or exception payloads in status/logs.
            save_state(error='Backup externo falhou. Confira caminhos, imagens e configuração do armazenamento. Tente novamente.')
            notify_failure()
            raise
        finally:save_state(running=False)

def notify_failure():
    email=os.getenv('NOWUP_BACKUP_NOTIFY_EMAIL') or os.getenv('NOWUP_ADMIN_EMAIL','')
    day=datetime.now(ZONE).date().isoformat()
    if not email or email.endswith('.local') or state().get('last_alert_day')==day:return
    try:
        from mailing import send_email
        if send_email(email,'Administrador NowUp','NowUp: falha no backup externo','<p>O envio do backup externo falhou. Entre no painel administrativo e consulte Backups. A última cópia confirmada não foi substituída por uma cópia incompleta.</p>'):
            save_state(last_alert_day=day)
    except Exception:pass

def automatic_enabled():return os.getenv('NOWUP_BACKUP_ENABLED','0')=='1'

def loop():
    while not _stop.is_set():
        try:
            now=datetime.now(ZONE)
            if automatic_enabled() and now.hour>=3 and state().get('last_daily')!=now.date().isoformat():external_backup()
        except Exception:pass
        _stop.wait(3600)

def start():
    global _thread
    if _thread and _thread.is_alive():return
    _stop.clear();_thread=threading.Thread(target=loop,name='nowup-backup',daemon=True);_thread.start()

def stop():_stop.set()

def authorize(request,write=False):
    _auth(request,'admin')
    if write:
        origin=request.headers.get('origin') or request.headers.get('referer','')
        parsed=urlparse(origin)
        if not origin or parsed.netloc!=request.headers.get('host'):
            raise HTTPException(403,'Origem da solicitação não permitida.')

@router.get('/admin/backups/status')
def status(request:Request):
    authorize(request)
    result=state()
    result['configured']=not missing_config();result['automatic']=automatic_enabled()
    result['running']=_local.locked()
    return JSONResponse(result,headers={'Cache-Control':'no-store'})

@router.post('/admin/backups/enviar')
def trigger(request:Request):
    authorize(request,True)
    if missing_config():raise HTTPException(400,'Configure o armazenamento externo antes de enviar.')
    if _local.locked():raise HTTPException(409,'Já existe um backup em andamento.')
    def run():
        try:external_backup()
        except Exception:pass
    threading.Thread(target=run,name='nowup-backup-manual',daemon=True).start()
    return {'message':'Envio solicitado. Aguarde a confirmação no painel.'}

@router.post('/admin/backups/baixar')
def download(request:Request):
    authorize(request,True)
    directory=Path(tempfile.mkdtemp(prefix='nowup-download-'))
    try:
        with backup_lock():archive=create_archive(directory)
    except Exception as exc:
        shutil.rmtree(directory)
        raise HTTPException(409,'Não foi possível gerar a cópia completa. Confira os caminhos e as imagens cadastradas.') from exc
    return FileResponse(archive,filename='NOWUP-BACKUP-'+datetime.now(ZONE).strftime('%Y%m%d-%H%M%S')+'.zip',media_type='application/zip',headers={'Cache-Control':'no-store'},background=BackgroundTask(shutil.rmtree,directory))
