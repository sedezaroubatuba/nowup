"""Transactional public image persistence; no per-request filesystem scan."""
import re
import json
import shutil
from pathlib import Path
PUBLIC={
 'users':{'avatar_filename'},
 'professionals':{'avatar_filename','cover_filename','featured_image_filename','slide_image_filename'},
 'photos':{'filename'},'posts':{'photo_filename'},
 'banners':{'image_filename','mobile_image_filename'},'cms_posts':{'image_filename'},
 'products':{'image_filename','customization192'},'product_categories':{'image_filename'},
 'daily_promotions':{'image_filename'},'store_banners207':{'image'},
 'home_banners210':{'image'},'site_settings':{'value'}}
FILENAME=re.compile(r'(?<![A-Za-z0-9_-])([A-Za-z0-9_-]+\.(?:jpe?g|png|webp|gif|svg))(?![A-Za-z0-9_.-])',re.I)

def references(conn,native=False):
    if native:
        columns={}
        for r in conn.execute("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema=current_schema()"):
            columns.setdefault(r[0],set()).add(r[1])
    else:
        tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        columns={t:{r[1] for r in conn.execute('PRAGMA table_info("'+t+'")')} for t in PUBLIC if t in tables}
    found=set()
    for table,allowed in PUBLIC.items():
        for column in allowed & columns.get(table,set()):
            for row in conn.execute('SELECT "'+column+'" FROM "'+table+'" WHERE "'+column+'" IS NOT NULL'):
                value=str(row[0] or '')
                def extract(value):
                    if isinstance(value,dict):
                        for v in value.values():extract(v)
                    elif isinstance(value,list):
                        for v in value:extract(v)
                    elif isinstance(value,str):
                        if value.startswith('/uploads/'):value=value[len('/uploads/'):]
                        if FILENAME.fullmatch(value):found.add(value)
                try:extract(json.loads(value))
                except (ValueError,TypeError):extract(value)
    return found

def initialize(conn):
    from nowup_auth247 import initialize as auth_initialize
    auth_initialize(conn)
    conn.execute('CREATE TABLE IF NOT EXISTS nowup_public_media245(filename TEXT PRIMARY KEY,body TEXT NOT NULL,digest TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS nowup_deleted_media247(filename TEXT PRIMARY KEY)')

class MediaConnection:
    def __init__(self,conn,directory):
        self._conn=conn;self._directory=Path(directory);self._before=None
    def __getattr__(self,name):return getattr(self._conn,name)
    def execute(self,statement,parameters=None):
        match=re.match(r'\s*(?:INSERT(?:\s+OR\s+\w+)?\s+INTO|UPDATE|DELETE\s+FROM)\s+["`]?([\w]+)',statement,re.I)
        if match and match[1] in PUBLIC and self._before is None:
            if getattr(self._conn,'dialect','sqlite')=='postgres':
                self._conn.execute('BEGIN')
                self._conn.execute('SELECT pg_advisory_xact_lock(247000000000001)')
            elif not self._conn.in_transaction:self._conn.execute('BEGIN IMMEDIATE')
            initialize(self._conn)
            self._before=references(self._conn)
        return self._conn.execute(statement,parameters) if parameters is not None else self._conn.execute(statement)
    def executemany(self,statement,rows):
        for row in rows:self.execute(statement,row)
    def commit(self):
        if self._before is not None:
            from nowup_media245 import put,NAME,TABLE
            after=references(self._conn)
            for name in after-self._before:
                self._conn.execute('DELETE FROM nowup_deleted_media247 WHERE filename=?',(name,))
                if not NAME.fullmatch(name):continue # bundled SVG demos remain filesystem assets
                path=self._directory/name
                if path.is_symlink():raise ValueError('Link de imagem inválido')
                bundled=Path(__file__).resolve().parent/'static'/name
                if not path.exists() and name.startswith('demo-') and bundled.is_file() and not bundled.is_symlink():shutil.copyfile(bundled,path)
                if path.is_file():put(self._conn,name,path.read_bytes())
                elif not self._conn.execute('SELECT 1 FROM '+TABLE+' WHERE filename=?',(name,)).fetchone():
                    raise ValueError('A imagem enviada não está disponível. Reenvie a imagem.')
            for name in self._before-after:
                self._conn.execute('DELETE FROM '+TABLE+' WHERE filename=?',(name,))
                self._conn.execute('INSERT INTO nowup_deleted_media247(filename) VALUES(?) ON CONFLICT(filename) DO NOTHING',(name,))
        self._conn.commit();self._before=None
    def rollback(self):self._conn.rollback();self._before=None
    def close(self):self._conn.close()
    def __enter__(self):return self
    def __exit__(self,kind,value,tb):
        try:self.rollback() if kind else self.commit()
        finally:self.close()
