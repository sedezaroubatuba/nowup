from __future__ import annotations
import csv, hashlib, io, os, secrets, sqlite3, unicodedata, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from PIL import Image

BASE=Path(__file__).resolve().parent
DB_PATH=Path(os.getenv("NOWUP_DB",BASE/"data"/"nowup.db"))
UPLOAD_DIR=Path(os.getenv("NOWUP_UPLOAD_DIR",BASE/"uploads")); UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
templates=Jinja2Templates(directory=str(BASE/"templates")); router=APIRouter()

def db():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); return c
def now_iso(): return datetime.now(timezone.utc).isoformat()
def slugify(v):
    v=unicodedata.normalize("NFKD",v or "").encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+","-",v).strip("-") or secrets.token_hex(4)
def hash_password(p):
    s=secrets.token_hex(16); d=hashlib.pbkdf2_hmac("sha256",p.encode(),bytes.fromhex(s),240_000); return f"{s}${d.hex()}"
def current_user(request):
    token=request.cookies.get("nowup_session")
    if not token:return None
    c=db(); r=c.execute("SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires_at>? AND u.is_active=1",(token,now_iso())).fetchone(); c.close(); return dict(r) if r else None
def cms_role(request):
    u=current_user(request)
    if not u or u["role"]!="admin": raise HTTPException(403,"Acesso administrativo necessário")
    c=db(); p=c.execute("SELECT cms_role FROM cms_permissions WHERE user_id=?",(u["id"],)).fetchone(); c.close(); return u,(p["cms_role"] if p else "admin")
def allow(request,*roles):
    u,r=cms_role(request)
    if r not in roles: raise HTTPException(403,"Seu nível de acesso não permite esta ação")
    return u,r
def settings(c=None):
    own=c is None; c=c or db(); d={r["key"]:r["value"] for r in c.execute("SELECT key,value FROM site_settings")}
    if own:c.close()
    return d
def public_context(request,**extra):
    c=db(); d=settings(c); cats=c.execute("SELECT * FROM categories WHERE active=1 ORDER BY sort_order,name").fetchall(); c.close()
    return {"request":request,"settings":d,"categories":cats,"user":current_user(request),**extra}
def save_image(upload):
    if not upload or not upload.filename:return ""
    raw=upload.file.read(6*1024*1024)
    if len(raw)>5*1024*1024:raise HTTPException(413,"Imagem maior que 5 MB")
    try:
        im=Image.open(io.BytesIO(raw)).convert("RGB"); im.thumbnail((1920,1920)); name=f"cms-{secrets.token_hex(12)}.webp"; im.save(UPLOAD_DIR/name,"WEBP",quality=86,method=6); return name
    except Exception as e:raise HTTPException(400,"Imagem inválida") from e

def init_cms_db():
    c=db(); c.executescript("""
    CREATE TABLE IF NOT EXISTS cms_pages(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,slug TEXT NOT NULL UNIQUE,content TEXT DEFAULT '',status TEXT NOT NULL DEFAULT 'published',seo_title TEXT DEFAULT '',seo_description TEXT DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS cms_posts(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,slug TEXT NOT NULL UNIQUE,excerpt TEXT DEFAULT '',content TEXT DEFAULT '',image_filename TEXT DEFAULT '',image_alt TEXT DEFAULT '',category TEXT DEFAULT 'Novidades',tags TEXT DEFAULT '',status TEXT NOT NULL DEFAULT 'draft',publish_at TEXT DEFAULT '',author_id INTEGER REFERENCES users(id) ON DELETE SET NULL,seo_title TEXT DEFAULT '',seo_description TEXT DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS cms_comments(id INTEGER PRIMARY KEY AUTOINCREMENT,post_id INTEGER NOT NULL REFERENCES cms_posts(id) ON DELETE CASCADE,name TEXT NOT NULL,email TEXT DEFAULT '',comment TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS cms_leads(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT DEFAULT '',phone TEXT DEFAULT '',subject TEXT DEFAULT '',message TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'new',created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS cms_permissions(user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,cms_role TEXT NOT NULL DEFAULT 'editor' CHECK(cms_role IN ('admin','editor','author')));
    """)
    for r in c.execute("SELECT id FROM users WHERE role='admin'").fetchall():c.execute("INSERT OR IGNORE INTO cms_permissions(user_id,cms_role) VALUES(?,'admin')",(r["id"],))
    defaults={"site_slogan":"Encontre quem resolve.","contact_email":"","contact_phone":"","contact_whatsapp":"","contact_address":"","instagram_url":"","facebook_url":"","linkedin_url":"","youtube_url":"","tiktok_url":"","seo_title":"Guia comercial de Ubatuba","seo_description":"Empresas, lojas, restaurantes e prestadores de serviços em Ubatuba.","seo_keywords":"guia comercial de Ubatuba, serviços em Ubatuba, empresas em Ubatuba","lead_recipient":"","analytics_id":"","tag_manager_id":"","facebook_pixel_id":""}
    for k,v in defaults.items():c.execute("INSERT OR IGNORE INTO site_settings(key,value) VALUES(?,?)",(k,v))
    c.commit();c.close()

