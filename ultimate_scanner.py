#!/usr/bin/env python3
"""
ULTIMATE SCANNER v7.12 — OPTIMIZED DATA LOADING
- Alpaca rate limiting (0.3s between batches)
- Yahoo Finance bulk download (all tickers at once)
"""
import os, io, time, json, sys, traceback, requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from openai import OpenAI
from typing import Dict, List, Optional
from alpaca.data import StockHistoricalDataClient, StockBarsRequest, TimeFrame

print("=" * 60)
print("ULTIMATE SCANNER v7.12 — OPTIMIZED")
print("=" * 60)

def get_env_final(var_name: str) -> str:
    candidates = []
    for k, v in os.environ.items():
        if k == var_name:
            candidates.append(v)
    for val in candidates:
        if val and val.strip() and len(val.strip()) > 10:
            return val.strip()
    keywords_map = {
        'ALPACA_API_KEY': ['ALPACA','API','KEY'],
        'ALPACA_SECRET_KEY': ['ALPACA','SECRET','KEY'],
        'DEEPSEEK_API_KEY': ['DEEPSEEK','API','KEY'],
        'FINNHUB_API_KEY': ['FINNHUB','API','KEY'],
    }
    if var_name in keywords_map:
        kw = keywords_map[var_name]
        for k, v in sorted(os.environ.items()):
            if all(w in k.upper() for w in kw):
                if v and v.strip() and len(v.strip()) > 10:
                    return v.strip()
    return ""

DEEPSEEK_KEY = get_env_final('DEEPSEEK_API_KEY')
ALPACA_KEY = get_env_final('ALPACA_API_KEY')
ALPACA_SECRET = get_env_final('ALPACA_SECRET_KEY')
FINNHUB_KEY = get_env_final('FINNHUB_API_KEY')
ALPACA_FEED = os.environ.get('ALPACA_DATA_FEED', 'iex').lower()
USE_ALPACA = bool(ALPACA_KEY and ALPACA_SECRET)

print(f"Keys: DEEPSEEK {'✅' if DEEPSEEK_KEY else '❌'}, ALPACA {'✅' if USE_ALPACA else '❌'}, FINNHUB {'✅' if FINNHUB_KEY else '❌'}")

CONFIG = {
    'DEEPSEEK_API_KEY': DEEPSEEK_KEY,
    'FINNHUB_API_KEY': FINNHUB_KEY,
    'ALPACA_API_KEY': ALPACA_KEY,
    'ALPACA_SECRET_KEY': ALPACA_SECRET,
    'ALPACA_DATA_FEED': ALPACA_FEED,
    'MODE_A': {'name': 'SNIPER', 'position_size': 2000, 'target_pct': 0.40, 'stop_pct': 0.05, 'min_score': 75, 'hold_days': '3-7', 'top_n': 2},
    'MODE_B': {'name': 'TACTICAL', 'position_size': 1000, 'target_pct': 0.20, 'stop_pct': 0.05, 'min_score': 55, 'hold_days': '1-3', 'top_n': 2},
    'MIN_PRICE': 3.0, 'MIN_VOLUME': 200_000,
    'BANNED_SECTORS': {'Healthcare'},
    'BANNED_INDUSTRIES': {'Biotechnology', 'Drug Manufacturers—General', 'Drug Manufacturers—Specialty & Generic', 'Medical Instruments & Supplies', 'Medical Devices', 'Diagnostics & Research', 'Health Information Services', 'Pharmaceutical Retailers'}
}

