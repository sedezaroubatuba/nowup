import os, re, sqlite3
from datetime import datetime, timezone
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
