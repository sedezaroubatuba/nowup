"""Read-only sales analytics for administrator, using finalized NowUp orders."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlencode
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

TZ = ZoneInfo('America/Sao_Paulo')
router = APIRouter()
_db = _auth = _templates = _context = None


def configure(db, auth, templates, context):
    global _db, _auth, _templates, _context
    _db, _auth, _templates, _context = db, auth, templates, context


def local_date(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(TZ)


def utc_bounds(start, end):
    return (datetime.combine(start,time.min,TZ).astimezone(timezone.utc).isoformat(),
            datetime.combine(end+timedelta(days=1),time.min,TZ).astimezone(timezone.utc).isoformat())


def report_period(inicio='', fim='', mes='', today=None):
    today = today or datetime.now(TZ).date()
    try:
        if mes:
            start = date.fromisoformat(mes+'-01')
            end = (start.replace(day=28)+timedelta(days=4)).replace(day=1)-timedelta(days=1)
        else:
            start = date.fromisoformat(inicio) if inicio else today.replace(day=1)
            end = date.fromisoformat(fim) if fim else today
        if start > today: raise ValueError('Período futuro')
        end = min(end,today)
        if start > end: raise ValueError('Datas invertidas')
        if (end-start).days >= 366: raise ValueError('Limite de 366 dias')
    except ValueError:
        raise HTTPException(400,'Informe um período válido de até 366 dias, sem datas futuras.')
    return start,end


def sales_report(conn, start, end, store_id=0):
    days=(end-start).days+1
    prev_start,prev_end=start-timedelta(days=days),start-timedelta(days=1)
    lower,upper=utc_bounds(prev_start,end)
    # Fictitious profiles are excluded from business analytics.
    profiles=[dict(r) for r in conn.execute("SELECT id,display_name,slug,city,created_at,blocked,admission_status FROM professionals WHERE is_demo=0 ORDER BY display_name")]
    if store_id and not any(p['id']==store_id for p in profiles):
        raise HTTPException(404,'Perfil não encontrado neste relatório')
    rows={p['id']:dict(p,amount=0,previous=0,orders=0,cancelled=0,pending=0,views=0) for p in profiles}
    daily={ (start+timedelta(days=i)).isoformat():0 for i in range(days)}
    monthly={}
    cursor=start.replace(day=1)
    while cursor<=end:
        monthly[cursor.strftime('%Y-%m')]=0
        cursor=(cursor.replace(day=28)+timedelta(days=4)).replace(day=1)
    weekdays=[dict(label=x,orders=0,amount=0) for x in ['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']]
    hours=[dict(label=f'{i:02d}h',orders=0,amount=0) for i in range(24)]
    query="""SELECT o.*,COALESCE(h.finished,o.updated_at,o.created_at) sold_at FROM orders o
      JOIN professionals p ON p.id=o.professional_id
      LEFT JOIN (SELECT order_id,MAX(created_at) finished FROM order_status_history WHERE status='completed' GROUP BY order_id) h ON h.order_id=o.id
      WHERE p.is_demo=0 AND (datetime(o.created_at)>=datetime(?) AND datetime(o.created_at)<datetime(?)
      OR o.status='completed' AND datetime(COALESCE(h.finished,o.updated_at,o.created_at))>=datetime(?) AND datetime(COALESCE(h.finished,o.updated_at,o.created_at))<datetime(?))"""
    for order in conn.execute(query,(lower,upper,lower,upper)):
        pid=order['professional_id']
        if store_id and pid!=store_id: continue
        item=rows[pid]; created=local_date(order['created_at'])
        if order['status']=='completed':
            sold=local_date(order['sold_at']); day=sold.date(); amount=order['total_cents']
            if prev_start<=day<=prev_end: item['previous']+=amount
            if start<=day<=end:
                item['amount']+=amount;item['orders']+=1
                daily[day.isoformat()]+=amount
                month=day.strftime('%Y-%m');monthly[month]=monthly.get(month,0)+amount
                # Demand peaks use time of order placement for sales finalized in period.
                weekdays[created.weekday()]['orders']+=1;weekdays[created.weekday()]['amount']+=amount
                hours[created.hour]['orders']+=1;hours[created.hour]['amount']+=amount
        elif start<=created.date()<=end:
            if order['status'] in ('cancelled','rejected'): item['cancelled']+=1
            else: item['pending']+=1
    view_lower,view_upper=utc_bounds(start,end)
    for r in conn.execute("SELECT professional_id,COUNT(*) views FROM analytics_events WHERE event_type='profile_view' AND datetime(created_at)>=datetime(?) AND datetime(created_at)<datetime(?) GROUP BY professional_id",(view_lower,view_upper)):
        if r['professional_id'] in rows: rows[r['professional_id']]['views']=r['views']
    selected=[r for r in rows.values() if not store_id or r['id']==store_id]
    for r in selected:
        age_start=max(start,local_date(r['created_at']).date())
        r['eligible_days']=max(0,(end-age_start).days+1)
        r['daily_average']=round(r['amount']/max(1,r['eligible_days']))
        months=max(1,(end.year-age_start.year)*12+end.month-age_start.month+1)
        r['monthly_average']=round(r['amount']/months)
        r['ticket']=round(r['amount']/r['orders']) if r['orders'] else 0
        r['change']=round((r['amount']-r['previous'])*100/r['previous'],1) if r['previous'] else None
        r['new_sales']=r['previous']==0 and r['amount']>0
        r['store_link']='/admin/vendas?'+urlencode({'inicio':start.isoformat(),'fim':end.isoformat(),'loja':r['id']})
    ranked=sorted(selected,key=lambda r:(-r['amount'],-r['orders'],r['display_name']))
    amount=sum(r['amount'] for r in selected); orders=sum(r['orders'] for r in selected)
    total_previous=sum(r['previous'] for r in selected)
    active=[r for r in selected if r['admission_status']=='approved' and not r['blocked'] and r['eligible_days']>0]
    no_sales=[r for r in active if r['orders']==0]
    return dict(start=start.isoformat(),end=end.isoformat(),previous_start=prev_start.isoformat(),previous_end=prev_end.isoformat(),days=days,
                profiles=profiles,store_id=store_id,rows=ranked,most_orders=sorted(selected,key=lambda r:(-r['orders'],-r['amount']))[:10],most_viewed=sorted(selected,key=lambda r:(-r['views'],r['display_name']))[:10],
                no_sales=no_sales,amount=amount,orders=orders,previous=total_previous,
                change=round((amount-total_previous)*100/total_previous,1) if total_previous else None,
                daily_average=round(amount/days),store_average=round(sum(r['amount'] for r in active)/len(active)) if active else 0,
                cancelled=sum(r['cancelled'] for r in selected),pending=sum(r['pending'] for r in selected),
                daily=[dict(label=k,amount=v) for k,v in daily.items()],monthly=[dict(label=k,amount=v) for k,v in sorted(monthly.items())],
                weekdays=weekdays,hours=hours,ticket=round(amount/orders) if orders else 0)


def sales_alerts(conn,today=None):
    today=today or datetime.now(TZ).date()
    report=sales_report(conn,today-timedelta(days=6),today)
    alerts=[]
    for r in report['rows']:
        if r['admission_status']!='approved' or r['blocked']: continue
        age=(today-local_date(r['created_at']).date()).days
        if age<14: continue
        typ=title=message=None
        if r['orders']==0:
            typ='no-sales';title='Loja sem vendas há 7 dias';message='Sem pedidos finalizados nos últimos 7 dias. Confira se a loja precisa de suporte.'
        elif r['previous']>=10000 and r['change'] is not None and r['change']<=-30:
            typ='decline';title='Vendas caíram pelo menos 30%';message=f"Queda de {abs(r['change']):g}% em relação aos 7 dias anteriores."
        elif r['orders']>=3 and r['previous']>=10000 and r['change'] is not None and r['change']>=50:
            typ='growth';title='Loja com crescimento nas vendas';message=f"Crescimento de {r['change']:g}% em relação aos 7 dias anteriores."
        if typ:
            alerts.append(dict(key=f'{today}:{typ}:{r["id"]}',title=title,name=r['display_name'],message=message,link=r['store_link']))
    return alerts


@router.get('/admin/vendas')
def report_page(request:Request,inicio:str='',fim:str='',mes:str='',loja:int=0):
    _auth(request,'admin');start,end=report_period(inicio,fim,mes)
    conn=_db()
    try: report=sales_report(conn,start,end,loja)
    finally: conn.close()
    return _templates.TemplateResponse('admin_sales.html',_context(request,sales=report))


@router.get('/admin/vendas/avisos')
def alerts(request:Request):
    _auth(request,'admin');conn=_db()
    try: items=sales_alerts(conn)
    finally: conn.close()
    return JSONResponse({'alerts':items},headers={'Cache-Control':'no-store'})
