"""PostgreSQL logical backup helpers. Credentials stay in environment variables."""
import os
import shutil
import subprocess
from pathlib import Path
from nowup_database import connect

def client_env():
    from psycopg.conninfo import conninfo_to_dict
    settings=conninfo_to_dict(os.environ['DATABASE_URL'])
    env=os.environ.copy()
    # Isolate connection settings from any unrelated shell PG environment.
    for key in list(env):
        if key.startswith('PG'): del env[key]
    mapping={'host':'PGHOST','hostaddr':'PGHOSTADDR','port':'PGPORT','dbname':'PGDATABASE',
             'user':'PGUSER','password':'PGPASSWORD','sslmode':'PGSSLMODE',
             'sslrootcert':'PGSSLROOTCERT','sslcert':'PGSSLCERT','sslkey':'PGSSLKEY',
             'channel_binding':'PGCHANNELBINDING','target_session_attrs':'PGTARGETSESSIONATTRS',
             'service':'PGSERVICE','options':'PGOPTIONS','connect_timeout':'PGCONNECT_TIMEOUT'}
    unknown=set(settings)-set(mapping)
    if unknown: raise RuntimeError('Parâmetro de conexão não suportado pelo backup; ajuste a configuração.')
    for key,value in settings.items():env[mapping[key]]=value
    env['PGCONNECT_TIMEOUT']='10'
    return env

def snapshot(directory):
    if not shutil.which('pg_dump') or not shutil.which('pg_restore'):
        raise RuntimeError('Backup PostgreSQL requer pg_dump e pg_restore compatíveis no servidor.')
    c=connect()
    target=Path(directory)/'nowup.pgdump'
    try:
        c.raw.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        sid=c.raw.execute('SELECT pg_export_snapshot()').fetchone()[0]
        refs=set()
        columns=c.raw.execute("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema='public' AND column_name LIKE '%filename%'").fetchall()
        from psycopg import sql
        for table,column in columns:
            refs.update(str(r[0]) for r in c.raw.execute(sql.SQL('SELECT {} FROM {}').format(sql.Identifier(column),sql.Identifier(table))) if r[0])
        run=subprocess.run(['pg_dump','--format=custom','--no-owner','--no-acl','--snapshot='+sid,'--file='+str(target)],env=client_env(),capture_output=True,timeout=180)
        if run.returncode:raise RuntimeError('Falha no backup PostgreSQL. Confira conexão e versão do pg_dump.')
        check=subprocess.run(['pg_restore','--list',str(target)],capture_output=True,timeout=30)
        if check.returncode:raise RuntimeError('O arquivo PostgreSQL gerado não passou na verificação.')
        os.chmod(target,0o600)
        return target,refs
    finally:c.rollback();c.close()
