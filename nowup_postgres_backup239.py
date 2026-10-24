"""Native PostgreSQL backup tools: credentials are passed through environment."""
import hashlib
import json
import os
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
        references=set();counts={}
        for table in tables:
            counts[table]=conn.execute(sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier(table))).fetchone()[0]
            columns=[r[0] for r in conn.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=%s AND column_name LIKE '%%filename%%'",(table,))]
            for column in columns:
                references.update(str(r[0]) for r in conn.execute(sql.SQL('SELECT {} FROM {} WHERE {} IS NOT NULL').format(sql.Identifier(column),sql.Identifier(table),sql.Identifier(column))) if r[0])
        for name in references:
            path=uploads/name
            if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or not path.is_file():
                raise RuntimeError('Há uma imagem cadastrada ausente; backup completo não confirmado')
        result=subprocess.run(['pg_dump','--format=custom','--no-owner','--no-privileges','--snapshot='+snapshot,'--schema='+schema,'--file='+str(dump)],env=native_environment(),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=600)
        if result.returncode:raise RuntimeError('Falha no pg_dump. Confira a versão do cliente, permissões e conexão')
    finally:
        conn.rollback();owner.putconn(conn)
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