# ---------- DATA LOADING ----------
def load_data_yfinance(tickers, days=60):
    """Bulk download via Yahoo Finance (многопоточно внутри библиотеки)"""
    print(f"  📡 Yahoo Finance: {len(tickers)} тикеров (bulk download)...")
    end = datetime.now()
    start = end - timedelta(days=days)
    all_data = {}
    
    try:
        # Загружаем все тикеры одним вызовом — yfinance делает это многопоточно
        df_all = yf.download(tickers, start=start, end=end, progress=False, group_by='ticker')
        
        for t in tickers:
            try:
                if len(tickers) == 1:
                    df = df_all
                else:
                    df = df_all[t]
                
                if not df.empty and len(df) >= 50:
                    df = df.reset_index()
                    # Приводим колонки к стандартному виду
                    df.columns = [c if isinstance(c, str) else c[0] for c in df.columns]
                    all_data[t] = df[['Date','Open','High','Low','Close','Volume']]
            except:
                continue
        
        print(f"    ✅ Yahoo loaded: {len(all_data)} tickers")
    except Exception as e:
        print(f"    ❌ Yahoo error: {e}")
        # Fallback: по одному
        print(f"    🔄 Fallback: sequential download...")
        for i, t in enumerate(tickers):
            if (i+1) % 100 == 0:
                print(f"      {i+1}/{len(tickers)}", flush=True)
            try:
                df = yf.download(t, start=start, end=end, progress=False)
                if not df.empty and len(df) >= 50:
                    df = df.reset_index()
                    all_data[t] = df[['Date','Open','High','Low','Close','Volume']]
            except:
                continue
    
    return all_data

def load_data_alpaca(tickers, days=60):
    if not USE_ALPACA:
        return {}
    try:
        client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)
    except Exception as e:
        print(f"  ❌ Alpaca client error: {e}")
        return {}
    
    end = datetime.now()
    start = end - timedelta(days=days)
    all_data = {}
    batch_size = 100
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    feed = CONFIG.get('ALPACA_DATA_FEED', 'iex')
    
    print(f"  📡 Alpaca: {len(tickers)} тикеров, {total_batches} батчей, feed={feed.upper()}")
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        bn = i // batch_size + 1
        
        try:
            request = StockBarsRequest(
                symbol_or_symbols=batch,
                timeframe=TimeFrame.Day,
                start=start,
                end=end,
                limit=10000,
                feed=feed
            )
            bars = client.get_stock_bars(request)
            
            # Правильная проверка BarSet
            try:
                symbols_in_response = list(bars.data.keys()) if hasattr(bars, 'data') else []
            except:
                symbols_in_response = []
            
            if bn == 1:
                print(f"    🔍 Debug батч 1: символов в ответе = {len(symbols_in_response)}")
                if symbols_in_response:
                    print(f"    Пример: {symbols_in_response[0]}")
                else:
                    print(f"    ⚠️ Пустой ответ Alpaca!")
            
            for symbol in batch:
                if symbol in symbols_in_response:
                    bar_list = bars.data[symbol]
                    data = []
                    for bar in bar_list:
                        data.append({
                            'Open': bar.open, 'High': bar.high,
                            'Low': bar.low, 'Close': bar.close,
                            'Volume': bar.volume
                        })
                    df = pd.DataFrame(data)
                    if not df.empty and len(df) >= 50:
                        all_data[symbol] = df
            
            if bn % 10 == 0:
                print(f"    Progress: {bn}/{total_batches} batches, {len(all_data)} tickers loaded", flush=True)
            
            # Rate limiting для бесплатного тарифа
            if bn < total_batches:
                time.sleep(0.3)  # 300ms между батчами
            
        except Exception as e:
            print(f"    ⚠️ Batch {bn} error: {e}")
            # При ошибке тоже ждём
            time.sleep(0.5)
    
    return all_data

# ---------- AI ----------
class DeepSeekAnalyzer:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    def analyze(self, ticker, data, mode):
        mc = CONFIG[f'MODE_{mode}']
        prompt = (
            f"Analyze {ticker} for {mc['name']}.\n"
            f"Price ${data.get('price','N/A')} | Pos {data.get('position_pct','N/A')}% | RVOL {data.get('rvol','N/A')}x\n"
            f"TASK: 🎯 Тип | 🧠 Физика | 💥 Сигнал (стоп, цель). Short, Russian."
        )
        try:
            r = self.client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], max_tokens=300, temperature=0.3)
            txt = r.choices[0].message.content
            blocks = {'full': txt, 'type': '', 'physics': '', 'signal': ''}
            for s in txt.split('###'):
                s = s.strip()
                if 'тип' in s.lower(): blocks['type'] = s.split('\n',1)[-1].strip()
                elif 'физика' in s.lower(): blocks['physics'] = s.split('\n',1)[-1].strip()
                elif 'сигнал' in s.lower(): blocks['signal'] = s.split('\n',1)[-1].strip()
            return blocks
        except Exception as e:
            return {'full': f"AI Error: {e}", 'type': '', 'physics': '', 'signal': ''}

