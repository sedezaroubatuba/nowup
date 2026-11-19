"""Comunicação lojista -> cliente, isolada por Cardápio Digital.

Não confunde autorização para avisos de pedidos com consentimento para promoções.
Disparos são feitos por fila durável, sempre revalidando loja, cliente e opt-in.
"""
from __future__ import annotations
import html
import json
import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlsplit
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

G = {}
STOP = threading.Event()
THREAD = None
LOG = logging.getLogger(__name__)
TZ = ZoneInfo("America/Sao_Paulo")
MAX_BANNER = 2 * 1024 * 1024


def esc(value):
    return html.escape(str(value or ""), quote=True)


def now():
    return datetime.now(timezone.utc).isoformat()


def setup():
    c = G["db"]()
    try:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS merchant_comms450(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
            kind TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
            image_filename TEXT NOT NULL DEFAULT '', link TEXT NOT NULL DEFAULT '',
            product_ids TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL, scheduled_at TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'scheduled', recipients INTEGER NOT NULL DEFAULT 0,
            sent INTEGER NOT NULL DEFAULT 0);
        CREATE INDEX IF NOT EXISTS idx_merchant_comms450_due
            ON merchant_comms450(state,scheduled_at);
        CREATE INDEX IF NOT EXISTS idx_merchant_comms450_store
            ON merchant_comms450(professional_id,id);
        CREATE TABLE IF NOT EXISTS merchant_comms450_consent(
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
            allowed INTEGER NOT NULL, version TEXT NOT NULL, updated_at TEXT NOT NULL,
            PRIMARY KEY(user_id,professional_id));
        CREATE TABLE IF NOT EXISTS merchant_comms450_devices(
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
            endpoint TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(user_id,professional_id,endpoint));
        CREATE TABLE IF NOT EXISTS merchant_comms450_deliveries(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL REFERENCES merchant_comms450(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            state TEXT NOT NULL DEFAULT 'pending', notified_at TEXT NOT NULL DEFAULT '',
            UNIQUE(campaign_id,user_id));
        CREATE INDEX IF NOT EXISTS idx_merchant_comms450_delivery
            ON merchant_comms450_deliveries(campaign_id,state,id);
        """)
        c.commit()
    finally:
        c.close()


def merchant(request):
    user = G["require_user"](request, "professional")
    c = G["db"]()
    try:
        p = G["require_premium_catalog"](c, user["id"])
        if p["plan_active"] not in ("cardapio", "completo", "ambos"):
            raise HTTPException(403, "Disponível somente no Cardápio Digital.")
        return dict(p)
    finally:
        c.close()


def store(slug):
    if not re.fullmatch(r"[a-z0-9_-]{1,100}", slug):
        raise HTTPException(404)
    c = G["db"]()
    try:
        p = c.execute("""SELECT * FROM professionals WHERE slug=? AND blocked=0
            AND admission_status='approved' AND is_premium=1
            AND plan_active IN ('cardapio','completo','ambos')""", (slug,)).fetchone()
        if not p:
            raise HTTPException(404, "Cardápio não encontrado.")
        return dict(p)
    finally:
        c.close()


def customer(request, p):
    # Garante que a sessão do Cardápio da loja é avaliada no escopo correto.
    request.state.scope_store345 = p
    request.state.store_app256 = p
    u = G["require_user"](request, "customer")
    if u.get("customer_store345") != p["id"]:
        raise HTTPException(403, "Este login pertence a outro cardápio.")
    return u


def products_for(c, p):
    return [dict(r) for r in c.execute(
        """SELECT id,name,image_filename,available,price_cents,promo_price_cents,category
           FROM products WHERE professional_id=? AND available=1 ORDER BY name,id LIMIT 2000""",
        (p["id"],))]


def visible_products(c, p, ids):
    if not ids:
        return []
    rows = [dict(r) for r in c.execute(
        "SELECT id,name,image_filename,price_cents,promo_price_cents,available FROM products WHERE professional_id=? AND id IN (" +
        ",".join("?" for _ in ids) + ")", [p["id"], *ids])]
    indexed = {r["id"]: r for r in rows if r["available"]}
    return [indexed[i] for i in ids if i in indexed]


def safe_link(raw):
    raw = (raw or "").strip()
    if not raw:
        return ""
    if len(raw) > 900:
        raise HTTPException(400, "Link muito longo.")
    p = urlsplit(raw)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise HTTPException(400, "Use apenas links HTTPS válidos.")
    return raw


def parse_schedule(value):
    if not value:
        return now()
    try:
        target = datetime.fromisoformat(value).replace(tzinfo=TZ).astimezone(timezone.utc)
    except ValueError:
        raise HTTPException(400, "Agendamento inválido.")
    delta = target - datetime.now(timezone.utc)
    if delta < timedelta(minutes=-2) or delta > timedelta(days=30):
        raise HTTPException(400, "Agende entre agora e os próximos 30 dias.")
    return target.isoformat()


def document(title, contents):
    return ("""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light">
<title>""" + esc(title) + """ · NowUp Cardápio</title><style>
:root{font-family:system-ui,-apple-system,sans-serif;color:#17132d;background:#f7f7fb}
*{box-sizing:border-box}body{margin:0}header{padding:18px 5%;background:#2a0c5c;color:#fff;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header b{font-size:21px}header a{color:#fff}.wrap{max-width:1120px;margin:24px auto;padding:0 16px}
.panel{background:#fff;border:1px solid #e8e4ee;border-radius:18px;padding:20px;margin-bottom:18px;box-shadow:0 4px 15px #2111390b}
h1{font-size:clamp(23px,5vw,32px);margin:0 0 10px}h2{font-size:19px}
.muted,small{color:#656177}.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(260px,.75fr);gap:20px}
label{display:block;font-weight:650;margin:15px 0 5px}input[type=text],input[type=url],input[type=datetime-local],textarea,select{display:block;width:100%;padding:13px;border:1px solid #d2cce0;border-radius:10px;font:inherit}
textarea{min-height:100px;resize:vertical}.radio{display:flex;gap:8px;align-items:center;padding:10px 0}.radio label{margin:0;font-weight:400}
button,.btn{display:inline-block;padding:12px 18px;border-radius:11px;border:0;color:#fff;background:#6b15d9;font-weight:700;text-decoration:none;cursor:pointer;font:inherit}
.btn-alt{background:#f1eafc;color:#481995}.btn-danger{background:#a41f37}button:disabled{opacity:.5}
.products{max-height:260px;overflow:auto;border:1px solid #ebe7f2;border-radius:10px;padding:9px}
.product{display:flex;align-items:center;gap:12px;border-bottom:1px solid #f0edf6;padding:7px 3px}
.product img,.thumb{width:55px;height:55px;object-fit:cover;border-radius:8px;background:#f4e9ff}
.product label{flex:1;font-weight:500;margin:0}.pill{display:inline-block;border-radius:40px;padding:4px 9px;background:#f1eafb;color:#541a9f;font-size:12px}
.preview{border:1px solid #d8cfeb;background:#faf7ff;border-radius:18px;padding:18px;overflow-wrap:anywhere}
.preview img{max-width:100%;border-radius:12px}article{border-bottom:1px solid #eee8f2;padding:12px 0}
article:last-child{border:0}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}
.cards article{border:1px solid #e5ddef;padding:12px;border-radius:14px}
.cards img{width:100%;height:125px;object-fit:cover;border-radius:10px}
@media(max-width:750px){.grid{grid-template-columns:1fr}header{padding:15px}.wrap{margin:12px auto}.panel{padding:16px}}
</style></head><body><header><b>✦ NowUp · Cardápio Digital</b>""" +
         contents + "</body></html>")


def push_url(p, campaign_id):
    return "/p/" + quote(p["slug"], safe="") + "/comunicados/" + str(campaign_id)


def worker_once():
    c = G["db"]()
    try:
        # Aguardar o horário, conferir opt-in por loja e nunca reutilizar público da Vitrine.
        due = [dict(r) for r in c.execute(
            "SELECT * FROM merchant_comms450 WHERE state IN ('scheduled','sending') AND scheduled_at<=? ORDER BY id LIMIT 5",
            (now(),))]
        for item in due:
            p = c.execute("""SELECT id,slug,blocked,admission_status,plan_active FROM professionals
                WHERE id=?""", (item["professional_id"],)).fetchone()
            if not p or p["blocked"] or p["admission_status"] != "approved" or p["plan_active"] not in ("cardapio", "completo", "ambos"):
                c.execute("UPDATE merchant_comms450 SET state='paused' WHERE id=?", (item["id"],))
                c.commit()
                continue
            if item["state"] == "scheduled":
                # Cliente precisa ter consentimento específico; apenas ativar push de pedidos não autoriza marketing.
                users = c.execute("""SELECT u.id FROM users u
                    JOIN merchant_comms450_consent pref
                      ON pref.user_id=u.id AND pref.professional_id=? AND pref.allowed=1 AND pref.version='v450'
                    WHERE u.customer_store345=? AND u.role='customer' AND u.is_active=1 AND u.email_verified=1""",
                    (p["id"], p["id"])).fetchall()
                for u in users:
                    c.execute("INSERT OR IGNORE INTO merchant_comms450_deliveries(campaign_id,user_id) VALUES(?,?)",
                              (item["id"], u["id"]))
                c.execute("UPDATE merchant_comms450 SET state='sending',recipients=? WHERE id=?",
                          (len(users),item["id"]))
                c.commit()
            recipients = c.execute("""SELECT d.id,d.user_id FROM merchant_comms450_deliveries d
                JOIN users u ON u.id=d.user_id
                JOIN merchant_comms450_consent pref ON pref.user_id=u.id
                   AND pref.professional_id=? AND pref.allowed=1 AND pref.version='v450'
                WHERE d.campaign_id=? AND d.state='pending'
                  AND u.customer_store345=? AND u.role='customer' AND u.is_active=1 AND u.email_verified=1
                ORDER BY d.id LIMIT 40""", (p["id"],item["id"],p["id"])).fetchall()
            for r in recipients:
                link = push_url(p,item["id"])
                notice = c.execute(
                    "INSERT INTO notifications(user_id,title,message,link,created_at) VALUES(?,?,?,?,?)",
                    (r["user_id"], item["title"], item["body"], link, now()))
                payload = {"title":item["title"],"body":item["body"][:180],"url":link,
                           "tag":"nowup-com450-" + str(item["id"])}
                if item["image_filename"]:
                    payload["image"] = "/uploads/" + item["image_filename"]
                else:
                    selection = visible_products(c, p, json.loads(item["product_ids"])[:1])
                    if selection and selection[0]["image_filename"]:
                        payload["image"] = "/uploads/" + selection[0]["image_filename"]
                G["nowup_alerts112"].enqueue(c, r["user_id"], notice.lastrowid, payload)
                c.execute("UPDATE merchant_comms450_deliveries SET state='sent',notified_at=? WHERE id=?",
                          (now(),r["id"]))
                c.commit()
            # Opt-outs após a criação da lista são descartados, não enviados.
            c.execute("""UPDATE merchant_comms450_deliveries SET state='skipped'
                WHERE campaign_id=? AND state='pending' AND user_id NOT IN
                (SELECT u.id FROM users u JOIN merchant_comms450_consent pref ON pref.user_id=u.id
                 WHERE pref.professional_id=? AND pref.allowed=1 AND pref.version='v450'
                   AND u.customer_store345=? AND u.is_active=1 AND u.email_verified=1)""",
                (item["id"],p["id"],p["id"]))
            count = c.execute("SELECT COUNT(*) FROM merchant_comms450_deliveries WHERE campaign_id=? AND state='sent'",
                              (item["id"],)).fetchone()[0]
            remaining = c.execute("SELECT COUNT(*) FROM merchant_comms450_deliveries WHERE campaign_id=? AND state='pending'",
                                  (item["id"],)).fetchone()[0]
            c.execute("UPDATE merchant_comms450 SET sent=?,state=? WHERE id=?",
                      (count,"sending" if remaining else "sent",item["id"]))
            c.commit()
    finally:
        c.close()


def worker():
    while not STOP.wait(10):
        try:
            worker_once()
        except Exception:
            LOG.exception("Fila de comunicados: erro; nova tentativa no próximo ciclo.")


def start():
    global THREAD
    setup()
    STOP.clear()
    if THREAD is None or not THREAD.is_alive():
        THREAD = threading.Thread(target=worker, daemon=True, name="comunicados450")
        THREAD.start()


def stop():
    STOP.set()
    if THREAD:
        THREAD.join(timeout=2)


def install(g):
    global G
    G = g
    app = g["app"]
    app.router.add_event_handler("startup", start)
    app.router.add_event_handler("shutdown", stop)

    @app.get("/painel/comunicacao-clientes", response_class=HTMLResponse)
    def settings_page(request: Request):
        p = merchant(request)
        c = g["db"]()
        try:
            products = products_for(c,p)
            history = [dict(r) for r in c.execute(
                "SELECT * FROM merchant_comms450 WHERE professional_id=? ORDER BY id DESC LIMIT 30",(p["id"],))]
            total = c.execute("""SELECT COUNT(*) FROM merchant_comms450_consent pref
                JOIN users u ON u.id=pref.user_id WHERE pref.professional_id=?
                AND pref.allowed=1 AND pref.version='v450' AND u.customer_store345=? AND u.is_active=1""",
                (p["id"],p["id"])).fetchone()[0]
        finally:
            c.close()
        options = "".join('<div class="product"><input type="checkbox" name="product_ids" value="' + str(x["id"]) +
            '" id="prod450-' + str(x["id"]) + '"><img src="' +
            ("/uploads/"+esc(x["image_filename"]) if x["image_filename"] else "/static/nowup-logo185.png") +
            '" alt=""><label for="prod450-' + str(x["id"]) + '">' + esc(x["name"]) +
            ' <small>R$ ' + ("%0.2f"%(g["current_price"](x)/100)).replace(".",",") + '</small></label></div>'
            for x in products)
        history_html = "".join('<article><span class="pill">' + esc(row["kind"]) + '</span> <b>' +
             esc(row["title"]) + '</b><p class="muted">' + esc(datetime.fromisoformat(row["created_at"]).astimezone(TZ).strftime("%d/%m/%Y %H:%M")) +
             " · " + esc(row["state"]) + " · " + str(row["sent"]) + " cliente(s) com aviso registrado; o push pode ainda estar na fila</p></article>"
             for row in history) or "<p>Nenhum comunicado enviado ainda.</p>"
        body = '<a href="/painel">← Voltar ao painel</a></header><div class="wrap"><h1>📣 Comunicação com clientes</h1><p class="muted">Configurações do Cardápio Digital · ' + esc(p["display_name"]) + '</p>'
        body += '<div class="grid"><section class="panel"><h2>Novo comunicado</h2><p class="pill">' + str(total) + ' clientes inscritos</p>'
        body += '<form action="/painel/comunicacao-clientes/enviar" method="post" enctype="multipart/form-data" id="com450-form">'
        body += '<label>Tipo de comunicado</label><select name="kind"><option value="aviso">Aviso da loja / entregas</option><option value="promocao">Promoção / novidades</option><option value="mensagem">Mensagem livre</option></select>'
        body += '<label>Título</label><input name="title" type="text" maxlength="60" required placeholder="Chegou nosso novo combo!">'
        body += '<label>Mensagem</label><textarea name="body" required maxlength="240" placeholder="Boa noite! Confira nossas novidades..."></textarea>'
        body += '<label>Selecionar produtos do meu cardápio (opcional, até 12)</label><input type="text" id="com450-search" placeholder="Buscar produto ou combo..."><div class="products" id="com450-products">' + options + '</div>'
        body += '<label>Banner / arte própria (opcional)</label><input type="file" name="banner" accept="image/jpeg,image/png,image/webp"><small>JPG, PNG ou WebP, até 2 MB. Se não escolher, será apenas texto e produtos.</small>'
        body += '<label>Link adicional (opcional)</label><input name="link" type="url" placeholder="https://..." maxlength="900">'
        body += '<label>Agendar envio (opcional)</label><input type="datetime-local" name="scheduled">'
        body += '<p class="muted">Mensagens e promoções somente para clientes que autorizaram. Limite: até 3 comunicados em 24 horas; espaçamento mínimo de 30 minutos.</p>'
        body += '<button type="submit">Enviar ou agendar comunicado</button></form></section>'
        body += '<section class="panel"><h2>Prévia para o cliente</h2><div class="preview"><b id="com450-preview-title">Título da comunicação</b><p id="com450-preview-body">Sua mensagem aparecerá aqui.</p><img id="com450-preview-img" hidden alt="Prévia da arte"></div>'
        body += '<p class="muted">O banner e os produtos aparecerão na página de novidades. O sistema pode exibir uma imagem junto ao push se o aparelho permitir.</p><a class="btn btn-alt" href="/p/'+esc(p["slug"])+'/comunicados">Ver comunicados da loja</a>'
        body += '<h2>Histórico</h2>' + history_html + '</section></div></div>'
        body += r"""<script>
(() => {
 const f=document.getElementById('com450-form');
 const preview=()=>{document.getElementById('com450-preview-title').textContent=f.elements.title.value||'Título da comunicação';document.getElementById('com450-preview-body').textContent=f.elements.body.value||'Sua mensagem aparecerá aqui.'};
 f.elements.title.addEventListener('input',preview);f.elements.body.addEventListener('input',preview);
 document.getElementById('com450-search').addEventListener('input',e=>{const term=e.target.value.toLocaleLowerCase('pt-BR');document.querySelectorAll('#com450-products .product').forEach(n=>{n.hidden=!n.textContent.toLocaleLowerCase('pt-BR').includes(term)});});
 f.elements.banner.addEventListener('change',e=>{const file=e.target.files[0],img=document.getElementById('com450-preview-img');if(!file){img.hidden=true;return}if(file.size>2097152){alert('Imagem maior que 2 MB.');e.target.value='';img.hidden=true;return}img.src=URL.createObjectURL(file);img.hidden=false;});
 f.addEventListener('submit',e=>{const chosen=f.querySelectorAll('input[name=product_ids]:checked');if(chosen.length>12){e.preventDefault();alert('Selecione no máximo 12 produtos.')}else if(!confirm('Confirma este comunicado para os clientes inscritos?'))e.preventDefault()});
})();
</script>"""
        return HTMLResponse(document("Comunicação com clientes",body),headers={"Cache-Control":"private, no-store"})

    @app.post("/painel/comunicacao-clientes/enviar")
    async def send_campaign(request: Request, title: str=Form(...), body: str=Form(...),
                            kind: str=Form("mensagem"), product_ids: list[int]=Form(default=[]),
                            banner: UploadFile | None=File(None),
                            link: str=Form(""), scheduled: str=Form("")):
        from nowup_sales107 import check_origin
        check_origin(request)
        p = merchant(request)
        title = title.strip()
        body = body.strip()
        if kind not in ("aviso","promocao","mensagem") or not (1<=len(title)<=60) or not (1<=len(body)<=240):
            raise HTTPException(400,"Preencha o título e a mensagem dentro dos limites.")
        ids = list(dict.fromkeys(product_ids))
        if len(ids)>12 or any(i<=0 for i in ids):
            raise HTTPException(400,"Selecione até 12 produtos cadastrados.")
        target=safe_link(link)
        when=parse_schedule(scheduled)
        c=g["db"]()
        try:
            existing=visible_products(c,p,ids)
            if len(existing)!=len(ids):
                raise HTTPException(400,"Um produto não pertence à sua loja ou está indisponível.")
            # Operação limitada para proteger clientes contra excesso de notificações.
            recent=c.execute("""SELECT scheduled_at FROM merchant_comms450
                WHERE professional_id=? AND state!='cancelled' AND created_at>=? ORDER BY created_at DESC""",
                (p["id"],(datetime.now(timezone.utc)-timedelta(hours=24)).isoformat())).fetchall()
            if len(recent)>=3:
                raise HTTPException(429,"Limite de 3 comunicados em 24 horas. Tente mais tarde.")
            for x in recent:
                try:
                    if abs((datetime.fromisoformat(x["scheduled_at"])-datetime.fromisoformat(when)).total_seconds())<1800:
                        raise HTTPException(429,"Mantenha 30 minutos entre comunicados.")
                except ValueError:
                    continue
            filename=""
            if banner and banner.filename:
                if banner.size is not None and banner.size>MAX_BANNER:
                    raise HTTPException(413,"Imagem maior que 2 MB.")
                filedata=await banner.read(MAX_BANNER+1)
                if len(filedata)>MAX_BANNER:
                    raise HTTPException(413,"Imagem maior que 2 MB.")
                if banner.content_type not in ("image/jpeg","image/png","image/webp"):
                    raise HTTPException(400,"Use JPG, PNG ou WebP.")
                await banner.seek(0)
                filename=g["save_image"](banner)
            cur=c.execute("""INSERT INTO merchant_comms450
                (professional_id,kind,title,body,image_filename,link,product_ids,created_at,scheduled_at)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (p["id"],kind,title,body,filename,target,json.dumps(ids),now(),when))
            c.commit()
            campaign_id=cur.lastrowid
        finally:
            c.close()
        return RedirectResponse("/painel/comunicacao-clientes?novo="+str(campaign_id),303)

    @app.get("/p/{slug}/comunicados", response_class=HTMLResponse)
    def customer_center(request: Request, slug: str):
        p=store(slug)
        request.state.store_app256=p
        request.state.scope_store345=p
        user=g["current_user"](request)
        has_access=bool(user and user["role"]=="customer" and user.get("customer_store345")==p["id"])
        c=g["db"]()
        try:
            records=[dict(x) for x in c.execute("""SELECT * FROM merchant_comms450
                WHERE professional_id=? AND state IN ('sent','sending')
                ORDER BY id DESC LIMIT 30""",(p["id"],))]
            optin = bool(has_access and c.execute(
                "SELECT 1 FROM merchant_comms450_consent WHERE user_id=? AND professional_id=? AND allowed=1 AND version='v450'",
                (user["id"],p["id"])).fetchone())
        finally:
            c.close()
        posts="".join('<article><span class="pill">'+esc(r["kind"])+'</span><h2><a href="/p/'+esc(p["slug"])+'/comunicados/'+str(r["id"])+'">'+esc(r["title"])+'</a></h2><p>'+esc(r["body"])+'</p>'+
            ('<img class="thumb" src="/uploads/'+esc(r["image_filename"])+'" alt="Arte do comunicado">' if r["image_filename"] else "")+'</article>'
            for r in records) or "<p>Esta loja ainda não publicou comunicados.</p>"
        body='<a href="/p/'+esc(p["slug"])+'/cardapio">← Ver cardápio</a></header><main class="wrap"><h1>🔔 Avisos e novidades · '+esc(p["display_name"])+'</h1><section class="panel"><h2>Receber avisos deste cardápio</h2>'
        if has_access:
            body += ('<p class="pill">Você autorizou mensagens promocionais.</p>' if optin else '<p>Você pode permitir notificações de promoções e comunicados deste estabelecimento. Os avisos de pedidos são independentes.</p>')
            body += '<button type="button" id="com450-subscribe" '+('hidden' if optin else '')+'>🔔 Autorizar novidades neste aparelho</button> '
            body += '<button type="button" class="btn btn-alt" id="com450-unsubscribe" '+('' if optin else 'hidden')+'>Cancelar promoções</button><p id="com450-status" role="status"></p>'
        else:
            body += '<p>Para receber novidades, entre como cliente desta loja e autorize as notificações.</p><a class="btn" href="/p/'+esc(p["slug"])+'/entrar">Entrar como cliente</a>'
        body += '</section><section class="panel"><h2>Comunicados da loja</h2>'+posts+'</section></main>'
        if has_access:
            body += r"""<script>
(() => {
 const root=location.pathname.replace(/\/$/,''),msg=document.getElementById('com450-status'),on=document.getElementById('com450-subscribe'),off=document.getElementById('com450-unsubscribe');
 const key=s=>Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-s.length%4)%4)),c=>c.charCodeAt(0));
 async function api(url,data){const r=await fetch(url,{method:data?'POST':'GET',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:data?JSON.stringify(data):undefined});const j=await r.json();if(!r.ok)throw new Error(j.detail||'Não foi possível concluir.');return j;}
 on?.addEventListener('click',async()=>{on.disabled=true;try{
 if(!window.isSecureContext||!('serviceWorker' in navigator)||!('PushManager' in window))throw new Error('Use um navegador compatível com push. No iPhone, abra o ícone da Tela de Início.');
 if(await Notification.requestPermission()!=='granted')throw new Error('Permita notificações nas configurações do aparelho.');
 const cfg=await api(root+'/push-chave');
 const storeRoot=root.slice(0,-'/comunicados'.length)+'/';
 const reg=await navigator.serviceWorker.register(storeRoot+'service-worker355.js',{scope:storeRoot});
 await navigator.serviceWorker.ready;
 let sub=await reg.pushManager.getSubscription();if(!sub)sub=await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:key(cfg.publicKey)});
 await api(root+'/assinar',sub.toJSON());msg.textContent='Novidades desta loja ativadas!';on.hidden=true;off.hidden=false;
 }catch(e){msg.textContent=e.message;}finally{on.disabled=false;}});
 off?.addEventListener('click',async()=>{off.disabled=true;try{await api(root+'/cancelar',{});msg.textContent='Promoções desativadas. Avisos de pedidos continuam independentes.';off.hidden=true;on.hidden=false;}catch(e){msg.textContent=e.message;}finally{off.disabled=false;}});
})();
</script>"""
        return HTMLResponse(document("Novidades da loja",body),headers={"Cache-Control":"private, no-store"})

    @app.get("/p/{slug}/comunicados/push-chave")
    def customer_key(request:Request,slug:str):
        p=store(slug)
        customer(request,p)
        return JSONResponse({"publicKey":g["nowup_push75"].keys()[1]})

    @app.post("/p/{slug}/comunicados/assinar")
    async def customer_subscribe(request:Request,slug:str):
        from nowup_sales107 import check_origin
        check_origin(request)
        p=store(slug)
        u=customer(request,p)
        data=g["nowup_push75"].validate(await request.json())
        session=g["nowup_push75"].session(request)
        c=g["db"]()
        try:
            old=c.execute("SELECT user_id FROM push_subscriptions WHERE endpoint=?",(data["endpoint"],)).fetchone()
            if old and old["user_id"]!=u["id"]:
                raise HTTPException(409,"Este aparelho está vinculado a outra conta. Saia dela antes de ativar.")
            count=c.execute("SELECT COUNT(*) FROM push_subscriptions WHERE user_id=?",(u["id"],)).fetchone()[0]
            if not old and count>=10:
                raise HTTPException(400,"Máximo de 10 aparelhos por conta.")
            c.execute("INSERT OR REPLACE INTO push_subscriptions VALUES(?,?,?,?)",
                      (data["endpoint"],u["id"],session,json.dumps(data)))
            c.execute("""INSERT INTO merchant_comms450_devices(user_id,professional_id,endpoint,created_at)
                VALUES(?,?,?,?) ON CONFLICT(user_id,professional_id,endpoint)
                DO UPDATE SET created_at=excluded.created_at""",(u["id"],p["id"],data["endpoint"],now()))
            c.execute("""INSERT INTO merchant_comms450_consent VALUES(?,?,?,?,?)
                ON CONFLICT(user_id,professional_id) DO UPDATE SET
                  allowed=excluded.allowed,version=excluded.version,updated_at=excluded.updated_at""",
                (u["id"],p["id"],1,"v450",now()))
            c.commit()
        finally:
            c.close()
        return {"ok":True}

    @app.post("/p/{slug}/comunicados/cancelar")
    def customer_unsubscribe(request:Request,slug:str):
        from nowup_sales107 import check_origin
        check_origin(request)
        p=store(slug)
        u=customer(request,p)
        c=g["db"]()
        try:
            c.execute("""INSERT INTO merchant_comms450_consent VALUES(?,?,?,?,?)
                ON CONFLICT(user_id,professional_id) DO UPDATE SET allowed=0,updated_at=excluded.updated_at""",
                (u["id"],p["id"],0,"v450",now()))
            c.execute("DELETE FROM merchant_comms450_devices WHERE user_id=? AND professional_id=?",
                      (u["id"],p["id"]))
            c.commit()
        finally:
            c.close()
        return {"ok":True}

    @app.get("/p/{slug}/comunicados/{campaign_id}", response_class=HTMLResponse)
    def campaign_page(request:Request,slug:str,campaign_id:int):
        p=store(slug)
        c=g["db"]()
        try:
            r=c.execute("""SELECT * FROM merchant_comms450
                WHERE id=? AND professional_id=? AND state IN ('sent','sending')""",
                (campaign_id,p["id"])).fetchone()
            if not r:
                raise HTTPException(404,"Comunicado indisponível.")
            r=dict(r)
            ids=json.loads(r["product_ids"])
            products=visible_products(c,p,ids)
        finally:
            c.close()
        cards="".join('<article><img src="'+("/uploads/"+esc(x["image_filename"]) if x["image_filename"] else "/static/nowup-logo185.png")+'" alt=""><h2>'+esc(x["name"])+'</h2><b>R$ '+("%0.2f"%(g["current_price"](x)/100)).replace(".",",")+'</b><p><a class="btn" href="/p/'+esc(p["slug"])+'/cardapio#produto-'+str(x["id"])+'">Ver no cardápio</a></p></article>' for x in products)
        body='<a href="/p/'+esc(p["slug"])+'/comunicados">← Outros comunicados</a></header><main class="wrap"><section class="panel"><span class="pill">'+esc(r["kind"])+'</span><h1>'+esc(r["title"])+'</h1><p>'+esc(r["body"])+'</p>'
        if r["image_filename"]:
            body+='<img style="max-width:100%;max-height:360px;object-fit:contain;border-radius:14px" src="/uploads/'+esc(r["image_filename"])+'" alt="Banner da loja">'
        if cards:
            body+='<h2>Produtos selecionados</h2><div class="cards">'+cards+'</div>'
        if r["link"]:
            body+='<p><a class="btn" href="'+esc(r["link"])+'" rel="nofollow noopener noreferrer" target="_blank">Abrir link da loja</a></p>'
        body+='<p><a class="btn btn-alt" href="/p/'+esc(p["slug"])+'/cardapio">Abrir cardápio completo</a></p></section></main>'
        return HTMLResponse(document(r["title"],body))
