"""Private encrypted KYC documents; document checks do not verify identity."""
import base64,hashlib,hmac,io,os,secrets,time
from pathlib import Path
from fastapi import APIRouter,HTTPException,Request,UploadFile,File,Form
from fastapi.responses import Response
import nowup_billing228 as billing
router=APIRouter();G={}
def configure(g):G.update(g)
def directory():
    path=Path(os.getenv('NOWUP_KYC_DIR',str(Path(G['db_path']).parent/'kyc-private')));path.mkdir(mode=0o700,parents=True,exist_ok=True);return path

def auth(request,c,store,review=False,write=False):
    user=G['current_user'](request)
    if not review and user and user['role']=='professional':
        if c.execute('SELECT 1 FROM professionals WHERE id=? AND user_id=?',(store,user['id'])).fetchone():return user
    actor=G['admin'].auth(request,c,'stores')
    if (review or write) and not actor['super'] and 'stores' not in actor['permissions']:raise HTTPException(403,'Permissão de escrita necessária para KYC')
    return actor

def signature(doc,expires):
    return hmac.new(os.environ['NOWUP_JWT_SECRET'].encode(),f'kyc:{doc}:{expires}'.encode(),hashlib.sha256).hexdigest()

@router.post('/admin/super/api/stores/{store}/kyc')
@router.post('/api/stores/{store}/kyc')
async def upload(request:Request,store:int,doc_type:str=Form(...),file:UploadFile=File(...)):
    origin=request.headers.get('origin','')
    from urllib.parse import urlsplit
    if urlsplit(origin).netloc!=request.headers.get('host'):raise HTTPException(403,'Origem inválida')
    if doc_type not in ('identity','business','address','facade','selfie'):raise HTTPException(422,'Tipo de documento inválido')
    with connection() as c:auth(request,c,store,write=True)
    content=await file.read(5*1024*1024+1)
    if not content or len(content)>5*1024*1024:raise HTTPException(413,'Máximo de 5 MB')
    mime='application/pdf' if content.startswith(b'%PDF-') else 'image/png' if content.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if content.startswith(b'\xff\xd8\xff') else None
    if mime is None:raise HTTPException(422,'Envie PDF, JPG ou PNG')
    from nowup_backup import protect_private
    filename=secrets.token_hex(24)+'.enc';path=directory()/filename
    path.write_bytes(protect_private(content));os.chmod(path,0o600)
    try:
        with connection() as c:
            auth(request,c,store,write=True)
            cur=c.execute('INSERT INTO kyc_docs(store_id,doc_type,file_path_encrypted,status,created_at) VALUES(?,?,?,\'pending\',?)',(store,doc_type,protect_private(filename.encode()).decode(),billing.stamp()))
            c.execute("UPDATE professionals SET kyc_status='pending' WHERE id=?",(store,));billing.audit(c,store,'upload','Documento recebido: '+doc_type)
            return {'id':cur.lastrowid,'status':'pending'}
    except Exception:path.unlink(missing_ok=True);raise

@router.get('/admin/super/api/stores/{store}/kyc')
@router.get('/api/stores/{store}/kyc')
def listing(request:Request,store:int):
    with connection() as c:
        auth(request,c,store)
        return {'items':[dict(r) for r in c.execute('SELECT id,doc_type,status,created_at,reviewed_at FROM kyc_docs WHERE store_id=? ORDER BY id DESC',(store,))]}

@router.get('/admin/super/api/kyc/{doc}/url')
@router.get('/api/kyc/{doc}/url')
def signed_url(request:Request,doc:int):
    with connection() as c:
        row=c.execute('SELECT store_id FROM kyc_docs WHERE id=?',(doc,)).fetchone()
        if not row:raise HTTPException(404)
        auth(request,c,row['store_id']);expires=int(time.time())+600
        return {'url':f'/api/kyc/{doc}/content?expires={expires}&signature={signature(doc,expires)}','expires_in':600}

@router.get('/api/kyc/{doc}/content')
def content(doc:int,expires:int,signature:str):
    if expires<int(time.time()) or expires>int(time.time())+600 or not hmac.compare_digest(signature,globals()['signature'](doc,expires)):raise HTTPException(403,'Link inválido ou expirado')
    from nowup_backup import unprotect_private
    with connection() as c:row=c.execute('SELECT file_path_encrypted FROM kyc_docs WHERE id=?',(doc,)).fetchone()
    if not row:raise HTTPException(404)
    filename=unprotect_private(row[0].encode()).decode()
    if Path(filename).name!=filename:raise HTTPException(404)
    raw=unprotect_private((directory()/filename).read_bytes())
    mime='application/pdf' if raw.startswith(b'%PDF-') else 'image/png' if raw.startswith(b'\x89PNG') else 'image/jpeg'
    return Response(raw,media_type=mime,headers={'Cache-Control':'private, no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff','Content-Disposition':f'attachment; filename="document-{doc}"'})

@router.post('/admin/super/api/stores/{store}/kyc/review')
@router.post('/api/stores/{store}/kyc/review')
async def review(request:Request,store:int):
    G['admin'].csrf(request)
    try:body=await request.json()
    except ValueError:raise HTTPException(422,'Conteúdo inválido')
    if not isinstance(body,dict) or not isinstance(body.get('reason'),str):raise HTTPException(422,'Justificativa inválida')
    if body.get('status') not in ('approved','rejected') or not 8<=len(body.get('reason','').strip())<=500:raise HTTPException(422,'Informe situação e justificativa')
    with connection() as c:
        actor=auth(request,c,store,True);c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT document FROM professionals WHERE id=?',(store,)).fetchone()
        if not row or not billing.valid_document(row['document']):raise HTTPException(422,'CPF/CNPJ inválido')
        latest=c.execute('SELECT MAX(id) id,doc_type FROM kyc_docs WHERE store_id=? GROUP BY doc_type',(store,)).fetchall()
        if body['status']=='approved' and not {'identity','business'}.issubset({r['doc_type'] for r in latest}):raise HTTPException(422,'Envie documento pessoal e documento do negócio antes de aprovar')
        ids=[r['id'] for r in latest]
        for doc in ids:c.execute('UPDATE kyc_docs SET status=?,reviewed_by=?,reviewed_at=? WHERE id=?',(body['status'],actor['actor_id'],billing.stamp(),doc))
        c.execute('UPDATE professionals SET kyc_status=? WHERE id=?',(body['status'],store));billing.audit(c,store,actor['actor_id'],'KYC '+body['status']+': '+body['reason'][:500])
    G.get('invalidate',lambda:None)();return {'ok':True,'status':body['status']}

from contextlib import contextmanager
@contextmanager
def connection():
    c=G['db']()
    try:
        yield c;c.commit()
    except Exception:c.rollback();raise
    finally:c.close()
