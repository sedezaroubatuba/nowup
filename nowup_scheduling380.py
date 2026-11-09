"""Same-day requested slots and atomic expiry of unanswered marketplace orders."""
import asyncio
import logging
from datetime import datetime,timedelta,timezone,time
from zoneinfo import ZoneInfo
from fastapi import Request,Form,HTTPException
from fastapi.responses import RedirectResponse
TZ=ZoneInfo('America/Sao_Paulo')
G={}
REASON='Cancelado automaticamente: a loja não respondeu em 5 minutos.'


def windows(p,now):
    schedule=G['parse_business_hours'](p['business_hours'])
    result=[]
    for offset in (-1,0):
        day=now.date()+timedelta(days=offset)
        row=schedule.get(G['DAYS'][day.weekday()],{})
        if not row.get('enabled'):continue
        try:
            start=datetime.combine(day,time.fromisoformat(row['start']),TZ)
            end=datetime.combine(day,time.fromisoformat(row['end']),TZ)
        except (ValueError,KeyError,TypeError):continue
        if end<=start:end+=timedelta(days=1)
        result.append((start,end))
    return result


def slots(p,now=None):
    p=dict(p);now=now or datetime.now(TZ)
    if not p.get('allow_schedule380') or p.get('business_status','open')!='open':return []
    result=[]
    for start,end in windows(p,now):
        value=max(start,now.replace(second=0,microsecond=0)+timedelta(minutes=1))
        # Fifteen-minute service slots, restricted to today's local date.
        value+=timedelta(minutes=(-value.minute)%15)
        while value<end and value.date()==now.date():
            result.append({'value':value.strftime('%Y-%m-%dT%H:%M'),'label':value.strftime('%H:%M')})
            value+=timedelta(minutes=15)
    return sorted(result,key=lambda r:r['value'])


def validate(p,raw,now=None):
    now=now or datetime.now(TZ)
    if not raw:return '', ''
    if raw not in {r['value'] for r in slots(p,now)}:
        raise HTTPException(409,'Escolha um horário disponível para hoje. Atualize o cardápio.')
    selected=datetime.fromisoformat(raw).replace(tzinfo=TZ)
    start=next(start for start,end in windows(p,now) if start<=selected<end)
    return selected.astimezone(timezone.utc).isoformat(), max(start,now).astimezone(timezone.utc).isoformat()


def save(c,oid,p,raw):
    selected,start=validate(p,raw)
    c.execute('UPDATE orders SET scheduled_for380=?,accept_after380=? WHERE id=?',(selected,start,oid))
    return selected


def expire(c,now=None,order_id=None):
    now=now or datetime.now(timezone.utc);stamp=now.isoformat();cutoff=(now-timedelta(minutes=5)).isoformat()
    where="status='new' AND COALESCE(order_origin,'legacy')<>'external' AND created_at<=? AND (COALESCE(accept_after380,'')='' OR accept_after380<=?)"
    params=[cutoff,cutoff]
    if order_id is not None:where+=' AND id=?';params.append(order_id)
    rows=c.execute('SELECT id,customer_id,order_code,tracking_token FROM orders WHERE '+where+' ORDER BY id LIMIT 500',params).fetchall()
    count=0
    for o in rows:
        changed=c.execute("UPDATE orders SET status='cancelled',cancellation_reason=?,updated_at=? WHERE id=? AND status='new' AND created_at<=? AND (COALESCE(accept_after380,'')='' OR accept_after380<=?)",(REASON,stamp,o['id'],cutoff,cutoff)).rowcount
        if not changed:continue
        count+=1
        c.execute('INSERT INTO order_status_history(order_id,status,created_at) VALUES(?,?,?)',(o['id'],'cancelled',stamp))
        c.execute('DELETE FROM push_jobs WHERE order_id=?',(o['id'],))
        if o['customer_id']:
            title='Pedido cancelado por falta de resposta'
            body=o['order_code']+' — '+REASON
            n=c.execute('INSERT INTO notifications(user_id,title,message,link,created_at) VALUES(?,?,?,?,?)',(o['customer_id'],title,body,'/pedido/'+o['tracking_token'],stamp))
            G['nowup_alerts112'].enqueue(c,o['customer_id'],n.lastrowid,{'title':title,'body':body,'url':'/pedido/'+o['tracking_token'],'tag':'nowup-expired-'+str(o['id'])})
    return count


def tick():
    c=G['db']()
    try:expire(c);c.commit()
    finally:c.close()


def install(g):
    G.update(g)
    g['templates'].env.globals['schedule_options380']=slots
    g['templates'].env.globals['schedule_label380']=lambda value:datetime.fromisoformat(value).astimezone(TZ).strftime('%d/%m às %H:%M')
    @g['app'].post('/painel/agendamento380')
    def setting(request:Request,enabled:str=Form('')):
        u=g['require_user'](request,'professional');c=g['db']()
        try:
            c.execute('UPDATE professionals SET allow_schedule380=? WHERE user_id=?',(1 if enabled=='1' else 0,u['id']));c.commit()
        finally:c.close()
        return RedirectResponse('/painel#horarios',303)
    task=None;stop=None
    async def runner():
        while not stop.is_set():
            try:await asyncio.to_thread(tick)
            except Exception:logging.exception('Order expiry processing failed')
            try:await asyncio.wait_for(stop.wait(),timeout=2)
            except asyncio.TimeoutError:pass
    async def start():
        nonlocal task,stop
        stop=asyncio.Event();task=asyncio.create_task(runner())
    async def shutdown():
        if task:stop.set();await task
    g['app'].router.add_event_handler('startup',start)
    g['app'].router.on_shutdown.insert(0,shutdown)
