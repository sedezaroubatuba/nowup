"""Administrative profile and manual billing presentation."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def today_local():
    return datetime.now(ZoneInfo('America/Sao_Paulo')).date()


def parse_date(value):
    if not value:
        return None
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('Use YYYY-MM-DD')
    return parsed


def valid_billing_dates(due, paid, today=None):
    due, paid = due.strip(), paid.strip()
    due_date, paid_date = parse_date(due), parse_date(paid)
    today = today or today_local()
    if paid_date and paid_date > today:
        raise ValueError('Future payment')
    if due_date and paid_date and due_date <= paid_date:
        raise ValueError('Due date must follow payment')
    return due, paid


def date_label(value):
    try:
        return parse_date(value[:10]).strftime('%d/%m/%Y') if value else 'Não informado'
    except (ValueError, TypeError):
        return 'Não informado'


def enrich_profiles(rows, today=None):
    today = today or today_local()
    result = []
    labels = {'demo':'Sem cobrança — fictício', 'free':'Sem cobrança — gratuito',
              'unconfigured':'Sem vencimento definido', 'overdue':'Inadimplente',
              'soon':'A vencer', 'current':'Em dia'}
    for row in rows:
        p = dict(row)
        p['profile_status'] = ('pending' if p['admission_status']=='pending' else
                               'rejected' if p['admission_status']=='rejected' else
                               'paused' if p['blocked'] else 'active')
        try: due = parse_date(p.get('billing_due_date', ''))
        except ValueError: due = None
        if p['is_demo']: status = 'demo'
        elif not p['is_premium']: status = 'free'
        elif due is None: status = 'unconfigured'
        elif due < today: status = 'overdue'
        elif due <= today + timedelta(days=7): status = 'soon'
        else: status = 'current'
        p.update(billing_status=status, billing_label=labels[status],
                 joined_label=date_label(p.get('created_at','')),
                 paid_label=date_label(p.get('billing_last_paid','')),
                 due_label=date_label(p.get('billing_due_date','')))
        result.append(p)
    return result
