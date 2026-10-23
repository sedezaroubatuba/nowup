"""One revocation registry for opaque sessions, including legacy admin routes."""
import hashlib
import os
import sqlite3
from datetime import datetime, timezone


def now(): return datetime.now(timezone.utc).isoformat()
def token_hash(token): return hashlib.sha256(token.encode()).hexdigest()

def require_secrets():
    for key in ('NOWUP_ADMIN_SECRET', 'NOWUP_JWT_SECRET'):
        if len(os.getenv(key, '')) < 32:
            raise RuntimeError(key + ' deve conter pelo menos 32 caracteres aleatórios.')
    if os.environ['NOWUP_ADMIN_SECRET'] == os.environ['NOWUP_JWT_SECRET']:
        raise RuntimeError('Use segredos distintos para administração e assinatura.')


def initialize(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS adm227_access(id INTEGER PRIMARY KEY AUTOINCREMENT,
      actor_id TEXT NOT NULL DEFAULT '',name TEXT NOT NULL DEFAULT '',session_hash TEXT UNIQUE,
      start TEXT NOT NULL DEFAULT '',last_activity TEXT NOT NULL DEFAULT '',end TEXT NOT NULL DEFAULT '',state TEXT NOT NULL DEFAULT 'Conectado')''')
    columns={r[1] for r in conn.execute('PRAGMA table_info(adm227_access)')}
    for key,kind in {'token_hash':'TEXT','user_id':'INTEGER','role':'TEXT','created_at':'TEXT','expires_at':'TEXT','revoked_at':'TEXT','end_at':'TEXT'}.items():
        if key not in columns: conn.execute('ALTER TABLE adm227_access ADD COLUMN '+key+' '+kind)
    conn.execute("UPDATE adm227_access SET token_hash=session_hash,created_at=start,revoked_at=NULLIF(end,''),end_at=NULLIF(end,'') WHERE token_hash IS NULL")
    conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_access_token ON adm227_access(token_hash)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)')
    for row in conn.execute('SELECT s.token,s.user_id,s.expires_at,u.role,u.name FROM sessions s JOIN users u ON u.id=s.user_id').fetchall():
        register(conn,row['token'],row['user_id'],row['role'],row['expires_at'],row['name'])


def register(conn,token,uid,role,expires,name=''):
    digest=token_hash(token);stamp=now();actor=('staff:' if role=='team' else 'admin:' if role=='admin' else role+':')+str(uid)
    conn.execute('''INSERT INTO adm227_access(actor_id,name,session_hash,start,last_activity,token_hash,user_id,role,created_at,expires_at)
       VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(session_hash) DO UPDATE SET
       token_hash=excluded.token_hash,user_id=excluded.user_id,role=excluded.role,expires_at=excluded.expires_at''',
       (actor,name,digest,stamp,stamp,digest,uid,role,stamp,expires))


def session_user(conn,token):
    if not token:return None
    row=conn.execute('''SELECT u.*,s.expires_at session_expires FROM sessions s JOIN users u ON u.id=s.user_id
        WHERE s.token=? AND s.expires_at>? AND u.is_active=1''',(token,now())).fetchone()
    if row is None:return None
    access=conn.execute('SELECT * FROM adm227_access WHERE session_hash=?',(token_hash(token),)).fetchone()
    if access:
        keys=access.keys()
        if access['end'] or ('revoked_at' in keys and access['revoked_at']):return None
        if 'expires_at' in keys and access['expires_at'] and access['expires_at']<=now():return None
    # Imported/old sessions are registered lazily; installation backfills normal sessions.
    if access is None and 'token_hash' in {r[1] for r in conn.execute('PRAGMA table_info(adm227_access)')}:
        register(conn,token,row['id'],row['role'],row['session_expires'],row['name']);conn.commit()
    return row


def revoke_session(conn,digest):
    stamp=now();columns={r[1] for r in conn.execute('PRAGMA table_info(adm227_access)')}
    if 'revoked_at' in columns:
        conn.execute("UPDATE adm227_access SET revoked_at=COALESCE(revoked_at,?),end_at=COALESCE(end_at,?),end=?,state='Revogada' WHERE session_hash=?",(stamp,stamp,stamp,digest))
    registry=conn.execute('SELECT user_id FROM adm227_access WHERE session_hash=?',(digest,)).fetchone() if 'user_id' in columns else None
    candidates=conn.execute('SELECT token FROM sessions WHERE user_id=?',(registry['user_id'],)).fetchall() if registry and registry['user_id'] is not None else conn.execute('SELECT token FROM sessions').fetchall()
    for row in candidates:
        if token_hash(row['token'])==digest:conn.execute('DELETE FROM sessions WHERE token=?',(row['token'],))
    tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'push_subscriptions' in tables:conn.execute('DELETE FROM push_subscriptions WHERE session_hash=?',(digest,))
    if 'adm227_team_sessions' in tables:conn.execute('DELETE FROM adm227_team_sessions WHERE token_hash=?',(digest,))


def clear_cookies(response):
    for name,path in [('nowup_session','/'),('nowup_team227','/admin/super'),('nowup_team227','/'),('nowup_admin_challenge','/'),('nowup_admin_verified','/')]:
        response.delete_cookie(name,path=path,httponly=True,secure=True,samesite='lax')
    response.headers['Cache-Control']='no-store'
    return response
