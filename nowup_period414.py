"""Simple sales periods in the merchant's local calendar."""
from datetime import date,datetime,timedelta
from fastapi import HTTPException
from zoneinfo import ZoneInfo

def selected_period(params,today=None):
    today=today or datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    mode=params.get('periodo','')
    try:
        if mode=='dia':start=end=date.fromisoformat(params.get('dia') or today.isoformat())
        elif mode=='mes':
            start=date.fromisoformat((params.get('mes') or today.strftime('%Y-%m'))+'-01')
            end=(start.replace(day=28)+timedelta(days=4)).replace(day=1)-timedelta(days=1)
        elif mode=='ano':
            year=int(params.get('ano') or today.year)
            start,end=date(year,1,1),date(year,12,31)
        elif mode:raise ValueError()
        else:
            start=date.fromisoformat(params.get('inicio') or today.replace(day=1).isoformat())
            end=date.fromisoformat(params.get('fim') or today.isoformat())
        if start>end or (end-start).days>366:raise ValueError()
    except (ValueError,TypeError,OverflowError):raise HTTPException(400,'Escolha um dia, mês ou ano válido.')
    return start,end
