"""Run server suites in separate processes to isolate legacy module globals."""
import os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.chdir(root)
env={**os.environ,'PYTHONPATH':str(root)+os.pathsep+str(root/'tests'),'NOWUP_DB_ENGINE':'sqlite','NOWUP_ADMIN_EMAIL':'audit348@example.invalid','NOWUP_ADMIN_PASSWORD':'isolated-audit348-password'}
failed=[]
for suite in [*sorted((root/'tests').glob('test_*.py')),root/'test_admin205.py']:
    result=subprocess.run([sys.executable,'-m','pytest',str(suite),'-q','--disable-warnings'],env=env,capture_output=True,text=True,timeout=180)
    print(suite.name, result.stdout.strip().splitlines()[-1:], flush=True)
    if result.returncode:
        failed.append(suite.name)
        print(result.stdout+result.stderr,flush=True)
if failed:print('FAILED:',', '.join(failed))
raise SystemExit(bool(failed))
