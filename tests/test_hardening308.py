import hashlib,io,json,sqlite3,zipfile
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from fastapi import FastAPI,Request,HTTPException
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile,Headers
from PIL import Image
from nowup_hardening308 import PublicFiles,RequestLimit308,save_photo,retire_photos,image_references
from nowup_security import session_user
from test_checkout247 import checkout

@pytest.mark.parametrize('path',['app.py','app.cpython-312.pyc','settings.env','notes.txt','.env','__pycache__/app.pyc'])
def test_private_files_never_served(tmp_path,path):
 p=tmp_path/path;p.parent.mkdir(exist_ok=True);p.write_text('private')
 app=FastAPI();app.mount('/static',PublicFiles(directory=tmp_path))
 assert TestClient(app).get('/static/'+path).status_code==404

def test_public_assets_and_images_scope(tmp_path):
 (tmp_path/'photo.jpg').write_bytes(b'image');(tmp_path/'app.js').write_text('let x=1')
 app=FastAPI();app.mount('/uploads',PublicFiles(directory=tmp_path,images_only=True));app.mount('/static',PublicFiles(directory=tmp_path))
 c=TestClient(app);assert c.get('/uploads/photo.jpg').status_code==200
 assert c.get('/uploads/app.js').status_code==404 and c.get('/static/app.js').status_code==200

def test_request_cap_including_streams():
 app=FastAPI();app.add_middleware(RequestLimit308,limit=10)
 @app.post('/')
 async def route(request:Request):return {'size':len(await request.body())}
 c=TestClient(app);assert c.post('/',content=b'123').json()['size']==3
 assert c.post('/',content=b'x'*11).status_code==413
 assert c.post('/',content=iter([b'123456',b'123456'])).status_code==413

def upload():
 buffer=io.BytesIO();im=Image.new('RGB',(400,300),'purple');exif=Image.Exif();exif[270]='Private metadata';im.save(buffer,'JPEG',exif=exif);buffer.seek(0)
 return UploadFile(buffer,filename='photo.jpg',headers=Headers({'content-type':'image/jpeg'}))

def test_photo_saved_atomically_without_metadata(tmp_path):
 name=save_photo(upload(),tmp_path);im=Image.open(tmp_path/name)
 assert im.size==(400,300) and len(im.getexif())==0
 assert not list(tmp_path.glob('.*.tmp'))

def test_failed_photo_write_preserves_old_and_cleans_temp(tmp_path,monkeypatch):
 (tmp_path/'old.jpg').write_bytes(b'old')
 import nowup_hardening308 as h
 def fail(*args):raise OSError('disk failure')
 monkeypatch.setattr(h.os,'replace',fail)
 with pytest.raises(HTTPException) as exc:save_photo(upload(),tmp_path)
 assert exc.value.status_code==503 and (tmp_path/'old.jpg').read_bytes()==b'old'
 assert sorted(p.name for p in tmp_path.iterdir())==['old.jpg']

def test_shared_photo_is_not_deleted_and_receipts_stay_private(tmp_path):
 database=tmp_path/'db'
 def db():return sqlite3.connect(database)
 with db() as c:
  c.executescript('CREATE TABLE professionals(avatar_filename,cover_filename);CREATE TABLE order_receipts206(filename);CREATE TABLE site_settings(key,value);')
  c.execute("INSERT INTO professionals VALUES('shared.jpg','shared.jpg')");c.execute("INSERT INTO order_receipts206 VALUES('private-receipt.jpg')")
  assert image_references(c)=={'shared.jpg'}
 (tmp_path/'shared.jpg').write_bytes(b'image');retire_photos(db,tmp_path,['shared.jpg']);assert (tmp_path/'shared.jpg').exists()
 with db() as c:c.execute("UPDATE professionals SET avatar_filename='',cover_filename=''")
 retire_photos(db,tmp_path,['shared.jpg']);assert not (tmp_path/'shared.jpg').exists()

def test_backup_includes_database_receipt_without_requiring_public_copy(tmp_path,monkeypatch):
 import nowup_backup as backup
 database=tmp_path/'db';photos=tmp_path/'photos';photos.mkdir();directory=tmp_path/'copy';directory.mkdir()
 with sqlite3.connect(database) as c:c.executescript("CREATE TABLE order_receipts206(filename,content);INSERT INTO order_receipts206 VALUES('private.jpg',X'1234');")
 monkeypatch.setattr(backup,'_db',database);monkeypatch.setattr(backup,'_uploads',photos)
 archive=backup.create_archive(directory)
 with zipfile.ZipFile(archive) as z:
  assert 'database/nowup.db' in z.namelist() and 'uploads/private.jpg' not in z.namelist()

def test_cms_editor_cannot_inherit_super_admin(checkout):
 m,client,*_=checkout
 stamp=datetime.now(timezone.utc);token='editor-token'
 with m.db() as c:
  c.execute('CREATE TABLE IF NOT EXISTS cms_permissions(user_id PRIMARY KEY,cms_role)')
  uid=c.execute("INSERT INTO users(role,name,email,password_hash,created_at) VALUES('admin','Editor','editor308@example.invalid','unused',?)",(stamp.isoformat(),)).lastrowid
  c.execute("INSERT INTO cms_permissions VALUES(?,'editor')",(uid,));c.execute('INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',(token,uid,(stamp+timedelta(minutes=10)).isoformat()))
  assert session_user(c,token)['role']=='cms'
 client.cookies.set('nowup_session',token)
 assert client.get('/admin/super/api/state').status_code in (401,403)

