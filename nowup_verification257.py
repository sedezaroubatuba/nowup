"""Private merchant evidence and manual review; no automatic identity claim."""
import base64
import io
import re
from fastapi import HTTPException, Request, Form, UploadFile, File
from fastapi.responses import Response, RedirectResponse
from PIL import Image, ImageOps

FIELDS = {'legal_name':'Razão social', 'owner_name':'Responsável', 'owner_cpf':'CPF do responsável', 'owner_role':'Vínculo com a empresa'}
DOCS = {'facade':'Foto da fachada', 'company':'Comprovante do CNPJ', 'identity':'Documento do responsável', 'address_proof':'Comprovante de endereço comercial'}
G = {}

def valid_doc(raw, size):
    value = re.sub(r'[^0-9]', '', raw or '')
    if len(value) != size or len(set(value)) == 1: return False
    weights = ([5,4,3,2,9,8,7,6,5,4,3,2], [6,5,4,3,2,9,8,7,6,5,4,3,2]) if size == 14 else (list(range(10,1,-1)),list(range(11,1,-1)))
    for n,w in enumerate(weights):
        remainder = sum(int(x)*y for x,y in zip(value[:size-2+n], w)) % 11
        if int(value[size-2+n]) != (0 if remainder < 2 else 11-remainder): return False
    return True

