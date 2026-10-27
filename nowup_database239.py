"""Explicit database backend selection and a tested bridge for legacy SQLite SQL.

SQLite remains the default. PostgreSQL is opt-in; connection failures never fall
back to a second database. No production credentials are stored in this module.
"""
from __future__ import annotations
import os
import re
import sqlite3
import threading
from functools import lru_cache

_pool = None
_pool_lock = threading.Lock()


def is_postgres():
    engine = os.getenv('NOWUP_DB_ENGINE', 'sqlite').lower()
    if engine not in ('sqlite', 'postgres'):
        raise RuntimeError('NOWUP_DB_ENGINE deve ser sqlite ou postgres')
    return engine == 'postgres'


def database_url():
    url = os.getenv('DATABASE_URL', '')
    if not url.startswith(('postgresql://', 'postgres://')):
        raise RuntimeError('Configure DATABASE_URL no ambiente, sem publicar a credencial no código')
    return url


class Row:
    def __init__(self, names, values):
        self.names, self.values = names, tuple(values)
        self.lookup = {}
        for name,value in zip(names,self.values):self.lookup.setdefault(name,value)
    def keys(self): return self.names
    def __getitem__(self, key): return self.values[key] if isinstance(key, (int, slice)) else self.lookup[key]
    def __iter__(self): return iter(self.values)
    def __len__(self): return len(self.values)


def row_factory(cursor):
    names = tuple(col.name for col in cursor.description) if cursor.description else ()
    return lambda values: Row(names, values)


class Cursor:
    def __init__(self, raw=None, rows=None, lastrowid=None, rowcount=None):
        self.raw, self.lastrowid = raw, lastrowid
        self.rows = iter(rows) if rows is not None else None
        self.rowcount = rowcount if rowcount is not None else (raw.rowcount if raw else 0)
    def fetchone(self): return next(self.rows, None) if self.rows is not None else self.raw.fetchone()
    def fetchall(self): return list(self.rows) if self.rows is not None else self.raw.fetchall()
    def __iter__(self):
        while True:
            row = self.fetchone()
            if row is None: break
            yield row


def pool():
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                from psycopg_pool import ConnectionPool
                from psycopg.adapt import Loader
                from decimal import Decimal
                class NumericLoader(Loader):
                    def load(self,data):
                        value=Decimal(bytes(data).decode())
                        return int(value) if value==value.to_integral_value() else float(value)
                def configure(conn):
                    conn.adapters.register_loader('numeric', NumericLoader)
                    conn.execute("SET TIME ZONE 'UTC'")
                    conn.execute("SET statement_timeout = '30s'")
                    conn.execute("SET lock_timeout = '15s'")
                _pool = ConnectionPool(database_url(), min_size=1,
                    max_size=max(1, min(40, int(os.getenv('NOWUP_PG_POOL_SIZE', '8')))),
                    timeout=15, kwargs={'autocommit': True, 'row_factory': row_factory, 'prepare_threshold': None},
                    configure=configure, open=True)
    return _pool


def close_pool():
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


_LITERAL = re.compile(r"'(?:''|[^'])*'")


@lru_cache(maxsize=4096)
def translate(statement):
    """Parse SQL instead of replacing placeholders inside quoted strings."""
    import sqlglot
    from sqlglot import exp
    ignore = bool(re.match(r'\s*INSERT\s+OR\s+IGNORE\b', statement, re.I))
    replace = bool(re.match(r'\s*INSERT\s+OR\s+REPLACE\b', statement, re.I))
    statement = re.sub(r'\bINSERT\s+OR\s+(IGNORE|REPLACE)\b', 'INSERT', statement, flags=re.I)
    # SQLite INTEGER PRIMARY KEY allocates an id even without AUTOINCREMENT.
    statement = re.sub(r'\bid\s+INTEGER\s+PRIMARY\s+KEY(?!\s+AUTOINCREMENT)',
                       'id INTEGER PRIMARY KEY AUTOINCREMENT', statement, flags=re.I)
    chunks = _LITERAL.split(statement)
    literals = _LITERAL.findall(statement)
    for i, chunk in enumerate(chunks):
        chunk = re.sub(r'\b(date|datetime|julianday)\s*\(', lambda m: 'nowup_'+m[1].lower()+'239(', chunk, flags=re.I)
        chunks[i] = chunk
    statement = ''.join(chunk+(literals[i] if i < len(literals) else '') for i, chunk in enumerate(chunks))
    tree = sqlglot.parse_one(statement, read='sqlite')
    constraints = []
    if isinstance(tree, exp.Create) and isinstance(tree.this, exp.Schema):
        table = tree.this.this.name
        for column in tree.this.expressions:
            if isinstance(column, exp.ColumnDef):
                keep = []
                for item in column.constraints:
                    if isinstance(item.kind, exp.Reference):
                        reference = item.kind.sql(dialect='postgres', identify=True)
                        constraints.append((table, column.name, reference))
                    else: keep.append(item)
                column.set('constraints', keep)
    for conflict in tree.find_all(exp.OnConflict):
        for ordered in list(conflict.find_all(exp.Ordered)):
            ordered.replace(ordered.this)
    for like in list(tree.find_all(exp.Like)):
        like.replace(exp.ILike(**like.args))
    # SQLite REAL is double precision, not PostgreSQL's 32-bit REAL.
    for datatype in tree.find_all(exp.DataType):
        if datatype.this == exp.DataType.Type.INT:
            datatype.set('this', exp.DataType.Type.BIGINT)
        if datatype.this == exp.DataType.Type.FLOAT:
            datatype.set('this', exp.DataType.Type.DOUBLE)
    rendered = tree.sql(dialect='postgres', identify=True)
    if ignore: rendered += ' ON CONFLICT DO NOTHING'
    if replace:
        if not re.match(r'\s*INSERT\s+INTO\s+"push_subscriptions"(?:\s|\()',rendered,re.I):
            raise ValueError('OR REPLACE não suportado para esta tabela')
        rendered += ' ON CONFLICT ("endpoint") DO UPDATE SET "user_id"=excluded."user_id", "session_hash"=excluded."session_hash", "subscription"=excluded."subscription"'
    return rendered, tuple(constraints)


