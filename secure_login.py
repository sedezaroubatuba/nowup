import os, hmac, hashlib, secrets, sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

BASE=Path(__file__).resolve().parent
DB_PATH=Path(os.getenv("NOWUP_DB",BASE/"data"/"nowup.db"))
router=APIRouter()

def db():
    conn=sqlite3.connect(DB_PATH)
    conn.row_factory=sqlite3.Row
    return conn

def verify_password(password: str, stored: str):
    try:
        salt,digest=stored.split("$",1)
        calc=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),240_000).hex()
        return hmac.compare_digest(calc,digest)
    except Exception:
        return False

def create_session(uid: int, dest: str, admin: bool=False):
    token=secrets.token_urlsafe(32)
    ttl=timedelta(minutes=30) if admin else timedelta(days=30)
    expires=(datetime.now(timezone.utc)+ttl).isoformat()
    conn=db(); conn.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)",(token,uid,expires)); conn.commit(); conn.close()
    resp=RedirectResponse(dest,303)
    kwargs={"httponly":True,"samesite":"lax","secure":os.getenv("NOWUP_HTTPS","0")=="1"}
    if not admin:
        kwargs["max_age"]=int(ttl.total_seconds())
    resp.set_cookie("nowup_session",token,**kwargs)
    return resp

@router.post("/entrar")
def secure_login(email: str=Form(...),password: str=Form(...),tipo: str=Form("")):
    normalized=email.strip().lower()
    conn=db()
    u=conn.execute("SELECT * FROM users WHERE email=? AND is_active=1",(normalized,)).fetchone()
    conn.close()
    suffix=f"&tipo={tipo}" if tipo in ("cliente","profissional","admin") else ""
    if not u or not verify_password(password,u["password_hash"]):
        return RedirectResponse(f"/entrar?erro=1{suffix}",303)
    if u["role"]!="admin" and "email_verified" in u.keys() and not u["email_verified"]:
        return RedirectResponse(f"/entrar?erro=verificacao{suffix}",303)
    if tipo=="admin" and u["role"]!="admin":
        return RedirectResponse("/entrar?tipo=admin&erro=perfil",303)
    if tipo=="profissional" and u["role"]!="professional":
        return RedirectResponse("/entrar?tipo=profissional&erro=perfil",303)
    if tipo=="cliente" and u["role"]!="customer":
        return RedirectResponse("/entrar?tipo=cliente&erro=perfil",303)
    if u["role"]=="admin":
        return create_session(u["id"],"/admin",admin=True)
    if u["role"]=="professional":
        return create_session(u["id"],"/painel")
    return create_session(u["id"],"/")

@router.get("/admin/entrar")
def force_admin_login(request: Request):
    token=request.cookies.get("nowup_session")
    if token:
        conn=db(); conn.execute("DELETE FROM sessions WHERE token=?",(token,)); conn.commit(); conn.close()
    resp=RedirectResponse("/entrar?tipo=admin",303)
    resp.delete_cookie("nowup_session")
    return resp
