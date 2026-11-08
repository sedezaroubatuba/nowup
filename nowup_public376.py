"""Bound public CMS writes and export untrusted values as XLSX text cells."""
import hashlib
import io
import time
import zipfile
from xml.etree.ElementTree import Element, SubElement, tostring
from fastapi import HTTPException


def initialize(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS public_limits376(bucket TEXT NOT NULL,window_start INTEGER NOT NULL,attempts INTEGER NOT NULL,PRIMARY KEY(bucket,window_start))')
    conn.execute('CREATE INDEX IF NOT EXISTS public_limits376_window ON public_limits376(window_start)')


def check_public(database,request,now=None):
    """Use the ASGI client address, never a user-supplied forwarded header."""
    now=int(time.time() if now is None else now)
    host=request.client.host if request.client else 'unknown'
    buckets=[('ip:'+host,5),('global',300)]
    conn=database()
    try:
        # Atomic upserts acquire only the rows involved, not a global advisory lock.
        conn.execute('BEGIN')
        blocked=False
        for value,limit in buckets:
            bucket=hashlib.sha256(('public-cms376:'+value).encode()).hexdigest()
            window=now//60*60
            conn.execute('INSERT INTO public_limits376 VALUES(?,?,1) ON CONFLICT(bucket,window_start) DO UPDATE SET attempts=public_limits376.attempts+1',(bucket,window))
            count=conn.execute('SELECT attempts FROM public_limits376 WHERE bucket=? AND window_start=?',(bucket,window)).fetchone()[0]
            blocked=blocked or count>limit
        conn.execute('DELETE FROM public_limits376 WHERE window_start<?',(now-3600,))
        conn.commit()
    except Exception:
        conn.rollback();raise
    finally:
        conn.close()
    if blocked:
        raise HTTPException(429,'Você enviou várias mensagens. Aguarde um minuto antes de tentar novamente.',headers={'Retry-After':str(60-now%60),'Cache-Control':'no-store'})


XMLNS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'

def _text(value):
    # XML 1.0 forbids most control characters; spreadsheet cell limit is 32767.
    value='' if value is None else str(value)
    return ''.join(c for c in value if c in '\t\n\r' or 0x20<=ord(c)<=0xD7FF or 0xE000<=ord(c)<=0xFFFD or 0x10000<=ord(c)<=0x10FFFF)[:32767]


def contact_workbook(rows):
    """No formula, URL relationship, macro or inferred cell type is emitted."""
    sheet=Element('worksheet',xmlns=XMLNS);data=SubElement(sheet,'sheetData')
    headers=('Nome','E-mail','Telefone','Assunto','Mensagem','Status','Data')
    for number,values in enumerate([headers]+list(rows),1):
        row=SubElement(data,'row',r=str(number))
        for col,value in enumerate(values):
            cell=SubElement(row,'c',r=chr(65+col)+str(number),t='inlineStr')
            text=SubElement(SubElement(cell,'is'),'t',{'{http://www.w3.org/XML/1998/namespace}space':'preserve'})
            text.text=_text(value)
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml','<?xml version="1.0"?><workbook xmlns="'+XMLNS+'" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Contatos" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml',tostring(sheet,encoding='utf-8',xml_declaration=True))
    return out.getvalue()
