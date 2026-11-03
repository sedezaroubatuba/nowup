"""Display-only formatting for immutable order snapshots."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def note_lines(value):
    if not value:return []
    return [line.strip() for line in str(value).replace(' · ','\n').splitlines() if line.strip()]


def local_time(value):
    try:
        stamp=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y às %H:%M')
    except (ValueError,TypeError):return str(value or '')