@router.get("/admin/cms",response_class=HTMLResponse)
def cms_dashboard(request:Request):
    u,role=cms_role(request);c=db();pages=c.execute("SELECT * FROM cms_pages ORDER BY updated_at DESC").fetchall();posts=c.execute("SELECT p.*,u.name author_name FROM cms_posts p LEFT JOIN users u ON u.id=p.author_id ORDER BY p.id DESC").fetchall();leads=c.execute("SELECT * FROM cms_leads ORDER BY id DESC LIMIT 100").fetchall();comments=c.execute("SELECT c.*,p.title post_title FROM cms_comments c JOIN cms_posts p ON p.id=c.post_id ORDER BY c.id DESC").fetchall();admins=c.execute("SELECT u.id,u.name,u.email,u.is_active,COALESCE(cp.cms_role,'admin') cms_role FROM users u LEFT JOIN cms_permissions cp ON cp.user_id=u.id WHERE u.role='admin' ORDER BY u.id").fetchall();data=settings(c);c.close()
    return templates.TemplateResponse("cms_admin.html",public_context(request,pages=pages,posts=posts,leads=leads,comments=comments,admins=admins,cms_role=role,cms_user=u,settings=data))

@router.post("/admin/cms/configuracoes")
async def cms_save_settings(request:Request):
    allow(request,"admin");form=await request.form();allowed=("brand_name","site_slogan","contact_email","contact_phone","contact_whatsapp","contact_address","instagram_url","facebook_url","linkedin_url","youtube_url","tiktok_url","seo_title","seo_description","seo_keywords","lead_recipient","analytics_id","tag_manager_id","facebook_pixel_id","active_cities");c=db()
    for k in allowed:
        v=str(form.get(k,"")).strip()[:1000];c.execute("INSERT INTO site_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(k,v))
    c.commit();c.close();return RedirectResponse("/admin/cms?ok=config#configuracoes",303)

@router.post("/admin/cms/paginas/salvar")
def page_save(request:Request,page_id:int=Form(0),title:str=Form(...),slug:str=Form(""),content:str=Form(""),status:str=Form("published"),seo_title:str=Form(""),seo_description:str=Form("")):
    allow(request,"admin","editor");s=slugify(slug or title);status=status if status in ("draft","published","hidden") else "draft";c=db()
    try:
        if page_id:c.execute("UPDATE cms_pages SET title=?,slug=?,content=?,status=?,seo_title=?,seo_description=?,updated_at=? WHERE id=?",(title[:160],s,content,status,seo_title[:160],seo_description[:320],now_iso(),page_id))
        else:c.execute("INSERT INTO cms_pages(title,slug,content,status,seo_title,seo_description,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(title[:160],s,content,status,seo_title[:160],seo_description[:320],now_iso(),now_iso()))
        c.commit()
    except sqlite3.IntegrityError:c.rollback()
    c.close();return RedirectResponse("/admin/cms#paginas",303)
@router.post("/admin/cms/paginas/{pid}/duplicar")
def page_dup(request:Request,pid:int):
    allow(request,"admin","editor");c=db();p=c.execute("SELECT * FROM cms_pages WHERE id=?",(pid,)).fetchone()
    if p:c.execute("INSERT INTO cms_pages(title,slug,content,status,seo_title,seo_description,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(p["title"]+" (cópia)",slugify(p["slug"]+"-copia-"+secrets.token_hex(2)),p["content"],"draft",p["seo_title"],p["seo_description"],now_iso(),now_iso()));c.commit()
    c.close();return RedirectResponse("/admin/cms#paginas",303)
@router.post("/admin/cms/paginas/{pid}/excluir")
def page_del(request:Request,pid:int):
    allow(request,"admin");c=db();c.execute("DELETE FROM cms_pages WHERE id=?",(pid,));c.commit();c.close();return RedirectResponse("/admin/cms#paginas",303)

@router.post("/admin/cms/posts/salvar")
def post_save(request:Request,post_id:int=Form(0),title:str=Form(...),slug:str=Form(""),excerpt:str=Form(""),content:str=Form(""),category:str=Form("Novidades"),tags:str=Form(""),status:str=Form("draft"),publish_at:str=Form(""),seo_title:str=Form(""),seo_description:str=Form(""),image_alt:str=Form(""),image:Optional[UploadFile]=File(None)):
    u,role=allow(request,"admin","editor","author");s=slugify(slug or title);status=status if status in ("draft","published","scheduled") else "draft";fn=save_image(image);c=db()
    try:
        if post_id:
            old=c.execute("SELECT * FROM cms_posts WHERE id=?",(post_id,)).fetchone()
            if not old or (role=="author" and old["author_id"]!=u["id"]):raise HTTPException(403)
            fn=fn or old["image_filename"];c.execute("UPDATE cms_posts SET title=?,slug=?,excerpt=?,content=?,image_filename=?,image_alt=?,category=?,tags=?,status=?,publish_at=?,seo_title=?,seo_description=?,updated_at=? WHERE id=?",(title[:180],s,excerpt[:500],content,fn,image_alt[:200],category[:80],tags[:300],status,publish_at[:40],seo_title[:160],seo_description[:320],now_iso(),post_id))
        else:c.execute("INSERT INTO cms_posts(title,slug,excerpt,content,image_filename,image_alt,category,tags,status,publish_at,author_id,seo_title,seo_description,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(title[:180],s,excerpt[:500],content,fn,image_alt[:200],category[:80],tags[:300],status,publish_at[:40],u["id"],seo_title[:160],seo_description[:320],now_iso(),now_iso()))
        c.commit()
    except sqlite3.IntegrityError:c.rollback()
    c.close();return RedirectResponse("/admin/cms#blog",303)
@router.post("/admin/cms/posts/{pid}/excluir")
def post_del(request:Request,pid:int):
    u,r=allow(request,"admin","editor","author");c=db();p=c.execute("SELECT author_id FROM cms_posts WHERE id=?",(pid,)).fetchone()
    if p and (r!="author" or p["author_id"]==u["id"]):c.execute("DELETE FROM cms_posts WHERE id=?",(pid,));c.commit()
    c.close();return RedirectResponse("/admin/cms#blog",303)

@router.post("/admin/cms/comentarios/{cid}/{action}")
def comment_action(request:Request,cid:int,action:str):
    allow(request,"admin","editor");c=db()
    if action=="excluir":c.execute("DELETE FROM cms_comments WHERE id=?",(cid,))
    elif action in ("approved","spam","pending"):c.execute("UPDATE cms_comments SET status=? WHERE id=?",(action,cid))
    else:raise HTTPException(400)
    c.commit();c.close();return RedirectResponse("/admin/cms#comentarios",303)
@router.post("/admin/cms/leads/{lid}/{action}")
def lead_action(request:Request,lid:int,action:str):
    allow(request,"admin","editor");c=db()
    if action=="excluir":c.execute("DELETE FROM cms_leads WHERE id=?",(lid,))
    elif action in ("new","read","answered","archived"):c.execute("UPDATE cms_leads SET status=? WHERE id=?",(action,lid))
    else:raise HTTPException(400)
    c.commit();c.close();return RedirectResponse("/admin/cms#leads",303)
@router.get("/admin/cms/leads.csv")
def leads_csv(request:Request):
    allow(request,"admin","editor");c=db();rows=c.execute("SELECT name,email,phone,subject,message,status,created_at FROM cms_leads ORDER BY id DESC").fetchall();c.close();out=io.StringIO();w=csv.writer(out);w.writerow(["Nome","E-mail","Telefone","Assunto","Mensagem","Status","Data"]);w.writerows([tuple(r) for r in rows]);data='\ufeff'+out.getvalue();return StreamingResponse(iter([data.encode("utf-8")]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=contatos-nowup.csv"})

@router.post("/admin/cms/usuarios/salvar")
def user_save(request:Request,name:str=Form(...),email:str=Form(...),password:str=Form(...),cms_role_value:str=Form("editor")):
    allow(request,"admin");role=cms_role_value if cms_role_value in ("admin","editor","author") else "editor";c=db()
    try:
        cur=c.execute("INSERT INTO users(role,name,email,password_hash,email_verified,is_active,created_at) VALUES('admin',?,?,?,?,1,?)",(name[:120],email.strip().lower(),hash_password(password),1,now_iso()));c.execute("INSERT INTO cms_permissions(user_id,cms_role) VALUES(?,?)",(cur.lastrowid,role));c.commit()
    except sqlite3.IntegrityError:c.rollback()
    c.close();return RedirectResponse("/admin/cms#usuarios",303)
@router.post("/admin/cms/usuarios/{uid}/papel")
def user_role(request:Request,uid:int,cms_role_value:str=Form(...)):
    u,_=allow(request,"admin");role=cms_role_value if cms_role_value in ("admin","editor","author") else "editor"
    if uid==u["id"] and role!="admin":return RedirectResponse("/admin/cms#usuarios",303)
    c=db();c.execute("INSERT INTO cms_permissions(user_id,cms_role) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET cms_role=excluded.cms_role",(uid,role));c.commit();c.close();return RedirectResponse("/admin/cms#usuarios",303)

@router.get("/pagina/{slug}",response_class=HTMLResponse)
def public_page(request:Request,slug:str):
    c=db();p=c.execute("SELECT * FROM cms_pages WHERE slug=? AND status='published'",(slug,)).fetchone();c.close()
    if not p:raise HTTPException(404,"Página não encontrada")
    return templates.TemplateResponse("cms_page.html",public_context(request,page=p))
@router.get("/noticias",response_class=HTMLResponse)
def public_blog(request:Request):
    c=db();posts=c.execute("SELECT * FROM cms_posts WHERE status='published' OR (status='scheduled' AND publish_at!='' AND publish_at<=?) ORDER BY COALESCE(NULLIF(publish_at,''),created_at) DESC",(now_iso(),)).fetchall();c.close();return templates.TemplateResponse("cms_blog.html",public_context(request,posts=posts))
@router.get("/noticias/{slug}",response_class=HTMLResponse)
def public_post(request:Request,slug:str):
    c=db();p=c.execute("SELECT * FROM cms_posts WHERE slug=? AND (status='published' OR (status='scheduled' AND publish_at<=?))",(slug,now_iso())).fetchone()
    if not p:c.close();raise HTTPException(404,"Notícia não encontrada")
    comments=c.execute("SELECT * FROM cms_comments WHERE post_id=? AND status='approved' ORDER BY id DESC",(p["id"],)).fetchall();c.close();return templates.TemplateResponse("cms_post.html",public_context(request,post=p,comments=comments))
@router.post("/noticias/{pid}/comentar")
def public_comment(pid:int,name:str=Form(...),email:str=Form(""),comment:str=Form(...)):
    c=db();p=c.execute("SELECT slug FROM cms_posts WHERE id=?",(pid,)).fetchone()
    if p and name.strip() and comment.strip():c.execute("INSERT INTO cms_comments(post_id,name,email,comment,created_at) VALUES(?,?,?,?,?)",(pid,name[:100],email[:160],comment[:1500],now_iso()));c.commit()
    c.close();return RedirectResponse(f"/noticias/{p['slug']}?comentario=enviado" if p else "/noticias",303)
@router.get("/contato",response_class=HTMLResponse)
def contact_page(request:Request):return templates.TemplateResponse("cms_contact.html",public_context(request))
@router.post("/contato")
def contact_submit(name:str=Form(...),email:str=Form(""),phone:str=Form(""),subject:str=Form(""),message:str=Form(...)):
    c=db();c.execute("INSERT INTO cms_leads(name,email,phone,subject,message,created_at) VALUES(?,?,?,?,?,?)",(name[:120],email[:160],phone[:40],subject[:160],message[:3000],now_iso()));c.commit();c.close();return RedirectResponse("/contato?enviado=1",303)