def initialize():
    with G['db']() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS merchant_evidence257(
          professional_id INTEGER PRIMARY KEY REFERENCES professionals(id) ON DELETE CASCADE,
          legal_name TEXT NOT NULL, owner_name TEXT NOT NULL, owner_cpf TEXT NOT NULL,
          owner_role TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', reason TEXT DEFAULT '',
          reviewed_by INTEGER, reviewed_at TEXT DEFAULT '');
          CREATE TABLE IF NOT EXISTS merchant_documents257(
          professional_id INTEGER NOT NULL REFERENCES professionals(id) ON DELETE CASCADE,
          kind TEXT NOT NULL, content TEXT NOT NULL, mime TEXT NOT NULL,
          PRIMARY KEY(professional_id,kind));
          CREATE TABLE IF NOT EXISTS merchant_audit257(
          professional_id INTEGER NOT NULL, actor INTEGER NOT NULL, action TEXT NOT NULL, created_at TEXT NOT NULL);''')

def evidence(fields, uploads, document):
    if not valid_doc(document,14): raise HTTPException(400,'Informe um CNPJ válido. A situação cadastral será conferida manualmente.')
    if not all(str(fields.get(k,'')).strip() for k in FIELDS) or not valid_doc(fields['owner_cpf'],11):
        raise HTTPException(400,'Preencha razão social, nome, CPF válido e vínculo do responsável.')
    result = {}
    for kind in DOCS:
        upload = uploads.get(kind)
        if not upload or not upload.filename: raise HTTPException(400,'Anexe: '+DOCS[kind])
        raw = upload.file.read(5*1024*1024+1)
        if len(raw)>5*1024*1024: raise HTTPException(400,'Cada anexo deve ter até 5 MB.')
        try:
            im=Image.open(io.BytesIO(raw))
            if im.format not in ('JPEG','PNG','WEBP') or im.width*im.height>16000000: raise ValueError()
            im=ImageOps.exif_transpose(im).convert('RGB'); im.thumbnail((2200,2200))
            out=io.BytesIO(); im.save(out,'JPEG',quality=88)
        except Exception: raise HTTPException(400,'Anexe fotos JPG, PNG ou WebP legíveis, de até 16 megapixels.')
        result[kind]=base64.b64encode(out.getvalue()).decode('ascii')
    return result

def save(c,pid,fields,documents):
    c.execute('INSERT INTO merchant_evidence257(professional_id,legal_name,owner_name,owner_cpf,owner_role) VALUES(?,?,?,?,?)',(pid,*(fields[k].strip()[:180] for k in FIELDS)))
    for kind,content in documents.items(): c.execute('INSERT INTO merchant_documents257 VALUES(?,?,?,?)',(pid,kind,content,'image/jpeg'))

def require_review(c,pid):
    row=c.execute('SELECT status FROM merchant_evidence257 WHERE professional_id=?',(pid,)).fetchone()
    # Previously registered stores keep their existing approval; new registrations require evidence review.
    if row and row['status']!='verified': raise HTTPException(400,'Confira os anexos em Verificação de lojistas antes de aprovar a loja.')

def register(g):
    G.update(g); app=g['app']; app.add_event_handler('startup',initialize)
    def admin(request,c):
        import nowup_admin227 as adm
        actor=adm.auth(request,c,'stores')
        if not actor['super']: raise HTTPException(403,'Documentos restritos ao Super ADM')
        return actor
    @app.get('/admin/verificacao-lojistas')
    def listing(request:Request):
        c=g['db']()
        try:
            admin(request,c)
            stores=c.execute('SELECT p.id,p.display_name,p.document,p.address,p.city,p.neighborhood,p.whatsapp,u.email,e.* FROM merchant_evidence257 e JOIN professionals p ON p.id=e.professional_id JOIN users u ON u.id=p.user_id ORDER BY p.id DESC').fetchall()
            return g['templates'].TemplateResponse('merchant_verification257.html',g['context'](request,stores=stores,fields257=FIELDS,docs257=DOCS))
        finally:c.close()
    @app.get('/admin/verificacao-lojistas/{pid}/documentos/{kind}')
    def download(request:Request,pid:int,kind:str):
        c=g['db']()
        try:
            a=admin(request,c)
            row=c.execute('SELECT * FROM merchant_documents257 WHERE professional_id=? AND kind=?',(pid,kind)).fetchone()
            if not row: raise HTTPException(404)
            c.execute('INSERT INTO merchant_audit257 VALUES(?,?,?,?)',(pid,a['id'],'view:'+kind,g['now_iso']()));c.commit()
            return Response(base64.b64decode(row['content']),media_type='image/jpeg',headers={'Cache-Control':'private, no-store','Content-Disposition':'inline; filename="documento.jpg"'})
        finally:c.close()
    @app.post('/admin/verificacao-lojistas/{pid}')
    def review(request:Request,pid:int,decision:str=Form(...),reason:str=Form(...),checked:str=Form('')):
        if decision not in ('verified','correction','rejected') or len(reason.strip())<8: raise HTTPException(400,'Escolha uma decisão e registre o motivo.')
        if decision=='verified' and checked!='1': raise HTTPException(400,'Confirme a conferência da empresa e do responsável.')
        c=g['db']()
        try:
            a=admin(request,c)
            if not c.execute('SELECT 1 FROM merchant_evidence257 WHERE professional_id=?',(pid,)).fetchone():raise HTTPException(404)
            c.execute('UPDATE merchant_evidence257 SET status=?,reason=?,reviewed_by=?,reviewed_at=? WHERE professional_id=?',(decision,reason.strip()[:1000],a['id'],g['now_iso'](),pid))
            if decision!='verified':c.execute("UPDATE professionals SET blocked=1,admission_status='pending',verified=0 WHERE id=?",(pid,))
            c.execute('INSERT INTO merchant_audit257 VALUES(?,?,?,?)',(pid,a['id'],decision+':'+reason.strip()[:1000],g['now_iso']()));c.commit()
        finally:c.close()
        return RedirectResponse('/admin/verificacao-lojistas',303)

    @app.get('/painel/documentos')
    def merchant_page(request:Request):
        u=g['require_user'](request,'professional');c=g['db']()
        try:
            p=c.execute('SELECT p.id,p.document,e.* FROM professionals p LEFT JOIN merchant_evidence257 e ON e.professional_id=p.id WHERE p.user_id=?',(u['id'],)).fetchone()
            if not p: raise HTTPException(404)
            return g['templates'].TemplateResponse('merchant_documents257.html',g['context'](request,p=p,fields257=FIELDS,docs257=DOCS))
        finally:c.close()
    @app.post('/painel/documentos')
    def resubmit(request:Request,legal_name:str=Form(...),owner_name:str=Form(...),owner_cpf:str=Form(...),owner_role:str=Form(...),facade:UploadFile=File(...),company:UploadFile=File(...),identity:UploadFile=File(...),address_proof:UploadFile=File(...)):
        u=g['require_user'](request,'professional');c=g['db']()
        try:
            p=c.execute('SELECT p.id,p.document,e.status FROM professionals p LEFT JOIN merchant_evidence257 e ON e.professional_id=p.id WHERE p.user_id=?',(u['id'],)).fetchone()
            if not p or p['status'] not in ('correction','pending'):raise HTTPException(400,'Reenvio disponível após solicitação de correção ou enquanto aguarda análise.')
            fields=dict(legal_name=legal_name,owner_name=owner_name,owner_cpf=owner_cpf,owner_role=owner_role)
            docs=evidence(fields,dict(facade=facade,company=company,identity=identity,address_proof=address_proof),p['document'])
            c.execute('DELETE FROM merchant_documents257 WHERE professional_id=?',(p['id'],))
            c.execute('DELETE FROM merchant_evidence257 WHERE professional_id=?',(p['id'],))
            save(c,p['id'],fields,docs)
            c.execute('INSERT INTO merchant_audit257 VALUES(?,?,?,?)',(p['id'],u['id'],'resubmitted',g['now_iso']()));c.commit()
        finally:c.close()
        return RedirectResponse('/painel/documentos',303)