def test_admin_code_is_one_use_and_failed_attempts_are_bounded(checkout,monkeypatch):
 import admin_customization as auth
 m,client,*_=checkout;monkeypatch.setattr(auth,'db',m.db)
 with m.db() as c:
  c.execute('CREATE TABLE IF NOT EXISTS cms_permissions(user_id PRIMARY KEY,cms_role)')
  uid=c.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0]
  c.execute('INSERT INTO admin_login_codes(challenge,user_id,code_hash,expires_at,attempts) VALUES(?,?,?,?,0)',('challenge',uid,hashlib.sha256(b'123456').hexdigest(),(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()))
 client.cookies.set('nowup_admin_challenge','challenge')
 def submit():return client.post('/admin/codigo',data={'code':'123456'},follow_redirects=False)
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:submit(),range(2)))
 assert sum(r.headers.get('location') in ('/admin','/admin/super') for r in results)==1, [(r.status_code,dict(r.headers)) for r in results]
 with m.db() as c:assert c.execute('SELECT COUNT(*) FROM sessions WHERE user_id=?',(uid,)).fetchone()[0]==1

def test_reset_token_can_only_change_password_once(checkout):
 m,client,*_=checkout
 with m.db() as c:
  uid=c.execute("SELECT id FROM users WHERE role='customer'").fetchone()[0]
  c.execute('INSERT INTO password_reset_tokens(token_hash,user_id,expires_at) VALUES(?,?,?)',(hashlib.sha256(b'reset').hexdigest(),uid,(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()))
 def reset(password):return client.post('/redefinir-senha',data={'token':'reset','password':password,'password_confirm':password},follow_redirects=False)
 with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(reset,['new-password-one','new-password-two']))
 assert sum('senha_redefinida=1' in r.headers.get('location','') for r in responses)==1

def test_auth_recovery_is_limited(checkout):
 m,client,*_=checkout
 # An invalid email does not send mail and still consumes the abuse budget.
 for _ in range(3):assert client.post('/recuperar-senha',data={'email':'invalid'},follow_redirects=False).status_code==303
 assert client.post('/recuperar-senha',data={'email':'invalid'},follow_redirects=False).status_code==429

def test_wrong_admin_codes_cannot_bypass_attempt_limit(checkout,monkeypatch):
 import admin_customization as auth
 m,client,*_=checkout;monkeypatch.setattr(auth,'db',m.db)
 with m.db() as c:
  uid=c.execute("SELECT id FROM users WHERE role='admin'").fetchone()[0]
  c.execute('INSERT INTO admin_login_codes(challenge,user_id,code_hash,expires_at) VALUES(?,?,?,?)',('limited',uid,hashlib.sha256(b'123456').hexdigest(),(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()))
 for _ in range(5):
  r=client.post('/admin/codigo',data={'code':'000000'},headers={'Cookie':'nowup_admin_challenge=limited'},follow_redirects=False)
  assert r.headers.get('location')=='/admin/codigo?erro=1'
 r=client.post('/admin/codigo',data={'code':'123456'},headers={'Cookie':'nowup_admin_challenge=limited'},follow_redirects=False)
 assert '2fa_expirado' in r.headers.get('location','')
 with m.db() as c:assert c.execute('SELECT COUNT(*) FROM sessions WHERE user_id=?',(uid,)).fetchone()[0]==0

def test_avatar_replacement_preserves_shared_cover(checkout,monkeypatch):
 m,client,_,_,product,_=checkout
 with m.db() as c:
  p=c.execute('SELECT p.* FROM professionals p JOIN products pr ON pr.professional_id=p.id WHERE pr.id=?',(product,)).fetchone()
  c.execute("UPDATE professionals SET avatar_filename='shared.jpg',cover_filename='shared.jpg' WHERE id=?",(p['id'],))
 (m.UPLOAD_DIR/'shared.jpg').write_bytes(b'old image')
 monkeypatch.setattr(m,'current_user',lambda request:{'id':p['user_id'],'role':'professional'})
 r=client.post('/painel/identidade',files={'avatar':('new.jpg',upload().file.getvalue(),'image/jpeg')},follow_redirects=False)
 assert r.status_code==303
 with m.db() as c:
  saved=c.execute('SELECT avatar_filename,cover_filename FROM professionals WHERE id=?',(p['id'],)).fetchone()
  assert saved['avatar_filename']!='shared.jpg' and saved['cover_filename']=='shared.jpg'
  assert (m.UPLOAD_DIR/saved['avatar_filename']).is_file() and (m.UPLOAD_DIR/'shared.jpg').is_file()

def test_security_headers_and_api_docs(checkout):
 m,client,*_=checkout
 r=client.get('/health');assert r.status_code==200
 assert r.headers['x-content-type-options']=='nosniff' and "object-src 'none'" in r.headers['content-security-policy']
 for path in ['/docs','/redoc','/openapi.json']:assert client.get(path).status_code==404
