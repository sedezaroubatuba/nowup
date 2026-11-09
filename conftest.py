"""Never let the test suite use the repository database or a production DSN."""
import os,tempfile
from pathlib import Path

_KEYS=('NOWUP_DB_ENGINE','NOWUP_DB','NOWUP_UPLOAD_DIR','DATABASE_URL','NOWUP_ADMIN_EMAIL','NOWUP_ADMIN_PASSWORD')

def pytest_configure(config):
    config._nowup391_previous={key:os.environ.get(key) for key in _KEYS}
    config._nowup391_directory=tempfile.TemporaryDirectory(prefix='nowup-tests391-')
    base=Path(config._nowup391_directory.name)
    os.environ.update(NOWUP_DB_ENGINE='sqlite',NOWUP_DB=str(base/'suite.db'),NOWUP_UPLOAD_DIR=str(base/'uploads'),NOWUP_ADMIN_EMAIL='suite391@example.invalid',NOWUP_ADMIN_PASSWORD='isolated-suite391-password')
    os.environ.pop('DATABASE_URL',None)

def pytest_unconfigure(config):
    for key,value in getattr(config,'_nowup391_previous',{}).items():
        if value is None:os.environ.pop(key,None)
        else:os.environ[key]=value
    directory=getattr(config,'_nowup391_directory',None)
    if directory:directory.cleanup()
