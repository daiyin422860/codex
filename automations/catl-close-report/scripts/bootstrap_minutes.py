"""Restore ten verified per-day minute caches using public quote feeds and optional Tushare."""
import argparse
import json
from pathlib import Path
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from catl_close_volume import ARCH, EM, QQ, fetch, parse_em, qqarchive, ts, valid, writej

SYMBOL = '300750.SZ'


def day_rows(end):
    start = end - timedelta(days=75)
    query = dict(secid='0.300750', klt=101, fqt=0, beg=start.strftime('%Y%m%d'), end=end.strftime('%Y%m%d'),
                 fields1='f1,f2,f3,f4,f5,f6', fields2='f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61')
    try:
        days = parse_em(fetch(EM + '?' + urlencode(query)))
    except (OSError, ValueError, TypeError):
        rows = ts('daily', dict(ts_code=SYMBOL, start_date=query['beg'], end_date=query['end']))
        days = [dict(date=datetime.strptime(r['trade_date'],'%Y%m%d').date().isoformat(), volume_hands=r['vol'],
                     open=r['open'],high=r['high'],low=r['low'],close=r['close']) for r in rows]
    days = sorted(days, key=lambda d:d['date'])[-10:]
    if len(days) != 10 or len({d['date'] for d in days}) != 10 or days[-1]['date'] != end.isoformat():
        raise SystemExit('目标日期或最近十日的日线尚未核验')
    return {d['date'].replace('-',''):d for d in days}


def historical_bars(days, minute_file):
    by_day = defaultdict(list)
    keys = sorted(days)
    if minute_file:
        payload = json.loads(minute_file.read_text(encoding='utf-8'))
        if payload.get('code') != 0:
            raise ValueError('历史分钟存档状态异常')
        body = payload['data']
        rows = [dict(zip(body['fields'], item)) for item in body['items']]
    else:
        rows = ts('stk_mins', dict(ts_code=SYMBOL, freq='1min', start_date=days[keys[0]]['date']+' 09:00:00',
                                   end_date=days[keys[-1]]['date']+' 15:05:00'))
    for row in rows:
        if row['ts_code'] == SYMBOL:
            by_day[row['trade_time'][:10].replace('-','')].append(row)
    for day, rows in by_day.items():
        if day not in days:
            continue
        rows.sort(key=lambda row: row['trade_time'])
        period = dict(open=rows[0]['open'], close=rows[-1]['close'], high=max(r['high'] for r in rows),
                      low=min(r['low'] for r in rows))
        if any(abs(v-days[day][k])>.011 for k,v in period.items()):
            continue
        yield dict(date=day, source='Tushare stk_mins（日量、OHLC交叉核验）',
                   bars=[{'time':r['trade_time'][11:16].replace(':',''),
                          'hands':float(Decimal(str(r['vol']))/100)} for r in rows])


def bootstrap(asof, minute_file):
    now=datetime.now(ZoneInfo('Asia/Shanghai'))
    if asof>now.date() or (asof==now.date() and now.hour<15):
        raise SystemExit('请选择已经收盘的交易日')
    days = day_rows(asof)
    saved = {}

    def collect(candidates):
        for obj in candidates:
            key=obj['date']
            if key in days and key not in saved and valid(obj,days[key]):
                saved[key]=obj

    try:
        collect(qqarchive(fetch(QQ), '腾讯近五日分时'))
    except (OSError,ValueError):
        pass
    missing={k:d for k,d in days.items() if k not in saved}
    if missing:
        try:
            collect(historical_bars(missing, minute_file))
        except (RuntimeError,OSError,ValueError):
            pass
    missing=sorted(days.keys()-saved.keys())
    if missing:
        raise SystemExit('未通过完整分钟核验：'+', '.join(missing)+'。核对历史分钟权限和限频后重试，或提供本机的历史分钟响应。')
    for key,obj in saved.items():
        writej(ARCH/(key+'.json'),obj)
    print('已核验并归档10个交易日：'+', '.join(sorted(saved)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--date',required=True,type=date.fromisoformat)
    p.add_argument('--minute-file', type=Path, help='可选：本机已保存的 Tushare stk_mins 原始 JSON')
    args=p.parse_args()
    bootstrap(args.date,args.minute_file)
