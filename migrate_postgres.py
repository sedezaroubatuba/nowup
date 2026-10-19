"""Copy a verified SQLite snapshot into an EMPTY PostgreSQL database atomically.
Never changes source. Destination URL is read from DATABASE_URL, never printed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from nowup_database import connect, convert, postgres_enabled, TEMPORAL_SQL

def quote(name): return '"'+name.replace('"','""')+'"'

def migrate(source, manifest=None):
    if not postgres_enabled(): raise ValueError('Configure DATABASE_URL no ambiente de teste.')
    source=Path(source).resolve()
    if not source.is_file(): raise ValueError('Snapshot SQLite não encontrado.')
    if manifest:
        data=json.loads(Path(manifest).read_text())
        if data.get('files',{}).get('database/nowup.db')!=hashlib.sha256(source.read_bytes()).hexdigest():
            raise ValueError('O banco não confere com o manifesto do backup.')
    src=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
    dst=connect()
    try:
        src.execute('BEGIN')
        if src.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]:raise ValueError('Snapshot corrompido.')
        if src.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('Snapshot contém referências inválidas.')
        pg=dst.raw
        pg.execute('SELECT pg_advisory_xact_lock(223001)')
        if pg.execute("SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' LIMIT 1").fetchone():
            raise ValueError('Destino não está vazio. Nada foi importado; use um banco de teste vazio.')
        pg.execute(TEMPORAL_SQL)
        tables=src.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        # Foreign keys added and validated after rows, supporting any table order.
        import sqlglot
        from sqlglot import exp
        foreign=[]
        for table,ddl in tables:
            tree=sqlglot.parse_one(convert(ddl),read='postgres')
            schema=tree.this
            kept=[]
            for item in schema.expressions:
                if isinstance(item,exp.ForeignKey):continue
                if isinstance(item,exp.ColumnDef):
                    item.set('constraints',[c for c in item.constraints if not isinstance(c.kind,exp.Reference)])
                kept.append(item)
            schema.set('expressions',kept)
            pg.execute(tree.sql(dialect='postgres'))
            grouped={}
            for row in src.execute('PRAGMA foreign_key_list('+quote(table)+')'):
                grouped.setdefault(row[0],[]).append(row)
            for fid,rows in grouped.items():foreign.append((table,fid,sorted(rows,key=lambda r:r[1])))
        sequence_values=dict(src.execute("SELECT name,seq FROM sqlite_sequence")) if src.execute("SELECT 1 FROM sqlite_master WHERE name='sqlite_sequence'").fetchone() else {}
        counts={}
        for table,_ in tables:
            cols=[r[1] for r in src.execute('PRAGMA table_info('+quote(table)+')')]
            names=','.join(map(quote,cols))
            # COPY streaming keeps secrets out of logs and uses bounded memory.
            with pg.cursor().copy('COPY '+quote(table)+' ('+names+') FROM STDIN') as cp:
                for row in src.execute('SELECT '+names+' FROM '+quote(table)):cp.write_row(row)
            n=src.execute('SELECT count(*) FROM '+quote(table)).fetchone()[0]
            if pg.execute('SELECT count(*) FROM '+quote(table)).fetchone()[0]!=n:raise ValueError('Contagem divergente na importação.')
            # Verify every typed row, not just counts (tables all have a PK).
            def digest(rows):
                h=hashlib.sha256()
                for row in rows:h.update((json.dumps(list(row),ensure_ascii=False,separators=(',',':'),default=lambda v: {'bytes':bytes(v).hex()} if isinstance(v,(bytes,bytearray,memoryview)) else str(v))+'\n').encode())
                return h.digest()
            pk=[r[1] for r in sorted(src.execute('PRAGMA table_info('+quote(table)+')'),key=lambda r:r[5]) if r[5]]
            order=','.join(map(quote,pk or cols))
            query='SELECT '+names+' FROM '+quote(table)+' ORDER BY '+order
            if digest(src.execute(query))!=digest(pg.execute(query)):raise ValueError('Conteúdo divergente na importação: '+table)
            counts[table]=n
            for col in cols:
                seq=pg.execute('SELECT pg_get_serial_sequence(%s,%s)',(quote(table),col)).fetchone()[0]
                if seq:
                    maximum=pg.execute('SELECT max('+quote(col)+') FROM '+quote(table)).fetchone()[0]
                    maximum=max(maximum or 0,sequence_values.get(table,0))
                    pg.execute('SELECT setval(%s,%s,%s)',(seq,max(1,maximum),maximum>=1))
        for table,fid,rows in foreign:
            cols=','.join(quote(r[3]) for r in rows)
            ref=','.join(quote(r[4]) for r in rows)
            update,delete=rows[0][5],rows[0][6]
            allowed={'NO ACTION','RESTRICT','SET NULL','SET DEFAULT','CASCADE'}
            if update not in allowed or delete not in allowed:raise ValueError('Ação de referência desconhecida.')
            pg.execute('ALTER TABLE '+quote(table)+' ADD CONSTRAINT '+quote('fk223_'+table+'_'+str(fid))+' FOREIGN KEY ('+cols+') REFERENCES '+quote(rows[0][2])+' ('+ref+') ON UPDATE '+update+' ON DELETE '+delete)
        for (ddl,) in src.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"):
            pg.execute(convert(ddl))
        dst.commit()
        return counts
    except BaseException:
        dst.rollback();raise
    finally:dst.close();src.close()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('snapshot',type=Path)
    p.add_argument('--manifest',type=Path)
    p.add_argument('--confirm-empty-test-database',action='store_true',required=True)
    args=p.parse_args()
    try:
        counts=migrate(args.snapshot,args.manifest)
    except ValueError as exc:print(str(exc),file=sys.stderr);return 1
    except Exception:print('Importação interrompida e revertida. Nenhum dado foi confirmado no destino. Consulte o diagnóstico em ambiente privado.',file=sys.stderr);return 1
    print('Importação confirmada:',len(counts),'tabelas;',sum(counts.values()),'registros verificados. Origem preservada.')
    return 0
if __name__=='__main__':raise SystemExit(main())
