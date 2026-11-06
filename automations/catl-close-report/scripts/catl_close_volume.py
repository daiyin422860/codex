"""Build the 10-session CATL close report. Pass an explicit Shanghai completed session date."""
from argparse import ArgumentParser
from datetime import date, datetime, timedelta
from pathlib import Path
from decimal import Decimal
from zoneinfo import ZoneInfo
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import subprocess, csv, json, os, sys
BASE=Path(__file__).resolve().parents[1]; ROOT=BASE/'research/宁德收盘图报'; ARCH=ROOT/'分钟档案'
EM='https://push2his.eastmoney.com/api/qt/stock/kline/get'
QQ='https://web.ifzq.gtimg.cn/appstock/app/day/query?code=sz300750'
TS='https://api.tushare.pro'
def writej(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');temp.replace(path)
def readj(path):return json.loads(path.read_bytes())
def fetch(url,data=None):
    r=Request(url,data=json.dumps(data).encode() if data else None,headers={'User-Agent':'Mozilla/5.0','Content-Type':'application/json','Referer':'https://quote.eastmoney.com/' if 'eastmoney' in url else 'https://gu.qq.com/'})
    with urlopen(r,timeout=15) as resp:return json.load(resp)
def ts(api,params):
    token=os.environ.get('TUSHARE_TOKEN','')
    if not token and (BASE/'.env').exists():
        for l in (BASE/'.env').read_text().splitlines():
            if l.startswith('TUSHARE_TOKEN='):token=l.split('=',1)[1].strip().strip('\'"')
    if not token: raise ValueError('Tushare凭证未配置')
    raw=fetch(TS,{'api_name':api,'params':params,'token':token})
    if raw.get('code')!=0 or not raw.get('data'):raise RuntimeError(f'{api}无可用数据')
    body=raw['data'];return [dict(zip(body['fields'],row)) for row in body['items']]
def parse_em(raw):
    if (raw.get('data') or {}).get('code')!='300750':raise ValueError('标的未核验')
    out=[]
    for s in raw['data']['klines']:
        day,o,c,h,l,v,a,_,pct,*_=s.split(',')
        out.append(dict(date=day,open=float(o),close=float(c),high=float(h),low=float(l),pct=float(pct),volume_hands=float(v),amount_yuan=float(a)))
    return out
def slabels(start,n):
    s=datetime.strptime(start,'%H%M')
    return [(s+timedelta(minutes=i)).strftime('%H%M') for i in range(n)]
LABELS=slabels('0930',121)+slabels('1301',120)
def qqarchive(raw,tag):
    for row in (raw.get('data') or {}).get('sz300750',{}).get('data',[]):
        ds=row['date'];bars=[];last=0;mp={x.split()[0]:x.split()[1:] for x in row['data']}
        if '1300' in mp and mp.get('1130')!=mp['1300']:continue
        for t in LABELS:
            if t not in mp:break
            v=int(mp[t][1]);bars.append({'time':t,'hands':v-last});last=v
        if len(bars)==len(LABELS) and all(b['hands']>=0 for b in bars):
            yield {'date':ds,'source':tag,'bars':bars}
def valid(row,d):
    if not row or row.get('date')!=d['date'].replace('-',''):return False
    try:
        bs=row['bars']; times=[b['time'] for b in bs]
        return (times in [LABELS,LABELS[1:]] and all(float(b['hands'])>=0 for b in bs)
                and abs(sum(float(b['hands']) for b in bs)-d['volume_hands'])<=1)
    except (KeyError,TypeError,ValueError): return False
def main():
    ap=ArgumentParser();ap.add_argument('--date',required=True,type=date.fromisoformat);args=ap.parse_args()
    asof=args.date;now=datetime.now(ZoneInfo('Asia/Shanghai'))
    if asof>now.date() or (asof==now.date() and now.hour<15): raise SystemExit('目标交易日尚未收盘')
    stamp=asof.strftime('%Y%m%d');out=ROOT/asof.isoformat();out.mkdir(parents=True,exist_ok=True);ARCH.mkdir(parents=True,exist_ok=True)
    cached=out/'日线_东财.json';daily_src=None
    beg=(asof-timedelta(days=80)).strftime('%Y%m%d')
    ep=EM+'?'+urlencode(dict(secid='0.300750',klt=101,fqt=0,beg=beg,end=stamp,fields1='f1,f2,f3,f4,f5,f6',fields2='f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61'))
    try:
        raw=readj(cached) if cached.exists() else fetch(ep)
        ds=parse_em(raw); assert ds[-1]['date']==asof.isoformat()
        writej(cached,raw);daily_src=ep
    except Exception:
        tr=ts('daily',{'ts_code':'300750.SZ','start_date':beg,'end_date':stamp})
        writej(out/'日线_Tushare.json',tr);daily_src='Tushare daily (vol=手, amount=千元)'
        ds=[dict(date=datetime.strptime(r['trade_date'],'%Y%m%d').date().isoformat(),open=r['open'],close=r['close'],high=r['high'],low=r['low'],pct=r['pct_chg'],volume_hands=r['vol'],amount_yuan=r['amount']*1000) for r in tr]
    ds=sorted(ds,key=lambda d:d['date'])[-10:]
    if len(ds)!=10 or len({d['date'] for d in ds})!=10 or ds[-1]['date']!=asof.isoformat():raise SystemExit('10日完整日线尚未核验，不能沿用旧收盘')
    # Constant-time bootstrap from the verified initial week; later runs use the incremental archive.
    inputs=[BASE/'research/2026-10-26_宁德收盘复盘/minutes_raw.json',BASE/'research/2026-10-27_尾盘核验/minutes.json',BASE/'research/2026-11-06_收盘技术分析/分时/腾讯五日分时.json']
    try:
        fresh=fetch(QQ);writej(out/'腾讯最近五日.json',fresh);inputs.append(out/'腾讯最近五日.json')
    except Exception:pass
    mapping={d['date'].replace('-',''):d for d in ds}
    for path in inputs:
        if not path.exists():continue
        for obj in qqarchive(readj(path),f'腾讯分时 {QQ} | {path.relative_to(BASE)}'):
            k=obj['date']
            if k in mapping and valid(obj,mapping[k]):writej(ARCH/(k+'.json'),obj)
    for k,d in mapping.items():
        f=ARCH/(k+'.json');current=readj(f) if f.exists() else None
        if not valid(current,d):
            try:
                tr=ts('stk_mins',dict(ts_code='300750.SZ',freq='1min',start_date=d['date']+' 09:00:00',end_date=d['date']+' 15:05:00'))
                assert all(x['ts_code']=='300750.SZ' and x['trade_time'][:10]==d['date'] for x in tr)
                tr=sorted(tr,key=lambda x:x['trade_time']); assert tr and abs(float(tr[-1]['close'])-d['close'])<.011
                curr={'date':k,'source':'Tushare stk_mins vol（股）÷100','bars':[{'time':x['trade_time'][11:16].replace(':',''),'hands':float(Decimal(str(x['vol']))/100)} for x in tr]}
                if valid(curr,d):
                    writej(out/(k+'_Tushare分钟.json'),tr);writej(f,curr);current=curr
            except (ValueError,AssertionError,IndexError,KeyError,OSError,RuntimeError):pass
        if valid(current,d):
            d['bars']=current['bars'];d['minute_source']=current['source']
            d['minute_note']='09:30含开盘累计量' if len(d['bars'])==241 else '首分钟按来源合并'
        else:d.update(bars=None,minute_note='该日完整分钟量未通过核验')
    qty=sum(Decimal(str(d['volume_hands']))*100 for d in ds)
    amt=sum(Decimal(str(d['amount_yuan'])) for d in ds)
    if qty<=0 or any(d['volume_hands']<=0 or d['amount_yuan']<=0 for d in ds): raise SystemExit('成交量额缺失')
    vwap=float(amt/qty)
    if not min(d['low'] for d in ds)<=vwap<=max(d['high'] for d in ds):raise SystemExit('成交额或股数单位异常')
    doc=dict(asof=asof.isoformat(),vwap10=vwap,days=ds,total_volume_shares=float(qty),total_amount_yuan=float(amt),daily_source=daily_src,adjustment='不复权；按成交金额和实际成交量估算，不包含交易费。',minute_days=sum(bool(d['bars']) for d in ds),generated_at_bj=now.isoformat())
    data=out/'十日数据.json';writej(data,doc)
    chart=out/'宁德时代_最近10个交易日分时成交量.png'
    subprocess.run([sys.executable,str(BASE/'scripts/render_catl_ten_volume.py'),str(data),str(chart)],check=True)
    with (out/'分钟成交量.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['日期','时间（北京）','成交量（手）'])
        for d in ds:
            for b in d['bars'] or []:w.writerow([d['date'],b['time'][:2]+':'+b['time'][2:],b['hands']])
    print(f"{ds[0]['date']} – {ds[-1]['date']} | 分钟量 {doc['minute_days']}/10天 | 市场成交均价 {vwap:.2f}元 | {chart}")
if __name__=='__main__': main()
