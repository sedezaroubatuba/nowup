"""Read-only merchant Kanban data; order mutations retain existing validation."""
from datetime import datetime

STAGES = (
    ('new', 'Novos', ('new', 'reviewing', 'awaiting_approval', 'revision_approved')),
    ('preparing', 'Em preparo', ('confirmed', 'preparing', 'ready')),
    ('delivery', 'Em entrega', ('out_for_delivery',)),
    ('closed', 'Encerrados', ('completed', 'cancelled', 'rejected')),
)


def board(conn, professional_id, lower, upper, tz):
    active = tuple(status for _, _, statuses in STAGES[:3] for status in statuses)
    placeholders = ','.join('?' for _ in active)
    rows = conn.execute(f"""SELECT o.*,
      COALESCE((SELECT SUM(quantity) FROM order_items WHERE order_id=o.id),0) item_count
      FROM orders o WHERE o.professional_id=? AND
      (o.status IN ({placeholders}) OR (o.created_at>=? AND o.created_at<?))
      ORDER BY o.id DESC""", (professional_id, *active, lower, upper)).fetchall()
    stages = [dict(key=key, title=title, orders=[]) for key, title, _ in STAGES]
    today = []
    for raw in rows:
        order = dict(raw)
        if lower <= order['created_at'] < upper:
            today.append(order)
        created = datetime.fromisoformat(order['created_at']).astimezone(tz)
        order['local_time'] = created.strftime('%d/%m • %H:%M')
        order['previous_day'] = not (lower <= order['created_at'] < upper)
        status = order['status']
        order['next_status'], order['next_label'] = {
            'new': ('confirmed', 'Aceitar pedido'),
            'revision_approved': ('confirmed', 'Aceitar pedido'),
            'confirmed': ('preparing', 'Iniciar preparo'),
            'preparing': ('ready', 'Marcar como pronto'),
            'ready': ('out_for_delivery', 'Saiu para entrega') if order['fulfillment_type'] == 'delivery' else ('completed', 'Concluir retirada'),
            'out_for_delivery': ('completed', 'Finalizar entrega'),
        }.get(status, ('', ''))
        for stage, (_, _, statuses) in zip(stages, STAGES):
            if status in statuses:
                stage['orders'].append(order)
                break
    valid = [order for order in today if order['status'] not in ('cancelled', 'rejected')]
    total = sum(order['total_cents'] for order in valid)
    return dict(stages=stages, count=len(today), active=sum(len(s['orders']) for s in stages[:3]),
                total=total, average=round(total / len(valid)) if valid else 0)
