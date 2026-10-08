"""Restore only into a NEW folder, never directly over a running NowUp."""
import argparse,base64,getpass,hashlib,json,os,shutil,sqlite3,tempfile,zipfile
from pathlib import Path,PurePosixPath
from nowup_backup import decrypt_archive

def stage_backup(archive,output):
    output=Path(output)
    if output.exists():raise ValueError('A pasta de destino já existe. Escolha uma pasta nova.')
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise ValueError('Arquivo ZIP danificado.')
        manifest=json.loads(z.read('manifest.json'))
        if manifest.get('format')!='nowup-backup-v1':raise ValueError('Formato desconhecido.')
        expected=manifest['files']
        if len(z.namelist())!=len(set(z.namelist())) or set(z.namelist())!=set(expected)|{'manifest.json'}:raise ValueError('Lista de arquivos inconsistente.')
        for name in expected:
            path=PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or not (name=='database/nowup.db' or name.startswith('uploads/')):raise ValueError('Caminho não permitido.')
        output.mkdir(parents=True,mode=0o700)
        try:
            for name,digest in expected.items():
                target=output/name;target.parent.mkdir(parents=True,exist_ok=True)
                h=hashlib.sha256()
                with z.open(name) as src,target.open('xb') as dst:
                    for chunk in iter(lambda:src.read(1024*1024),b''):h.update(chunk);dst.write(chunk)
                os.chmod(target,0o600)
                if h.hexdigest()!=digest:raise ValueError('A verificação de integridade falhou.')
            conn=sqlite3.connect((output/'database/nowup.db').resolve().as_uri()+'?mode=ro',uri=True)
            try:
                if conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Banco inválido.')
            finally:conn.close()
            (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False))
        except Exception:shutil.rmtree(output);raise
    return len(expected)-1

def main():
    parser=argparse.ArgumentParser(description='Conferir e recuperar backup em uma pasta NOVA de teste.')
    parser.add_argument('backup',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nowup-restore-') as directory:
        archive=args.backup
        if archive.name.endswith('.enc'):
            secret=os.getenv('NOWUP_BACKUP_ENCRYPTION_KEY') or getpass.getpass('Chave de criptografia (entrada oculta): ')
            key=base64.b64decode(secret,validate=True)
            if len(key)!=32:raise ValueError('Chave inválida.')
            plaintext=Path(directory)/'backup.zip';decrypt_archive(archive,plaintext,key);archive=plaintext
        count=stage_backup(archive,args.output)
    print(f'Cópia verificada: banco e {count} arquivos de fotos, na pasta {args.output}. Nada foi alterado no site.')

if __name__=='__main__':main()
