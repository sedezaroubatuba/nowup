"""Shared fixed-window login limits; no plaintext email stored."""
import hashlib,time
from fastapi import HTTPException

def initialize(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS auth_cooldowns348(bucket TEXT PRIMARY KEY,sent_at INTEGER NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS auth_limits247(bucket TEXT NOT NULL,window_start INTEGER NOT NULL,attempts INTEGER NOT NULL,PRIMARY KEY(bucket,window_start))')

def check(db,request,email,kind='login',now=None):
    now=int(time.time() if now is None else now)
    specs=[('account',str(email).strip().lower(),600,10 if kind=='login' else 3),('origin',request.client.host if request.client else 'unknown',300,120 if kind=='login' else 30)]
    conn=db()
    try:
        conn.execute('BEGIN IMMEDIATE');blocked=False
        for scope,value,period,limit in specs:
            key=hashlib.sha256((kind+':'+scope+':'+value).encode()).hexdigest();window=now//period*period
            conn.execute('INSERT INTO auth_limits247(bucket,window_start,attempts) VALUES(?,?,1) ON CONFLICT(bucket,window_start) DO UPDATE SET attempts=auth_limits247.attempts+1',(key,window))
            count=conn.execute('SELECT attempts FROM auth_limits247 WHERE bucket=? AND window_start=?',(key,window)).fetchone()[0];blocked=blocked or count>limit
        conn.execute('DELETE FROM auth_limits247 WHERE window_start<?',(now-1200,));conn.commit()
    except Exception:conn.rollback();raise
    finally:conn.close()
    if blocked:raise HTTPException(429,'Muitas tentativas. Aguarde alguns minutos e tente novamente.',headers={'Retry-After':'600','Cache-Control':'no-store'})


def verification(db,request,account,now=None):
    now=int(time.time() if now is None else now)
    check(db,request,account,kind='verification',now=now)
    key=hashlib.sha256(('verification:'+account.strip().lower()).encode()).hexdigest()
    conn=db()
    try:
        conn.execute('BEGIN IMMEDIATE')
        changed=conn.execute('INSERT INTO auth_cooldowns348(bucket,sent_at) VALUES(?,?) ON CONFLICT(bucket) DO UPDATE SET sent_at=excluded.sent_at WHERE auth_cooldowns348.sent_at<=?',(key,now,now-60)).rowcount
        conn.execute('DELETE FROM auth_cooldowns348 WHERE sent_at<?',(now-86400,))
        conn.commit()
    except Exception:conn.rollback();raise
    finally:conn.close()
    if not changed:raise HTTPException(429,'Aguarde um minuto antes de reenviar.',headers={'Retry-After':'60','Cache-Control':'no-store'})


def verification_token348(user):
    from datetime import datetime,timezone,timedelta
    token=user['verification_token'];expires=user['verification_expires_at']
    try:valid=bool(token) and datetime.fromisoformat(expires)>datetime.now(timezone.utc)
    except (ValueError,TypeError):valid=False
    if valid:return token,expires
    import secrets
    return secrets.token_urlsafe(32),(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat()


def password_matches404(password, stored, verify):
    """Do equal-cost password work for unknown/inactive and existing accounts.

    The fixed dummy credential can never authenticate: a real stored hash is
    required independently of the comparison result. Rate limiting stays first.
    """
    if not isinstance(password, str) or len(password) > 128:
        return False
    dummy = "00000000000000000000000000000000$5bef77d1f5b62578a218575132d4f1e0edab72039084aa7fe9960148fc5d9e49"
    matched = verify(password, stored or dummy)
    return bool(stored) and matched
