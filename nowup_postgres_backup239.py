"""Native PostgreSQL backup tools: credentials are passed through environment."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import zipfile
from datetime import datetime,timezone
from pathlib import Path


def native_environment():
    from psycopg.conninfo import conninfo_to_dict
    from nowup_database239 import database_url
    info=conninfo_to_dict(database_url())
    env=os.environ.copy()
    for key,value in info.items():env['PG'+('DATABASE' if key=='dbname' else key.upper())]=value
    return env


def create_archive(directory,uploads,hash_file):
    from nowup_database239 import pool
    from psycopg import sql
    if not shutil.which('pg_dump'):raise RuntimeError('Instale pg_dump compatível antes de habilitar backups PostgreSQL')
    directory,uploads=Path(directory),Path(uploads)
    dump=directory/'nowup.dump';owner=pool();conn=owner.getconn()
    try:
        conn.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        snapshot=conn.execute('SELECT pg_export_snapshot()').fetchone()[0]
        schema=conn.execute('SELECT current_schema()').fetchone()[0]
        tables=[r[0] for r in conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema=current_schema() AND table_type='BASE TABLE'")]
        from nowup_media247 import references as public_references
        references=public_references(conn,native=True);counts={}
        for table in tables:
            counts[table]=conn.execute(sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier(table))).fetchone()[0]
        # Materialize the durable copies from the SAME exported snapshot used
        # by pg_dump. Private order receipts remain inside the dump only.
        import base64
        staged=directory/'media247';staged.mkdir(mode=0o700)
        if 'nowup_public_media245' in tables:
            for row in conn.execute('SELECT filename,body,digest FROM nowup_public_media245'):
                name,encoded,digest=row[0],row[1],row[2]
                if not re.fullmatch(r'[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp|gif)',name,re.I):raise RuntimeError('Nome de imagem persistida inválido')
                data=base64.b64decode(encoded,validate=True)
                if hashlib.sha256(data).hexdigest()!=digest:raise RuntimeError('Imagem persistida falhou na integridade')
                (staged/name).write_bytes(data)
        deleted=set()
        if 'nowup_deleted_media247' in tables:deleted={r[0] for r in conn.execute('SELECT filename FROM nowup_deleted_media247')}
        for source in uploads.rglob('*'):
            if source.is_symlink():raise RuntimeError('Link simbólico na pasta de fotos')
            if not source.is_file() or source.name in deleted:continue
            relative=source.relative_to(uploads)
            if len(relative.parts)!=1:raise RuntimeError('Subpasta de imagens não suportada')
            target=staged/relative
            if not target.exists():
                before=source.stat();shutil.copyfile(source,target);after=source.stat()
                if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):raise RuntimeError('Imagem mudou durante o backup')
        for name in references:
            if Path(name).name!=name or name in deleted or not (staged/name).is_file():
                raise RuntimeError('Há uma imagem cadastrada ausente; backup completo não confirmado')
        result=subprocess.run(['pg_dump','--format=custom','--no-owner','--no-privileges','--snapshot='+snapshot,'--schema='+schema,'--file='+str(dump)],env=native_environment(),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=600)
        if result.returncode:raise RuntimeError('Falha no pg_dump. Confira a versão do cliente, permissões e conexão')
    finally:
        conn.rollback();owner.putconn(conn)
    uploads=staged
    manifest={'format':'nowup-backup-v2','backend':'postgres','schema':schema,'created_at':datetime.now(timezone.utc).isoformat(),'database':'database/nowup.dump','row_counts':counts,'files':{'database/nowup.dump':hash_file(dump)}}
    archive=directory/'nowup-backup.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,allowZip64=True) as zipped:
        zipped.write(dump,'database/nowup.dump')
        for path in sorted(uploads.rglob('*')):
            if path.is_symlink():raise RuntimeError('A pasta de fotos contém um link simbólico não permitido')
            if not path.is_file():continue
            entry='uploads/'+path.relative_to(uploads).as_posix();before=path.stat();digest=hashlib.sha256()
            with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW),'rb') as src,zipped.open(entry,'w',force_zip64=True) as dst:
                for chunk in iter(lambda:src.read(1024*1024),b''):digest.update(chunk);dst.write(chunk)
            after=path.stat()
            if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):raise RuntimeError('Uma imagem mudou durante o backup; tente novamente')
            manifest['files'][entry]=digest.hexdigest()
        zipped.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False))
    archive.chmod(0o600)
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip():raise RuntimeError('Backup PostgreSQL danificado')
    return archive
