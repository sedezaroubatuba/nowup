"""Manual backup import restricted to the isolated NowUp TEST service.

Never changes NOWUP_DB_ENGINE, production data, or an existing PostgreSQL target.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import urlparse, unquote
import zipfile
from fastapi import File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

TEST_HOST='nowup-teste-adm-v227.onrender.com'
MAX_BYTES=64*1024*1024
MAX_EXPANDED=256*1024*1024


def validate_target(url):
    parsed=urlparse(url)
    if parsed.scheme not in ('postgres','postgresql') or unquote(parsed.path).strip('/')!='nowup_teste':
        raise HTTPException(409,'Esta ferramenta aceita somente o banco nowup_teste. Nenhuma alteração realizada.')
    if os.getenv('NOWUP_DB_ENGINE','sqlite')!='sqlite':
        raise HTTPException(409,'Mantenha NOWUP_DB_ENGINE=sqlite durante a importação de teste.')


def validate_archive(path):
    try:
        with zipfile.ZipFile(path) as archive:
            entries=archive.infolist()
            if len(entries)>5000 or sum(e.file_size for e in entries)>MAX_EXPANDED:
                raise ValueError('Arquivo excede o limite de extração.')
            manifest=json.loads(archive.read('manifest.json'))
            if manifest.get('format')!='nowup-backup-v1' or manifest.get('database')!='database/nowup.db':
                raise ValueError('Selecione o backup SQLite completo baixado no painel NowUp.')
            # stage_backup subsequently checks every path, hash and SQLite integrity.
    except (ValueError,KeyError,zipfile.BadZipFile) as error:
        raise HTTPException(400,'Backup inválido ou formato não aceito.') from None



# V243: diagnostic queries run in a separate, read-only PostgreSQL connection.
# Only allowlisted categories leave this process; raw exceptions may contain secrets.
def failure_category(output):
    text = output.decode('utf-8', 'replace') if isinstance(output, bytes) else str(output or '')
    lowered = text.lower()
    rules = [
        ('destino não está vazio', 'destino_ocupado', 'O banco de teste já contém tabelas. Não reimporte nem apague dados.'),
        ('password authentication failed', 'autenticacao_banco', 'A autenticação do PostgreSQL falhou. Confira a URL interna no Render.'),
        ('could not translate host name', 'host_banco', 'O endereço do PostgreSQL não foi resolvido.'),
        ('name or service not known', 'host_banco', 'O endereço do PostgreSQL não foi resolvido.'),
        ('connection refused', 'conexao_recusada', 'O PostgreSQL recusou a conexão.'),
        ('timeout', 'tempo_conexao', 'A conexão ou operação excedeu o tempo disponível.'),
        ('timed out', 'tempo_conexao', 'A conexão ou operação excedeu o tempo disponível.'),
        ('modulenotfounderror', 'dependencia_ausente', 'Falta uma dependência no deploy de teste.'),
        ('checksum divergente', 'conferencia_dados', 'A comparação dos dados falhou. Não ative PostgreSQL.'),
        ('referências inválidas', 'referencias_origem', 'O backup contém referências inválidas.'),
        ('permission denied', 'permissao', 'Uma operação foi recusada por falta de permissão.'),
        ('undefinedcolumn', 'estrutura_sql', 'Uma coluna não foi reconhecida durante a migração.'),
        ('syntaxerror', 'estrutura_sql', 'O processo encontrou um erro de sintaxe.'),
        ('integrityerror', 'integridade_destino', 'O processo encontrou uma restrição de integridade.'),
    ]
    for marker, code, message in rules:
        if marker in lowered:
            return {'code': code, 'message': message}
    return {'code': 'falha_nao_classificada', 'message': 'O processo falhou por uma causa ainda não identificada. Não reimporte.'}


DIAGNOSTIC_SCRIPT = r"""
import json, os
try:
    import psycopg
    with psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=10,
                         options='-c default_transaction_read_only=on') as connection:
        with connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION READ ONLY')
            cursor.execute("SELECT current_database(), current_setting('transaction_read_only')")
            database, read_only = cursor.fetchone()
            if database != 'nowup_teste' or read_only != 'on':
                print(json.dumps({'code': 'destino_nao_confirmado'}))
            else:
                cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
                tables = cursor.fetchone()[0]
                print(json.dumps({'code': 'conexao_ok', 'database': database,
                                  'tables': tables, 'read_only': True}))
except Exception as error:
    # The parent classifies this output and never sends the raw text to the page/logs.
    import sys
    print(type(error).__name__ + ': ' + str(error), file=sys.stderr)
    sys.exit(1)