# ---------- SCORING ----------
class DataSources:
    def __init__(self, config): self.config = config
    def get_options_anomaly(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            exps = stock.options
            if not exps: return {'score':0,'unusual_calls':0,'max_vol_oi':0}
            uc, mv = 0, 0
            for ex in exps[:3]:
                try:
                    ch = stock.option_chain(ex).calls
                    ch = ch[ch['volume']>50]
                    for _,o in ch.iterrows():
                        v,oi=o['volume'],o['openInterest']
                        if oi>0 and v/oi>3.0: uc+=1; mv=max(mv,v/oi)
                except: continue
            sc = 40 if uc>10 else 30 if uc>5 else 15 if uc>2 else 0
            return {'score':sc,'unusual_calls':uc,'max_vol_oi':round(mv,2)}
        except: return {'score':0,'unusual_calls':0,'max_vol_oi':0}
    def get_insider_activity(self, ticker):
        try:
            r = requests.get("http://openinsider.com/screener", params={'t':ticker,'td':7,'xc':'1'}, timeout=10)
            tables = pd.read_html(r.content)
            if tables:
                df = tables[-1]
                buys = df[df['Value ($)']>50000]
                if not buys.empty:
                    tv = buys['Value ($)'].sum()
                    return {'count':len(buys),'total_value':tv,'score':30 if tv>500000 else 20 if tv>100000 else 10}
        except: pass
        return {'count':0,'total_value':0,'score':0}
    def get_finnhub_data(self, ticker):
        ak = self.config.get('FINNHUB_API_KEY')
        if not ak: return {'news_sentiment':'N/A','news_count':0,'earnings_surprise':None}
        try:
            r = requests.get("https://finnhub.io/api/v1/company-news", params={'symbol':ticker,'from':(datetime.now()-timedelta(7)).strftime('%Y-%m-%d'),'to':datetime.now().strftime('%Y-%m-%d'),'token':ak}, timeout=5)
            news = r.json() if r.status_code==200 else []
            bl = sum(1 for n in news for k in ['beat','surge','upgrade','growth'] if k in n.get('headline','').lower())
            br = sum(1 for n in news for k in ['miss','cut','downgrade','loss'] if k in n.get('headline','').lower())
            sent = 'BULLISH' if bl>br else 'BEARISH' if br>bl else 'NEUTRAL'
            return {'news_count':len(news),'news_sentiment':sent,'earnings_surprise':None}
        except: return {'news_sentiment':'N/A','news_count':0,'earnings_surprise':None}
    def get_short_data(self, ticker):
        try:
            info = yf.Ticker(ticker).info
            sp = info.get('shortPercentOfFloat',0)*100
            sc = 25 if sp>20 else 15 if sp>15 else 5 if sp>10 else 0
            return {'short_pct':round(sp,2),'score':sc}
        except: return {'short_pct':0,'score':0}
    def get_dark_pool_data(self, ticker):
        return {'dp_ratio':0,'trend_5d':0,'score':0}
    def get_congress_trading(self, ticker):
        return {'total_buys':0,'score':0}

class SignalScorer:
    def __init__(self, ds): self.ds = ds
    def is_biopharma(self, ticker):
        try:
            i = yf.Ticker(ticker).info
            return i.get('sector','') in CONFIG['BANNED_SECTORS'] or i.get('industry','') in CONFIG['BANNED_INDUSTRIES']
        except: return False
    def score(self, ticker, df, cp, pp, dp, rv, hp):
        o = self.ds.get_options_anomaly(ticker)
        i = self.ds.get_insider_activity(ticker)
        f = self.ds.get_finnhub_data(ticker)
        s = self.ds.get_short_data(ticker)
        a_s, a_sig = 0, []
        if o['score']>=30: a_s+=o['score']; a_sig.append(f"⚡ Options: {o['unusual_calls']} unusual")
        if i['score']>=20: a_s+=i['score']; a_sig.append(f"💼 Insider: {i['count']} buys")
        b_s, b_sig = 0, []
        if rv>2.5: b_s+=25; b_sig.append(f"📈 RVOL: {rv:.1f}x")
        elif rv>2.0: b_s+=15; b_sig.append(f"📈 RVOL: {rv:.1f}x")
        if f['news_sentiment']=='BULLISH': b_s+=15; b_sig.append("📰 News: Bullish")
        if s['score']>=15: b_s+=s['score']; b_sig.append(f"🎯 Short: {s['short_pct']}%")
        if 50<=pp<=85: b_s+=15; b_sig.append(f"📊 Position: {pp:.0f}%")
        if hp<2: b_s+=10; b_sig.append(f"🎯 HOD Pinch: {hp:.1f}%")
        return {
            'ticker':ticker,'price':round(cp,2),'position_pct':round(pp,1),'discount_pct':round(dp,1),
            'rvol':round(rv,2),'hod_pinch':round(hp,1),
            'mode_a_score':a_s,'mode_a_signals':a_sig,'mode_a_qualifies':a_s>=CONFIG['MODE_A']['min_score'],
            'mode_b_score':b_s,'mode_b_signals':b_sig,'mode_b_qualifies':b_s>=CONFIG['MODE_B']['min_score'],
            'unusual_calls':o['unusual_calls'],'insider_buys':i['count'],'insider_value':i['total_value'],
            'short_pct':s['short_pct'],'dp_ratio':0,'congress_buys':0,
            'earnings_surprise':None,'news_sentiment':f['news_sentiment']
        }

# ---------- SCANNER ----------
class UltimateScanner:
    def __init__(self):
        self.ds = DataSources(CONFIG)
        self.scorer = SignalScorer(self.ds)
        self.ai = DeepSeekAnalyzer(CONFIG['DEEPSEEK_API_KEY'])
        self.universe = self._load_universe()
    
    def _load_universe(self):
        cache = 'universe_cache.csv'
        if os.path.exists(cache) and (time.time()-os.path.getmtime(cache))<86400:
            t = pd.read_csv(cache)['Symbol'].tolist()
            print(f"✅ Universe from cache: {len(t)} tickers")
            return t
        print("🔄 Loading universe via Alpaca...")
        tickers = []
        if USE_ALPACA:
            try:
                headers = {"APCA-API-KEY-ID":ALPACA_KEY,"APCA-API-SECRET-KEY":ALPACA_SECRET}
                params = {"status":"active","asset_class":"us_equity","exchange":"NASDAQ,NYSE,ARCA","tradable":"true"}
                resp = requests.get("https://paper-api.alpaca.markets/v2/assets", headers=headers, params=params, timeout=30)
                resp.raise_for_status()
                tickers = [a['symbol'] for a in resp.json() if a.get('symbol')]
            except Exception as e:
                print(f"  ❌ Alpaca assets error: {e}")
        if not tickers:
            tickers = ['AAPL','MSFT','GOOGL','AMZN','NVDA','META','TSLA','AMD','INTC']
        pd.DataFrame({'Symbol':tickers}).to_csv(cache, index=False)
        print(f"✅ Universe: {len(tickers)} tickers")
        return tickers
    
    def run(self):
        start = time.time()
        print("="*60)
        print("🎯 ULTIMATE SCANNER v7.12")
        print("="*60)
        print(f"📊 Universe: {len(self.universe)} tickers")
        
        # Try Alpaca first
        print("\n📥 Loading via Alpaca...")
        all_data = load_data_alpaca(self.universe, days=60)
        if not all_data:
            print("⚠️ Alpaca returned 0 tickers. Switching to Yahoo Finance...")
            all_data = load_data_yfinance(self.universe, days=60)
        
        print(f"\n✅ Loaded: {len(all_data)} tickers")
        if not all_data:
            print("❌ No data at all.")
            return {"mode_a":[],"mode_b":[],"stats":{}}
        
        # Filtering
        print("\n🔍 Filtering...")
        filtered = []
        for t, df in all_data.items():
            try:
                cp = df['Close'].iloc[-1]; av = df['Volume'].tail(20).mean()
                if cp < CONFIG['MIN_PRICE'] or av < CONFIG['MIN_VOLUME']: continue
                h6 = df['High'].max(); l6 = df['Low'].min()
                pp = ((cp-l6)/(h6-l6)*100) if h6>l6 else 50
                dp = ((cp-h6)/h6*100)
                if not (pp<70 and dp<-25) and not (50<=pp<=85): continue
                filtered.append(t)
            except: continue
        print(f"✅ Filtered: {len(filtered)} tickers")
        
        # Scoring
        print(f"\n🔍 Scoring {len(filtered)}...")
        results = []
        for i, t in enumerate(filtered, 1):
            if i%20==0: print(f"  {i}/{len(filtered)}", flush=True)
            df = all_data[t]
            if self.scorer.is_biopharma(t): continue
            try:
                cp = df['Close'].iloc[-1]; av = df['Volume'].tail(20).mean()
                h6 = df['High'].max(); l6 = df['Low'].min()
                pp = ((cp-l6)/(h6-l6)*100) if h6>l6 else 50
                dp = ((cp-h6)/h6*100)
                rv = df['Volume'].iloc[-1]/av if av>0 else 0
                td = df.iloc[-1]
                hp = ((td['High']-td['Close'])/td['High']*100) if td['High']>0 else 0
                r = self.scorer.score(t, df, cp, pp, dp, rv, hp)
                if r and (r['mode_a_qualifies'] or r['mode_b_qualifies']):
                    results.append(r)
            except: continue
        
        ma = [r for r in results if r['mode_a_qualifies']]
        mb = [r for r in results if r['mode_b_qualifies'] and not r['mode_a_qualifies']]
        ma.sort(key=lambda x: x['mode_a_score'], reverse=True)
        mb.sort(key=lambda x: x['mode_b_score'], reverse=True)
        ta, tb = ma[:2], mb[:2]
        print(f"\n🎯 MODE A: {len(ma)} found, top {len(ta)}")
        print(f"⚡ MODE B: {len(mb)} found, top {len(tb)}")
        
        print("\n🧠 AI analysis...")
        for r in ta: r['ai'] = self.ai.analyze(r['ticker'], r, 'A')
        for r in tb: r['ai'] = self.ai.analyze(r['ticker'], r, 'B')
        
        ts = datetime.now().strftime('%Y%m%d_%H%M')
        output = {'timestamp':ts,'mode_a':ta,'mode_b':tb,'stats':{'universe_size':len(self.universe),'loaded':len(all_data),'filtered':len(filtered),'mode_a_total':len(ma),'mode_b_total':len(mb),'scan_time_sec':round(time.time()-start,1)}}
        with open('scan_results.json','w',encoding='utf-8') as f: json.dump(output, f, ensure_ascii=False, indent=2)
        
        print("\n" + "="*60)
        for label, arr in [("🔴 MODE A: SNIPER", ma), ("🟡 MODE B: TACTICAL", mb)]:
            print(label); print("="*60)
            if not arr: print("  ⚪ No signals")
            else:
                for r in arr:
                    print(f"\n📈 {r['ticker']} | ${r['price']} | Score: {r[f'mode_{label.split()[-1].lower()}_score']}")
                    for s in r[f'mode_{label.split()[-1].lower()}_signals'][:5]: print(f"   {s}")
                    if r.get('ai'):
                        if r['ai']['type']: print(f"🎯 {r['ai']['type']}")
                        if r['ai']['signal']: print(f"💥 {r['ai']['signal']}")
        print(f"\n💾 Saved: scan_results.json | ⏱️ {time.time()-start:.1f} sec")
        return output

if __name__ == "__main__":
    pass
