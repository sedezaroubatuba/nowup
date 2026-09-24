import hashlib, hmac, os, secrets, sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from mailing import configured, send_password_reset

BASE=Path(__file__).resolve().parent
DB_PATH=Path(os.getenv("NOWUP_DB",BASE/"data"/"nowup.db"))
templates=Jinja2Templates(directory=str(BASE/"templates"))
router=APIRouter()

def db():
    conn=sqlite3.connect(DB_PATH)
    conn.row_factory=sqlite3.Row
    return conn

def settings():
    conn=db()
    rows=conn.execute("SELECT key,value FROM site_settings").fetchall()
    conn.close()
    return {r["key"]:r["value"] for r in rows}

def page(request, message="", token=""):
    return templates.TemplateResponse("password_reset.html",
        {"request":request,"settings":settings(),"user":None,"message":message,"token":token})

@router.get("/esqueci-senha", response_class=HTMLResponse)
def forgot_page(request: Request):
    return page(request)

@router.post("/esqueci-senha")
def forgot(request: Request, email: str=Form(...)):
    generic="Se a conta existir, enviaremos instruções para este e-mail."
    if not configured():
        return page(request,"Recuperação por e-mail indisponível no momento.")
    normalized=email.strip().lower()
    now=datetime.now(timezone.utc)
    conn=db()
    conn.execute("""CREATE TABLE IF NOT EXISTS password_resets(
        user_id INTEGER PRIMARY KEY, token_hash TEXT NOT NULL,
        expires_at TEXT NOT NULL, requested_at TEXT NOT NULL)""")
    user=conn.execute("SELECT id,name,email FROM users WHERE email=? AND is_active=1",(normalized,)).fetchone()
    if user:
        prior=conn.execute("SELECT requested_at FROM password_resets WHERE user_id=?",(user["id"],)).fetchone()
        if not prior or prior["requested_at"] < (now-timedelta(minutes=5)).isoformat():
            token=secrets.token_urlsafe(32)
            digest=hashlib.sha256(token.encode()).hexdigest()
            conn.execute("""INSERT INTO password_resets(user_id,token_hash,expires_at,requested_at)
                VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET token_hash=excluded.token_hash,
                expires_at=excluded.expires_at,requested_at=excluded.requested_at""",
                (user["id"],digest,(now+timedelta(minutes=30)).isoformat(),now.isoformat()))
            conn.commit()
            send_password_reset(user["email"],user["name"],token)
    conn.close()
    return page(request,generic)

@router.get("/recuperar-senha", response_class=HTMLResponse)
def reset_page(request: Request, token: str=""):
    if not token:
        return RedirectResponse("/esqueci-senha",303)
    return page(request,token=token)

@router.post("/recuperar-senha")
def reset(request: Request, token: str=Form(...), password: str=Form(...),
          password_confirm: str=Form(...)):
    if len(password)<12 or password!=password_confirm:
        return page(request,"Use ao menos 12 caracteres e confirme a mesma senha.",token)
    digest=hashlib.sha256(token.encode()).hexdigest()
    conn=db()
    conn.execute("BEGIN IMMEDIATE")
    row=conn.execute("SELECT user_id,expires_at FROM password_resets WHERE token_hash=?",(digest,)).fetchone()
    if not row or row["expires_at"] < datetime.now(timezone.utc).isoformat():
        conn.rollback(); conn.close()
        return page(request,"Link inválido ou vencido. Solicite outro.")
    salt=secrets.token_hex(16)
    hashed=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),240_000).hex()
    conn.execute("UPDATE users SET password_hash=? WHERE id=?",(f"{salt}${hashed}",row["user_id"]))
    conn.execute("DELETE FROM sessions WHERE user_id=?",(row["user_id"],))
    conn.execute("DELETE FROM password_resets WHERE user_id=?",(row["user_id"],))
    conn.commit(); conn.close()
    return RedirectResponse("/entrar?senha=alterada",303)
