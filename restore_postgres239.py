"""Restore a verified native PostgreSQL backup only into an empty destination."""
import argparse,json,subprocess,tempfile,hashlib
from pathlib import Path


def restore(staged,confirm_empty=False):
    if not confirm_empty:raise ValueError('Confirme um destino NOVO e vazio antes de restaurar')
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict,make_conninfo
    from nowup_database239 import database_url
    from nowup_postgres_backup239 import native_environment
    staged=Path(staged);manifest=json.loads((staged/'manifest.json').read_text())
    if manifest.get('backend')!='postgres':raise ValueError('Este backup não é PostgreSQL')
    with (staged/'database/nowup.dump').open('rb') as source:
        if hashlib.file_digest(source,'sha256').hexdigest()!=manifest['files']['database/nowup.dump']:raise ValueError('Checksum do dump divergente')
    with psycopg.connect(database_url(),autocommit=True) as conn:
        if conn.execute("SELECT 1 FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema') AND table_schema NOT LIKE 'pg_%' LIMIT 1").fetchone():raise ValueError('O destino contém tabelas. Nada foi apagado')
    # Password remains in the environment, not in the process argument list.
    target=make_conninfo(dbname=conninfo_to_dict(database_url())['dbname'])
    result=subprocess.run(['pg_restore','--exit-on-error','--single-transaction','--clean','--if-exists','--no-owner','--no-privileges','--dbname='+target,str(staged/'database/nowup.dump')],env=native_environment(),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=600)
    if result.returncode:raise RuntimeError('Restauração recusada ou interrompida; confira permissões e versão do pg_restore')
    with psycopg.connect(database_url(),autocommit=True) as conn:
        conn.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(manifest.get('schema','public'))))
        for table,expected in manifest.get('row_counts',{}).items():
            actual=conn.execute(sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier(table))).fetchone()[0]
            if actual!=expected:raise ValueError('Contagem divergente na tabela '+table)
    return len(manifest.get('row_counts',{}))


def main():
    from restore_backup import stage_backup
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path,nargs='?')
    parser.add_argument('--staged',type=Path,help='Pasta já conferida por restore_backup.py, inclusive após descriptografia')
    parser.add_argument('--confirm-empty-target',action='store_true')
    args=parser.parse_args()
    if bool(args.archive)==bool(args.staged):parser.error('Informe um ZIP ou --staged, nunca os dois')
    if args.staged:
        count=restore(args.staged,args.confirm_empty_target)
    else:
        with tempfile.TemporaryDirectory(prefix='nowup-pg-restore-') as root:
            staged=Path(root)/'staged';stage_backup(args.archive,staged)
            count=restore(staged,args.confirm_empty_target)
    print(f'Restauração conferida: {count} tabelas. Fotos permanecem na cópia de backup; publique-as no armazenamento da loja antes da troca.')

if __name__=='__main__':main()
