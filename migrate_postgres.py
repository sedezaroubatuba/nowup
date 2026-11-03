"""Importação isolada: nunca escreve no schema public ou no SQLite de origem."""
import argparse
import base64
import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path

from nowup_database239 import translate, database_url


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def fingerprint(rows):
    def value(v):
        if isinstance(v, (bytes, memoryview)):
            return {'bytes': base64.b64encode(bytes(v)).decode()}
        return v
    digests = []
    for row in rows:
        payload = json.dumps([value(v) for v in row], ensure_ascii=False, separators=(',', ':'))
        digests.append(hashlib.sha256(payload.encode()).hexdigest())
    return hashlib.sha256(''.join(sorted(digests)).encode()).hexdigest(), len(digests)


def source_plan(path):
    source = sqlite3.connect(Path(path).resolve(strict=True).as_uri() + '?mode=ro', uri=True)
    source.execute('PRAGMA query_only=ON')
    source.execute('BEGIN')
    try:
        if source.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Banco de origem inválido')
        if source.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Banco de origem contém referências inválidas')
        tables = source.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        plan = []
        for table, ddl in tables:
            rendered, _ = translate(ddl)
            columns = [r[1] for r in source.execute('PRAGMA table_info(' + quote(table) + ')')]
            digest, count = fingerprint(source.execute('SELECT * FROM ' + quote(table)))
            plan.append({'table': table, 'ddl': rendered, 'columns': columns, 'rows': count, 'fingerprint': digest})
        return source, plan
    except BaseException:
        source.close()
        raise


def migrate(path, schema, apply=False):
    if not re.fullmatch(r'nowup_migration_[a-z0-9_]{1,40}', schema):
        raise ValueError('Use um schema novo iniciado por nowup_migration_')
    source, plan = source_plan(path)
    try:
        report = {'mode': 'plan', 'schema': schema, 'tables': len(plan),
                  'rows': sum(t['rows'] for t in plan),
                  'counts': {t['table']: t['rows'] for t in plan}}
        if not apply:
            return report
        import psycopg
        from psycopg import sql
        from nowup_database239 import initialize_postgres_helpers, reset_identity_sequences
        # URL comes exclusively from the environment and is never printed.
        with psycopg.connect(database_url(), autocommit=False) as target:
            with target.transaction():
                target.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
                target.execute(sql.SQL('SET LOCAL search_path TO {}').format(sql.Identifier(schema)))
                initialize_postgres_helpers(target)
                for item in plan:
                    target.execute(item['ddl'])
                for item in plan:
                    table = item['table']
                    columns = item['columns']
                    insert = sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(
                        sql.Identifier(table), sql.SQL(',').join(map(sql.Identifier, columns)),
                        sql.SQL(',').join(sql.Placeholder() for _ in columns))
                    with target.cursor() as cursor:
                        cursor.executemany(insert, source.execute('SELECT * FROM ' + quote(table)))
                    digest, count = fingerprint(target.execute(sql.SQL('SELECT {} FROM {}').format(
                        sql.SQL(',').join(map(sql.Identifier, columns)), sql.Identifier(table))))
                    if count != item['rows'] or digest != item['fingerprint']:
                        raise ValueError('Conteúdo divergente na tabela ' + table)
                # Restore real foreign keys after copying all tables; validation is immediate.
                for item in plan:
                    table = item['table']
                    grouped = {}
                    for row in source.execute('PRAGMA foreign_key_list(' + quote(table) + ')'):
                        grouped.setdefault(row[0], []).append(row)
                    for fid, rows in grouped.items():
                        rows.sort(key=lambda r: r[1])
                        first = rows[0]
                        actions = {'NO ACTION', 'RESTRICT', 'SET NULL', 'SET DEFAULT', 'CASCADE'}
                        if first[5] not in actions or first[6] not in actions:
                            raise ValueError('Ação de referência desconhecida')
                        statement = sql.SQL('ALTER TABLE {} ADD CONSTRAINT {} FOREIGN KEY ({}) REFERENCES {} ({}) ON UPDATE ' + first[5] + ' ON DELETE ' + first[6]).format(
                            sql.Identifier(table), sql.Identifier('migration_fk_' + str(fid) + '_' + table),
                            sql.SQL(',').join(sql.Identifier(r[3]) for r in rows), sql.Identifier(first[2]),
                            sql.SQL(',').join(sql.Identifier(r[4]) for r in rows))
                        target.execute(statement)
                for index, in source.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"):
                    target.execute(translate(index)[0])
                from types import SimpleNamespace
                reset_identity_sequences(SimpleNamespace(raw=target))
                if source.execute("SELECT 1 FROM sqlite_master WHERE name='sqlite_sequence'").fetchone():
                    for table, previous in source.execute('SELECT name,seq FROM sqlite_sequence'):
                        if table not in {item['table'] for item in plan}: continue
                        sequence = target.execute('SELECT pg_get_serial_sequence(%s,%s)', (table, 'id')).fetchone()[0]
                        if sequence and previous:
                            current = target.execute(sql.SQL('SELECT last_value FROM {}').format(sql.Identifier(*sequence.split('.')))).fetchone()[0]
                            target.execute('SELECT setval(%s,%s,true)', (sequence, max(int(current), int(previous))))
            report['mode'] = 'imported_and_verified'
        return report
    finally:
        source.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database')
    parser.add_argument('--schema', required=True)
    parser.add_argument('--apply', action='store_true', help='Importar em schema novo; sem esta flag apenas confere a origem')
    args = parser.parse_args()
    try:
        print(json.dumps(migrate(args.database, args.schema, args.apply), ensure_ascii=False, indent=2))
    except Exception as exc:
        # Avoid exposing DSNs or row values from database exceptions.
        raise SystemExit('Migração interrompida (' + type(exc).__name__ + '). Nenhuma troca de produção foi realizada.')