"""


def diagnose_target():
    try:
        result = subprocess.run([sys.executable, '-c', DIAGNOSTIC_SCRIPT],
                                env=os.environ.copy(), capture_output=True, timeout=20)
    except subprocess.TimeoutExpired:
        return {'code': 'tempo_conexao', 'message': 'A conexão excedeu 20 segundos. Nenhum dado foi alterado.'}
    if result.returncode:
        return failure_category(result.stderr)
    try:
        data = json.loads(result.stdout)
        if data.get('code') == 'conexao_ok' and type(data.get('tables')) is int and data['tables'] >= 0 and data.get('read_only') is True and data.get('database') == 'nowup_teste':
            return {key: data[key] for key in ('code', 'database', 'tables', 'read_only')}
    except (ValueError, TypeError):
        pass
    return {'code': 'diagnostico_inconclusivo', 'message': 'Não foi possível confirmar o destino. Nenhum dado foi alterado.'}


def install(app, authorize, upload_dir):
    def guard(request):
        if os.getenv('NOWUP_MIGRATION_TEST','0')!='1' or request.url.hostname!=TEST_HOST:
            raise HTTPException(404)
        authorize(request,'admin')
        validate_target(os.getenv('DATABASE_URL',''))

    @app.get('/admin/migracao-teste/diagnostico')
    def diagnostic(request: Request):
        guard(request)
        data = diagnose_target()
        data['migration_verified'] = False
        data['notice'] = 'Diagnóstico somente de leitura; não confirma migração. Mantenha NOWUP_DB_ENGINE=sqlite.'
        return JSONResponse(data, headers={'Cache-Control': 'no-store'})

    @app.get('/admin/migracao-teste', response_class=HTMLResponse)
    def page(request: Request):
        guard(request)
        return HTMLResponse('''<!doctype html><html lang="pt-BR"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Migração de teste NowUp</title><body style="font:18px system-ui;max-width:600px;margin:32px auto;padding:20px"><h1>Migração de teste</h1><p><a href="/admin/migracao-teste/diagnostico">Conferir conexão e destino (sem importar)</a></p><p>Enviar uma cópia do backup para o banco <b>nowup_teste</b>. O banco de destino deve estar vazio. O site principal e o arquivo original serão preservados.</p><form method="post" enctype="multipart/form-data"><label>Backup completo (.zip)<br><input name="backup" type="file" accept=".zip" required></label><p><button style="padding:16px;background:#7026bd;color:white;border:0;border-radius:8px">Importar e conferir no banco de teste</button></p></form><p>Aguarde o resultado sem reenviar. Não publique o backup no GitHub. Esta ação não ativa PostgreSQL no aplicativo.</p></body></html>''',headers={'Cache-Control':'no-store'})

    @app.post('/admin/migracao-teste')
    def upload(request: Request, backup: UploadFile=File(...)):
        guard(request)
        # Same-origin POST, additionally protected by the existing V238 middleware.
        if request.headers.get('origin')!='https://'+TEST_HOST:
            raise HTTPException(403,'Abra a ferramenta pelo endereço do serviço de teste.')
        with tempfile.TemporaryDirectory(prefix='nowup-mobile241-') as folder:
            folder=Path(folder);archive=folder/'backup.zip';size=0
            with archive.open('wb') as output:
                while True:
                    part=backup.file.read(1024*1024)
                    if not part:break
                    size+=len(part)
                    if size>MAX_BYTES:raise HTTPException(413,'Backup maior que 64 MB.')
                    output.write(part)
            validate_archive(archive)
            from restore_backup import stage_backup
            staged=folder/'staged'
            try:stage_backup(archive,staged)
            except Exception:raise HTTPException(400,'O backup não passou na conferência de arquivos e banco.') from None
            # Only identical existing images may be reused; never overwrite a different image.
            uploads=Path(upload_dir);sources=[]
            import hashlib
            for source in (staged/'uploads').rglob('*'):
                if not source.is_file():continue
                dest=uploads/source.relative_to(staged/'uploads')
                if dest.exists() and (dest.is_symlink() or not dest.is_file() or hashlib.sha256(dest.read_bytes()).digest()!=hashlib.sha256(source.read_bytes()).digest()):
                    raise HTTPException(409,'Há fotos diferentes na pasta de teste. Nenhum banco foi importado.')
                if any(parent.is_symlink() for parent in dest.parents):
                    raise HTTPException(409,'Pasta de fotos inválida.')
                sources.append((source,dest))
            report=folder/'report.json'
            environment=os.environ.copy();environment['NOWUP_DB_ENGINE']='postgres'
            script=Path(__file__).with_name('migrate_postgres239.py')
            # Migration itself refuses any nonempty database and rolls back on mismatch.
            try:
                result=subprocess.run([sys.executable,str(script),'--source',str(staged/'database/nowup.db'),'--report',str(report)],env=environment,capture_output=True,timeout=180)
            except subprocess.TimeoutExpired:
                raise HTTPException(503,'Tempo excedido. Não reenvie sem conferir o destino.') from None
            if result.returncode or not report.is_file():
                problem = failure_category(result.stderr)
                # Codes contain no credentials, SQL statements or personal data.
                import logging
                logging.getLogger(__name__).warning('NOWUP_MIGRATION_TEST failure_code=%s returncode=%s', problem['code'], result.returncode)
                raise HTTPException(409, {**problem, 'migration_verified': False, 'next': 'Não reenvie. Abra /admin/migracao-teste/diagnostico. Mantenha NOWUP_DB_ENGINE=sqlite.'})
            details=json.loads(report.read_text())
            if details.get('verified') is not True:
                raise HTTPException(503,'Conferência não confirmada. Mantenha SQLite.')
            import shutil
            try:
                for source,dest in sources:
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    if not dest.exists():shutil.copyfile(source,dest)
            except OSError:
                raise HTTPException(503,'Banco de teste importado, mas cópia de fotos incompleta. Não reenvie o backup; confira o armazenamento.') from None
            counts={name:item['rows'] for name,item in details['tables'].items()}
            return JSONResponse({'verified':True,'tables':len(counts),'counts':counts,'photos':len(sources),'message':'Banco de TESTE conferido. O aplicativo continua em SQLite. Guarde uma foto deste resultado.'},headers={'Cache-Control':'no-store'})
