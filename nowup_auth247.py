"""Shared fixed-window login limits; no plaintext email stored."""
import hashlib,time
from fastapi import HTTPException

def initialize(conn):
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
