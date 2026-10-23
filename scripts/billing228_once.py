"""One billing scheduler pass against an already migrated persistent database."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
from nowup_security import require_secrets
if __name__=='__main__':
 require_secrets()
 app.nowup_runtime228.run_once()
