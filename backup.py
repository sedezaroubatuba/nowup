"""Backup consistente do banco e dos uploads. Configure NOWUP_BACKUP_DIR em volume persistente."""
import os, sqlite3, tarfile, tempfile
from datetime import datetime, timezone
from pathlib import Path

BASE=Path(__file__).resolve().parent
DB=Path(os.getenv("NOWUP_DB",BASE/"data"/"nowup.db"))
UPLOADS=Path(os.getenv("NOWUP_UPLOAD_DIR",BASE/"uploads"))
DEST=Path(os.getenv("NOWUP_BACKUP_DIR",BASE/"backups"))

def backup():
    if not DB.is_file():
        raise RuntimeError("Banco de dados não encontrado")
    DEST.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    final=DEST/f"nowup-{stamp}.tar.gz"
    with tempfile.TemporaryDirectory() as tmp:
        snapshot=Path(tmp)/"nowup.db"
        source=sqlite3.connect(f"file:{DB}?mode=ro",uri=True)
        target=sqlite3.connect(snapshot)
        try:
            source.backup(target)
        finally:
            target.close(); source.close()
        with tarfile.open(final,"w:gz") as archive:
            archive.add(snapshot,arcname="nowup.db")
            if UPLOADS.is_dir():
                archive.add(UPLOADS,arcname="uploads")
    keep=int(os.getenv("NOWUP_BACKUP_KEEP","14"))
    for stale in sorted(DEST.glob("nowup-*.tar.gz"),reverse=True)[max(1,keep):]:
        stale.unlink()
    print(final)

if __name__=="__main__":
    backup()
