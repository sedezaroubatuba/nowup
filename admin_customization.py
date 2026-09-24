import os, re, sqlite3, hmac, hashlib, secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("NOWUP_DB", BASE / "data" / "nowup.db"))
router = APIRouter()

def db():
    conn=sqlite3.connect(DB_PATH)
    conn.row_factory=sqlite3.Row
    return conn

def require_admin(request: Request):
    token=request.cookies.get("nowup_session")
    if not token:
        raise HTTPException(401,"Faça login novamente")
    conn=db()
    row=conn.execute("""
      SELECT u.id,u.role FROM sessions s
      JOIN users u ON u.id=s.user_id
      WHERE s.token=? AND s.expires_at>? AND u.is_active=1
    """,(token,datetime.now(timezone.utc).isoformat())).fetchone()
    conn.close()
    if not row or row["role"]!="admin":
        raise HTTPException(403,"Acesso administrativo necessário")
    return row

@router.post("/admin/aparencia")
def save_appearance(
    request: Request,
    brand_name: str=Form("NowUp"),
    primary_color: str=Form("#2457e6"),
    accent_color: str=Form("#ff8a32"),
    font_family: str=Form("Inter"),
    hero_title: str=Form("Encontre quem resolve."),
    hero_subtitle: str=Form(""),
    public_email: str=Form(""),
    support_whatsapp: str=Form("")
):
    require_admin(request)
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}",primary_color):
        primary_color="#2457e6"
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}",accent_color):
        accent_color="#ff8a32"
    allowed_fonts={"Inter","Arial","Georgia","Trebuchet MS","Verdana"}
    if font_family not in allowed_fonts:
        font_family="Inter"
    data={
      "brand_name":brand_name.strip()[:40] or "NowUp",
      "primary_color":primary_color,
      "accent_color":accent_color,
      "font_family":font_family,
      "hero_title":hero_title.strip()[:120] or "Encontre quem resolve.",
      "hero_subtitle":hero_subtitle.strip()[:320],
      "public_email":public_email.strip()[:160],
      "support_whatsapp":support_whatsapp.strip()[:30]
    }
    conn=db()
    for key,value in data.items():
        conn.execute("INSERT INTO site_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,value))
    conn.commit(); conn.close()
    return RedirectResponse("/admin#aparencia",303)

@router.post("/admin/perfil")
def save_admin_profile(request: Request, name: str=Form(...)):
    admin=require_admin(request)
    clean=name.strip()[:100]
    if not clean:
        return RedirectResponse("/admin#perfil",303)
    conn=db(); conn.execute("UPDATE users SET name=? WHERE id=?",(clean,admin["id"])); conn.commit(); conn.close()
    return RedirectResponse("/admin#perfil",303)


def verify_password(password: str, stored: str):
    try:
        salt,digest=stored.split("$",1)
        calc=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),240_000).hex()
        return hmac.compare_digest(calc,digest)
    except Exception:
        return False

def create_secure_session(uid: int, dest: str, admin: bool=False):
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
    conn=db(); u=conn.execute("SELECT * FROM users WHERE email=? AND is_active=1",(normalized,)).fetchone(); conn.close()
    suffix=f"&tipo={tipo}" if tipo in ("cliente","profissional","admin") else ""
    if not u or not verify_password(password,u["password_hash"]):
        return RedirectResponse(f"/entrar?erro=1{suffix}",303)
    if u["role"]!="admin" and "email_verified" in u.keys() and not u["email_verified"]:
        return RedirectResponse(f"/entrar?erro=verificacao{suffix}",303)
    expected={"admin":"admin","profissional":"professional","cliente":"customer"}.get(tipo)
    if expected and u["role"]!=expected:
        return RedirectResponse(f"/entrar?tipo={tipo}&erro=perfil",303)
    if u["role"]=="admin":
        return create_secure_session(u["id"],"/admin",admin=True)
    if u["role"]=="professional":
        return create_secure_session(u["id"],"/painel")
    return create_secure_session(u["id"],"/")

@router.get("/admin/entrar")
def force_admin_login(request: Request):
    token=request.cookies.get("nowup_session")
    if token:
        conn=db(); conn.execute("DELETE FROM sessions WHERE token=?",(token,)); conn.commit(); conn.close()
    resp=RedirectResponse("/entrar?tipo=admin",303)
    resp.delete_cookie("nowup_session")
    return resp