class PostgresConnection:
    dialect = 'postgres'
    def __init__(self, raw, owner=None):
        self.raw, self.owner, self.closed = raw, owner, False
        self.constraints = []
        self.metadata = {}
    def _begin(self):
        from psycopg.pq import TransactionStatus
        if self.raw.info.transaction_status == TransactionStatus.IDLE:
            self.raw.execute('BEGIN')
    def execute(self, statement, parameters=None):
        import psycopg
        sql = statement.strip().rstrip(';')
        if re.match(r'PRAGMA\s+foreign_keys', sql, re.I): return Cursor(rows=[])
        match = re.fullmatch(r'PRAGMA\s+table_info\((.+)\)', sql, re.I)
        if match:
            name = match[1].strip('"\' ')
            rows = self.raw.execute('''SELECT ordinal_position-1 AS cid,column_name AS name,data_type AS type,
                CASE WHEN is_nullable='NO' THEN 1 ELSE 0 END AS notnull,column_default AS dflt_value,0 AS pk
                FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=%s ORDER BY ordinal_position''',(name,)).fetchall()
            return Cursor(rows=rows)
        if 'sqlite_master' in sql:
            sql = sql.replace('sqlite_master', 'information_schema.tables').replace("type='table'", "table_schema=current_schema()")
            sql = re.sub(r'\bname\b', 'table_name', sql)
        if re.fullmatch(r'BEGIN(?:\s+IMMEDIATE)?', sql, re.I):
            self._begin()
            if 'IMMEDIATE' in sql.upper():self.raw.execute('SELECT pg_advisory_xact_lock(239000000000000000)')
            return Cursor(rows=[])
        if re.match(r'(INSERT|UPDATE|DELETE)\b', sql, re.I): self._begin()
        translated, constraints = translate(sql)
        self.constraints.extend(item for item in constraints if item not in self.constraints)
        _constraints.update(constraints)
        if re.match(r'(CREATE|ALTER|DROP)\b', sql, re.I): self.metadata.clear()
        inserted = re.match(r'INSERT\s+(?:OR\s+(?:IGNORE|REPLACE)\s+)?INTO\s+["`]?([\w]+)', sql, re.I)
        auto_return = False
        if inserted and 'RETURNING' not in translated.upper():
            table = inserted[1]
            if table not in self.metadata:
                self.metadata[table] = {r[0] for r in self.raw.execute('SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=%s',(table,))}
            if 'id' in self.metadata[table]:
                translated += ' RETURNING "id"'
                auto_return = True
        # psycopg's parameter parser also sees percent signs inside string literals.
        if parameters is not None:
            translated = _LITERAL.sub(lambda m: m[0].replace('%', '%%'), translated)
        try:
            cursor = self.raw.execute(translated, parameters)
        except psycopg.IntegrityError as exc:
            raise sqlite3.IntegrityError(str(exc)) from exc
        except psycopg.OperationalError as exc:
            raise sqlite3.OperationalError(str(exc)) from exc
        except psycopg.Error as exc:
            raise sqlite3.OperationalError(str(exc)) from exc
        lastrowid = None
        if auto_return:
            row = cursor.fetchone()
            lastrowid = row[0] if row else None
        return Cursor(raw=cursor, lastrowid=lastrowid)
    def executemany(self, statement, rows):
        count = 0
        for values in rows: count += max(0, self.execute(statement, values).rowcount)
        return Cursor(rows=[], rowcount=count)
    def executescript(self, script):
        import sqlglot
        # Preserve SQL string literals while splitting multiple statements.
        for expression in sqlglot.parse(script, read='sqlite'):
            if expression is not None: self.execute(expression.sql(dialect='sqlite'))
    def commit(self): self.raw.commit()
    def rollback(self):
        if not self.raw.closed:self.raw.rollback()
    def close(self):
        if self.closed: return
        self.closed = True
        try:
            if not self.raw.closed:self.raw.rollback()
        finally:
            if self.owner: self.owner.putconn(self.raw)
            else: self.raw.close()
    def __enter__(self): return self
    def __exit__(self, kind, value, tb):
        try: self.rollback() if kind else self.commit()
        finally: self.close()
    def __del__(self):
        if not getattr(self, 'closed', True):
            try: self.close()
            except Exception: pass


