"""Copy a consistent SQLite snapshot into an EMPTY PostgreSQL database.

Credentials come from DATABASE_URL, never command-line arguments. This tool does
not change the source, publish code, enable PostgreSQL, or overwrite target data.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path


def canonical(value):
    if isinstance(value,(bytes,bytearray,memoryview)):
        return {'bytes':base64.b64encode(bytes(value)).decode()}
    return value


def digest_rows(rows):
    digest=hashlib.sha256();count=0
    for row in rows:
        digest.update(json.dumps([canonical(v) for v in row],ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())
        digest.update(b'\n');count+=1
    return count,digest.hexdigest()


def migrate(source_path, report_path=None):
    import psycopg
    from psycopg import sql
    from nowup_database239 import PostgresConnection, database_url, row_factory, finalize_postgres_constraints, initialize_postgres_helpers, close_pool
    source_path=Path(source_path).resolve()
    if not source_path.is_file():raise ValueError('Banco SQLite de origem não encontrado')
    if os.getenv('NOWUP_DB_ENGINE','sqlite')!='postgres':
        raise ValueError('Use NOWUP_DB_ENGINE=postgres apenas no processo de migração')
    report={'tables':{},'verified':False}
    with tempfile.TemporaryDirectory(prefix='nowup-migrate-') as temporary:
        source=sqlite3.connect(source_path.as_uri()+'?mode=ro',uri=True)
        snapshot=sqlite3.connect(Path(temporary)/'snapshot.db')
        try:source.backup(snapshot)
        finally:source.close()
        try:
            report['sqlite_snapshot_sha256']=hashlib.sha256((Path(temporary)/'snapshot.db').read_bytes()).hexdigest()
            if snapshot.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLite não passou na verificação de integridade')
            if snapshot.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('Há referências inválidas na origem. Corrija antes de migrar')
            definitions=snapshot.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
            raw=psycopg.connect(database_url(),autocommit=True,row_factory=row_factory,prepare_threshold=None)
            destination=PostgresConnection(raw)
            try:
                if raw.execute("SELECT 1 FROM information_schema.tables WHERE table_schema=current_schema() LIMIT 1").fetchone():
                    raise ValueError('Destino não está vazio; migração recusada sem apagar dados')
                # Helpers contain no application data. The table/data transaction is atomic.
                initialize_postgres_helpers(raw)
                destination.execute('BEGIN')
                for table,ddl in definitions:destination.execute(ddl)
                for table,_ in definitions:
                    info=snapshot.execute('PRAGMA table_info("'+table.replace('"','""')+'")').fetchall()
                    names=[r[1] for r in info]
                    fields=sql.SQL(',').join(map(sql.Identifier,names))
                    reader=snapshot.execute('SELECT * FROM "'+table.replace('"','""')+'"')
                    batch_size=min(100,max(1,60000//len(names)))
                    while True:
                        batch=reader.fetchmany(batch_size)
                        if not batch:break
                        row_sql=sql.SQL('(')+sql.SQL(',').join(sql.Placeholder() for _ in names)+sql.SQL(')')
                        statement=sql.SQL('INSERT INTO {} ({}) VALUES ').format(sql.Identifier(table),fields)+sql.SQL(',').join(row_sql for _ in batch)
                        raw.execute(statement,[value for row in batch for value in row])
                    primary=[r[1] for r in sorted(info,key=lambda r:r[5]) if r[5]] or names
                    order=', '.join('"'+name.replace('"','""')+'" ASC NULLS FIRST' for name in primary)
                    expected=digest_rows(snapshot.execute('SELECT * FROM "'+table.replace('"','""')+'" ORDER BY '+order))
                    actual=digest_rows(raw.execute(sql.SQL('SELECT {} FROM {} ORDER BY '+order).format(fields,sql.Identifier(table))))
                    if actual!=expected:raise ValueError('Contagem ou checksum divergente na tabela '+table)
                    report['tables'][table]={'rows':actual[0],'sha256':actual[1]}
                for name,ddl in snapshot.execute("SELECT name,sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY name"):
                    destination.execute(ddl)
                finalize_postgres_constraints(destination)
                destination.commit();report['verified']=True
            except Exception:
                destination.rollback();raise
            finally:destination.close()
        finally:snapshot.close()
    if report_path:
        output=Path(report_path);output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2));output.chmod(0o600)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--report',type=Path,default=Path('migration-report239.json'))
    args=parser.parse_args()
    report=migrate(args.source,args.report)
    print(f"Migração verificada: {len(report['tables'])} tabelas; {sum(t['rows'] for t in report['tables'].values())} registros. Origem preservada. O site ainda não foi trocado.")

if __name__=='__main__':main()
