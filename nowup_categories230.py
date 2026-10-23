"""Shared, local category artwork and automatic Portuguese name matching."""
import json
import re
import unicodedata
from pathlib import Path
from markupsafe import Markup

CATALOG = json.loads((Path(__file__).parent / 'static/category-icons230.json').read_text())
BY_KEY = {item['key']: item for item in CATALOG}


def normalize(value):
    value = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().lower()
    return ' '.join(re.findall(r'[a-z0-9]+', value))


def validate_key(value):
    """Only catalog IDs can be persisted. Old emojis gracefully become automatic."""
    return value if isinstance(value, str) and value in BY_KEY else 'auto'


def resolve(name, chosen='auto'):
    if chosen in BY_KEY:
        return chosen
    name = ' ' + normalize(name) + ' '
    for item in CATALOG:
        if any(' ' + normalize(alias) + ' ' in name for alias in item['aliases']):
            return item['key']
    return 'grid'


def icon(name, chosen='auto'):
    key = resolve(name, chosen)
    # Artwork and attributes are exclusively from our static allowlist, never user input.
    return Markup('<svg class="nu230-svg" viewBox="0 0 24 24" fill="none" '
                  'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
                  'stroke-linejoin="round" aria-hidden="true" focusable="false">' + BY_KEY[key]['svg'] + '</svg>')
