"""Shared opaque-session validation, including Super ADM revocations."""
import hashlib
import sqlite3
from datetime import datetime, timezone


def session_user(conn, token, store_id345=0):
    if not token:
        return None
    row = conn.execute('''SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
        WHERE s.token=? AND s.expires_at>? AND u.is_active=1 AND (s.absolute_expires_at238='' OR s.absolute_expires_at238>?)''',
        (token, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())).fetchone()
    if row is None:
        return None
    session345=conn.execute('SELECT * FROM sessions WHERE token=?',(token,)).fetchone()
    if session345 is None:return None
    actual345=session345['store_id345'] if 'store_id345' in session345.keys() else 0
    user345=row['customer_store345'] if 'customer_store345' in row.keys() else 0
    if actual345!=store_id345 or user345!=store_id345:return None
    if store_id345:
        if row['role']!='customer':return None
        row=dict(row);row['email']=row['customer_email345']
    # Editorial accounts must never inherit the platform's Super ADM privileges.
    if 'role' in row.keys() and row['role']=='admin':
        exists=conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cms_permissions'").fetchone()
        permission=conn.execute('SELECT cms_role FROM cms_permissions WHERE user_id=?',(row['id'],)).fetchone() if exists else None
        if permission and permission['cms_role']!='admin':
            row=dict(row);row['role']='cms'
    try:
        access = conn.execute('SELECT end FROM adm227_access WHERE session_hash=?',
            (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    except sqlite3.OperationalError as exc:
        # Existing installations may not have installed the Super ADM schema yet.
        if 'no such table: adm227_access' not in str(exc):
            raise
        access = None
    return None if access and access['end'] else row


def revoke_session(conn, token_hash):
    """Delete the exact opaque session as well as its team equivalent."""
    for row in conn.execute('SELECT token FROM sessions').fetchall():
        if hashlib.sha256(row['token'].encode()).hexdigest() == token_hash:
            conn.execute('DELETE FROM sessions WHERE token=?', (row['token'],))
            if conn.execute("SELECT 1 FROM sqlite_master WHERE name='push_subscriptions'").fetchone():
                conn.execute('DELETE FROM push_subscriptions WHERE session_hash=?', (token_hash,))
    conn.execute('DELETE FROM adm227_team_sessions WHERE token_hash=?', (token_hash,))