def connect(sqlite_path):
    if not is_postgres():
        conn = sqlite3.connect(sqlite_path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        return conn
    try:
        owner = pool()
        return PostgresConnection(owner.getconn(), owner)
    except Exception as exc:
        import psycopg
        if isinstance(exc,psycopg.OperationalError):raise sqlite3.OperationalError('PostgreSQL temporariamente indisponível') from exc
        raise

_constraints = set()


def initialize_postgres_helpers(raw=None):
    if not is_postgres() and raw is None: return
    owner = None if raw is not None else pool()
    conn = raw if raw is not None else owner.getconn()
    try:
        conn.execute('''
        CREATE OR REPLACE FUNCTION nowup_timestamp239(value text, VARIADIC modifiers text[] DEFAULT ARRAY[]::text[])
        RETURNS timestamptz LANGUAGE plpgsql AS $$
        DECLARE result timestamptz; modifier text;
        BEGIN
          IF value IS NULL OR value='' THEN RETURN NULL; END IF;
          BEGIN
            result := CASE WHEN value='now' THEN clock_timestamp() ELSE value::timestamptz END;
            FOREACH modifier IN ARRAY modifiers LOOP
              IF modifier ~ '^[+-]?[0-9]+ (seconds?|minutes?|hours?|days?|months?|years?)$' THEN
                result := result + modifier::interval;
              ELSIF modifier='start of day' THEN result:=date_trunc('day',result);
              ELSIF modifier='start of month' THEN result:=date_trunc('month',result);
              ELSIF modifier='start of year' THEN result:=date_trunc('year',result);
              ELSE RETURN NULL;
              END IF;
            END LOOP;
          EXCEPTION WHEN invalid_datetime_format OR datetime_field_overflow THEN RETURN NULL;
          END;
          RETURN result;
        END $$;
        CREATE OR REPLACE FUNCTION nowup_date239(value text, VARIADIC modifiers text[] DEFAULT ARRAY[]::text[])
        RETURNS text LANGUAGE SQL AS $$ SELECT to_char(nowup_timestamp239(value,VARIADIC modifiers) AT TIME ZONE 'UTC','YYYY-MM-DD') $$;
        CREATE OR REPLACE FUNCTION nowup_datetime239(value text, VARIADIC modifiers text[] DEFAULT ARRAY[]::text[])
        RETURNS text LANGUAGE SQL AS $$ SELECT to_char(nowup_timestamp239(value,VARIADIC modifiers) AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS') $$;
        CREATE OR REPLACE FUNCTION nowup_julianday239(value text, VARIADIC modifiers text[] DEFAULT ARRAY[]::text[])
        RETURNS double precision LANGUAGE SQL AS $$ SELECT (extract(epoch FROM nowup_timestamp239(value,VARIADIC modifiers))/86400.0 + 2440587.5)::double precision $$;
        ''')
    finally:
        if owner is not None: owner.putconn(conn)


def finalize_postgres_constraints(conn=None):
    if not is_postgres() and conn is None: return
    import hashlib
    from psycopg import sql
    owned = conn is None
    conn = conn or connect(None)
    try:
        for table, column, reference in sorted(_constraints | set(conn.constraints)):
            name='fk239_'+hashlib.sha256(f'{table}:{column}:{reference}'.encode()).hexdigest()[:20]
            if not conn.raw.execute('SELECT 1 FROM pg_constraint WHERE conname=%s AND connamespace=current_schema()::regnamespace',(name,)).fetchone():
                conn.raw.execute(sql.SQL('ALTER TABLE {} ADD CONSTRAINT {} FOREIGN KEY ({}) '+reference).format(sql.Identifier(table),sql.Identifier(name),sql.Identifier(column)))
        reset_identity_sequences(conn)
        if owned: conn.commit()
    finally:
        if owned: conn.close()


def reset_identity_sequences(conn):
    from psycopg import sql
    columns=conn.raw.execute("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema=current_schema() AND is_identity='YES'").fetchall()
    for table,column in columns:
        sequence=conn.raw.execute('SELECT pg_get_serial_sequence(%s,%s)',(table,column)).fetchone()[0]
        maximum=conn.raw.execute(sql.SQL('SELECT MAX({}) FROM {}').format(sql.Identifier(column),sql.Identifier(table))).fetchone()[0]
        if sequence and maximum is not None:
            # Never move an existing sequence backwards during a restart.
            current=conn.raw.execute(sql.SQL('SELECT last_value FROM {}').format(sql.Identifier(*sequence.split('.')))).fetchone()[0]
            conn.raw.execute('SELECT setval(%s,%s,true)',(sequence,max(int(maximum),int(current))))
