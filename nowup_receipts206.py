"""Comprovantes privados no chat do pedido. Nunca confirmam pagamento."""
import io
import secrets
import sqlite3
import warnings
from datetime import datetime,timezone
from PIL import Image,ImageOps,UnidentifiedImageError
from fastapi import APIRouter,Request,UploadFile,File,Form,HTTPException
from fastapi.responses import JSONResponse,Response
router=APIRouter();G={}
LIMIT=5*1024*1024
PIXELS=12_000_000
CLOSED={'completed','cancelled','rejected'}

def configure(globals_):G.update(globals_)
def initialize():
    c=G['db']()
    try:
        c.executescript('''CREATE TABLE IF NOT EXISTS order_receipts206(
        id INTEGER PRIMARY KEY,message_id INTEGER NOT NULL UNIQUE REFERENCES order_messages(id),
        order_id INTEGER NOT NULL REFERENCES orders(id),sender_id INTEGER NOT NULL REFERENCES users(id),
        request_id TEXT NOT NULL UNIQUE,filename TEXT NOT NULL,content_type TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,content BLOB NOT NULL,created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS order_receipts206_order ON order_receipts206(order_id,id);''');c.commit()
    finally:c.close()

def clean_content(raw):
    if not raw:raise HTTPException(400,'Selecione um comprovante')
    if len(raw)>LIMIT:raise HTTPException(413,'O comprovante deve ter até 5 MB')
    if raw.startswith(b'%PDF-'):
        if b'%%EOF' not in raw[-4096:]:raise HTTPException(400,'O PDF está incompleto. Envie o arquivo original ou uma imagem.')
        # PDFs são entregues como download, sem execução ou visualização incorporada.
        return raw,'application/pdf','pdf'
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as im:
                if im.format not in ('JPEG','PNG','WEBP') or im.width*im.height>PIXELS:
                    raise HTTPException(400,'Envie uma imagem JPG, PNG ou WebP com até 12 milhões de pixels')
                im.load();im=ImageOps.exif_transpose(im).convert('RGB');out=io.BytesIO();im.save(out,'JPEG',quality=90,optimize=True);data=out.getvalue()
        if len(data)>LIMIT:raise HTTPException(413,'A imagem é muito grande. Envie uma versão menor.')
        return data,'image/jpeg','jpg'
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise HTTPException(400,'Arquivo inválido. Envie uma imagem JPG, PNG, WebP ou um PDF.')

@router.post('/pedidos/{order_id}/comprovante206')
async def upload(request:Request,order_id:int,file:UploadFile=File(...),request_id:str=Form('')):
    c,u,order=G['authorized_order_chat'](request,order_id)
    try:
        if u['role']!='customer':raise HTTPException(403,'Somente o cliente pode enviar comprovante')
        if order['status'] in CLOSED:raise HTTPException(409,'O pedido foi encerrado')
    finally:c.close()
    raw=await file.read(LIMIT+1)
    await file.close()
    content,mime,ext=clean_content(raw)
    request_id=request_id.strip()
    if not request_id or len(request_id)>100 or any(x not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for x in request_id):
        raise HTTPException(400,'Identificador de envio inválido. Tente novamente.')
    request_id=str(u['id'])+':'+request_id
    # Revalida autorização e situação após ler o arquivo e sob a mesma transação da gravação.
    c,u,order=G['authorized_order_chat'](request,order_id)
    try:
        c.execute('BEGIN IMMEDIATE')
        live=c.execute('SELECT status FROM orders WHERE id=?',(order_id,)).fetchone()
        if not live or live['status'] in CLOSED:raise HTTPException(409,'O pedido foi encerrado')
        old=c.execute('SELECT id,order_id FROM order_receipts206 WHERE request_id=?',(request_id,)).fetchone()
        if old:
            if old['order_id']!=order_id:raise HTTPException(409,'Este envio já foi utilizado em outro pedido')
            return JSONResponse({'ok':True,'receipt_id':old['id'],'duplicate':True},headers={'Cache-Control':'no-store'})
        stamp=datetime.now(timezone.utc).isoformat()
        message=c.execute('INSERT INTO order_messages(order_id,sender_role,body,created_at) VALUES(?,?,?,?)',(order_id,'customer','Comprovante enviado pelo cliente. Pagamento aguardando conferência da loja.',stamp))
        cur=c.execute('INSERT INTO order_receipts206(message_id,order_id,sender_id,request_id,filename,content_type,size_bytes,content,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(message.lastrowid,order_id,u['id'],request_id,'comprovante-pedido-'+str(order_id)+'.'+ext,mime,len(content),sqlite3.Binary(content),stamp))
        receipt_id=cur.lastrowid
        note='Comprovante recebido. Confira no banco se o Pix entrou antes de liberar o pedido.'
        notification=c.execute('INSERT INTO notifications(user_id,title,message,link,created_at) VALUES(?,?,?,?,?)',(order['owner_id'],'Nova mensagem no pedido',note,'/painel#pedido-'+str(order_id),stamp))
        if G.get('nowup_alerts112'):
            G['nowup_alerts112'].enqueue(c,order['owner_id'],notification.lastrowid,{'title':'Comprovante recebido','body':note,'url':'/painel#pedido-'+str(order_id),'tag':'nowup-recibo-'+str(receipt_id)})
        c.commit()
    finally:c.close()
    return JSONResponse({'ok':True,'receipt_id':receipt_id},headers={'Cache-Control':'no-store'})

@router.get('/pedidos/{order_id}/comprovantes206/{receipt_id}')
def download(request:Request,order_id:int,receipt_id:int):
    c,u,order=G['authorized_order_chat'](request,order_id)
    try:
        row=c.execute('SELECT filename,content_type,content FROM order_receipts206 WHERE id=? AND order_id=?',(receipt_id,order_id)).fetchone()
        if not row:raise HTTPException(404,'Comprovante não encontrado')
        data=bytes(row['content']);mime=row['content_type'];filename=row['filename']
    finally:c.close()
    # File bytes never enter /static or /uploads; authentication is checked on every access.
    return Response(data,media_type=mime if mime=='image/jpeg' else 'application/octet-stream',headers={
        'Content-Disposition':('inline' if mime=='image/jpeg' else 'attachment')+'; filename="'+filename+'"',
        'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"sandbox; default-src 'none'",'Cross-Origin-Resource-Policy':'same-origin'})
