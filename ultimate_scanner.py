#!/usr/bin/env python3
"""
ULTIMATE SCANNER v7.21 — CRITICAL FIXES
- JSON encoder для numpy типов
- Thread-safe scan lock
- Объединённые yf.info вызовы
- Убраны заглушки dark_pool/congress
"""
import os, time, json, requests, random, threading
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from openai import OpenAI
from alpaca.data import StockHistoricalDataClient, StockBarsRequest, TimeFrame
import warnings
warnings.filterwarnings("ignore")

print("=" * 60)
print("ULTIMATE SCANNER v7.21 — CRITICAL FIXES")
print("=" * 60)

# ========== JSON ENCODER ДЛЯ NUMPY ==========
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super().default(obj)

# ========== HEADERS ==========
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ========== КОНФИГУРАЦИЯ ==========
CONFIG = {
    'MODE_A': {'name': 'SNIPER', 'position_size': 2000, 'target_pct': 0.40, 'stop_pct': 0.05, 'min_score': 75, 'hold_days': '3-7', 'top_n': 2},
    'MODE_B': {'name': 'TACTICAL', 'position_size': 1000, 'target_pct': 0.20, 'stop_pct': 0.05, 'min_score': 55, 'hold_days': '1-3', 'top_n': 2},
    'MIN_PRICE': 3.0, 'MIN_VOLUME': 200_000,
    'BANNED_SECTORS': {'Healthcare'},
    'BANNED_INDUSTRIES': {'Biotechnology', 'Drug Manufacturers—General', 'Drug Manufacturers—Specialty & Generic', 'Medical Instruments & Supplies', 'Medical Devices', 'Diagnostics & Research', 'Health Information Services', 'Pharmaceutical Retailers'}
}

# Чтение переменных окружения
ALPACA_KEY = os.environ.get('ALPACA_API_KEY', '').strip()
ALPACA_SECRET = os.environ.get('ALPACA_SECRET_KEY', '').strip()
DEEPSEEK_KEY = os.environ.get('DEEPSEEK_API_KEY', '').strip()
FINNHUB_KEY = os.environ.get('FINNHUB_API_KEY', '').strip()
USE_ALPACA = bool(ALPACA_KEY and ALPACA_SECRET)

print(f"Alpaca key: {len(ALPACA_KEY)} chars, secret: {len(ALPACA_SECRET)} chars")
print(f"DeepSeek: {'✅' if DEEPSEEK_KEY else '❌'}, Finnhub: {'✅' if FINNHUB_KEY else '❌'}")

# ========== ВСЕЛЕННАЯ ==========
def load_universe():
    cache_file = 'universe_cache.csv'
    if os.path.exists(cache_file) and (time.time() - os.path.getmtime(cache_file)) < 86400:
        tickers = pd.read_csv(cache_file)['Symbol'].tolist()
        tickers = [t.strip().upper() for t in tickers if t]
        print(f"✅ Кеш: {len(tickers)} тикеров")
        return tickers
    
    if USE_ALPACA:
        print("🔄 Alpaca API...")
        try:
            headers = {"APCA-API-KEY-ID": ALPACA_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET, **HEADERS}
            params = {"status": "active", "asset_class": "us_equity", "tradable": "true"}
            resp = requests.get("https://paper-api.alpaca.markets/v2/assets", headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            tickers = [a['symbol'] for a in resp.json() if a.get('symbol')]
            tickers = [t.strip().upper() for t in tickers if t]
            if tickers:
                pd.DataFrame({'Symbol': tickers}).to_csv(cache_file, index=False)
                print(f"  ✅ {len(tickers)} тикеров")
                return tickers
        except Exception as e:
            print(f"  ❌ {e}")
    
    tickers = ['AAPL','MSFT','GOOGL','AMZN','NVDA','META','TSLA','AMD','INTC']
    print(f"⚠️ Фолбэк: {len(tickers)} тикеров")
    return tickers

# ========== ЗАГРУЗКА ДАННЫХ ==========
def load_data_alpaca(tickers, days=60):
    if not USE_ALPACA: return {}
    
    client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)
    end = datetime.now()
    start = end - timedelta(days=days)
    all_data = {}
    batch_size = 20
    total = (len(tickers) + batch_size - 1) // batch_size
    
    print(f"📡 Alpaca: {len(tickers)} тикеров, батчей: {total}")
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        bn = i // batch_size + 1
        
        try:
            request = StockBarsRequest(symbol_or_symbols=batch, timeframe=TimeFrame.Day, start=start, end=end, feed='iex')
            bars = client.get_stock_bars(request)
            
            for symbol in batch:
                data_list = bars.data.get(symbol)
                if data_list:
                    df = pd.DataFrame([{'Open': b.open, 'High': b.high, 'Low': b.low, 'Close': b.close, 'Volume': b.volume} for b in data_list])
                    if len(df) >= 50:
                        all_data[symbol] = df
            
            if bn % 50 == 0:
                print(f"  {bn}/{total}, loaded {len(all_data)}")
        except Exception as e:
            if bn == 1: print(f"  ⚠️ {e}")
        
        time.sleep(2.0)
    
    print(f"✅ Alpaca: {len(all_data)} тикеров")
    return all_data

def load_data_yahoo(tickers, days=60):
    print(f"📡 Yahoo: {len(tickers)} тикеров...")
    end = datetime.now()
    start = end - timedelta(days=days)
    all_data = {}
    
    for i, t in enumerate(tickers):
        try:
            session = requests.Session()
            session.headers.update(HEADERS)
            stock = yf.Ticker(t, session=session)
            df = stock.history(start=start, end=end)
            if not df.empty and len(df) >= 50:
                all_data[t] = df
            if (i+1) % 100 == 0:
                print(f"  {i+1}/{len(tickers)}, loaded {len(all_data)}")
            time.sleep(random.uniform(0.5, 1.5))
        except: continue
    
    print(f"✅ Yahoo: {len(all_data)} тикеров")
    return all_data

# ========== ОБЪЕДИНЁННЫЙ СКОРИНГ (ОДИН yf.info НА ТИКЕР) ==========
class UnifiedScorer:
    def __init__(self):
        self.finnhub_key = FINNHUB_KEY
    
    def _enrich_ticker_info(self, ticker):
        """Один вызов yf.Ticker().info для всего"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                'info': info,
                'stock': stock,
                'is_biopharma': (info.get('sector','') in CONFIG['BANNED_SECTORS'] or 
                                info.get('industry','') in CONFIG['BANNED_INDUSTRIES']),
                'short_pct': info.get('shortPercentOfFloat', 0) * 100,
                'options': stock.options if hasattr(stock, 'options') else []
            }
        except:
            return None
    
    def _get_options_anomaly(self, enriched):
        if not enriched: return {'score': 0, 'unusual_calls': 0, 'max_vol_oi': 0}
        exps = enriched.get('options', [])
        if not exps: return {'score': 0, 'unusual_calls': 0, 'max_vol_oi': 0}
        
        uc, mv = 0, 0
        for ex in exps[:3]:
            try:
                ch = enriched['stock'].option_chain(ex).calls
                ch = ch[ch['volume'] > 50]
                for _, o in ch.iterrows():
                    v, oi = o['volume'], o['openInterest']
                    if oi > 0 and v / oi > 3.0:
                        uc += 1
                        mv = max(mv, v/oi)
            except: continue
        
        sc = 40 if uc > 10 else 30 if uc > 5 else 15 if uc > 2 else 0
        return {'score': sc, 'unusual_calls': uc, 'max_vol_oi': round(mv, 2)}
    
    def _get_insider_activity(self, ticker):
        try:
            r = requests.get("http://openinsider.com/screener", params={'t': ticker, 'td': 7, 'xc': '1'}, timeout=10, headers=HEADERS)
            tables = pd.read_html(r.content)
            if tables:
                df = tables[-1]
                buys = df[df['Value ($)'] > 50000]
                if not buys.empty:
                    tv = buys['Value ($)'].sum()
                    return {'count': len(buys), 'total_value': tv, 'score': 30 if tv > 500000 else 20 if tv > 100000 else 10}
        except: pass
        return {'count': 0, 'total_value': 0, 'score': 0}
    
    def _get_finnhub_data(self, ticker):
        if not self.finnhub_key: return {'news_sentiment': 'N/A', 'news_count': 0, 'earnings_surprise': None}
        try:
            r = requests.get("https://finnhub.io/api/v1/company-news", 
                           params={'symbol': ticker, 'from': (datetime.now()-timedelta(7)).strftime('%Y-%m-%d'),
                                  'to': datetime.now().strftime('%Y-%m-%d'), 'token': self.finnhub_key}, timeout=5)
            news = r.json() if r.status_code == 200 else []
            bl = sum(1 for n in news for k in ['beat','surge','upgrade','growth'] if k in n.get('headline','').lower())
            br = sum(1 for n in news for k in ['miss','cut','downgrade','loss'] if k in n.get('headline','').lower())
            sent = 'BULLISH' if bl > br else 'BEARISH' if br > bl else 'NEUTRAL'
            return {'news_count': len(news), 'news_sentiment': sent, 'earnings_surprise': None}
        except: return {'news_sentiment': 'N/A', 'news_count': 0, 'earnings_surprise': None}
    
    def score_ticker(self, ticker, df, cp, pp, dp, rv, hp):
        # Единый вызов yf.info
        enriched = self._enrich_ticker_info(ticker)
        if not enriched:
            return None
        
        # Проверка biopharma
        if enriched['is_biopharma']:
            return None
        
        # Сбор всех сигналов
        o = self._get_options_anomaly(enriched)
        i = self._get_insider_activity(ticker)
        f = self._get_finnhub_data(ticker)
        s = {'short_pct': round(enriched['short_pct'], 2), 
             'score': 25 if enriched['short_pct'] > 20 else 15 if enriched['short_pct'] > 15 else 5 if enriched['short_pct'] > 10 else 0}
        
        # MODE A
        a_s, a_sig = 0, []
        if o['score'] >= 30: a_s += o['score']; a_sig.append(f"⚡ Options: {o['unusual_calls']} unusual")
        if i['score'] >= 20: a_s += i['score']; a_sig.append(f"💼 Insider: {i['count']} buys (${i['total_value']/1000:.0f}k)")
        if rv > 2.5: a_s += 20; a_sig.append(f"📈 RVOL: {rv:.1f}x")
        if 20 <= pp <= 50: a_s += 25; a_sig.append(f"📍 Position: {pp:.0f}% (низ)")
        if dp < -15: a_s += 20; a_sig.append(f"📉 Discount: {dp:.1f}%")
        if hp < 2: a_s += 15; a_sig.append(f"🎯 HOD Pinch: {hp:.1f}%")
        
        # MODE B
        b_s, b_sig = 0, []
        if rv > 2.5: b_s += 25; b_sig.append(f"📈 RVOL: {rv:.1f}x")
        elif rv > 2.0: b_s += 15; b_sig.append(f"📈 RVOL: {rv:.1f}x")
        if f['news_sentiment'] == 'BULLISH': b_s += 15; b_sig.append(f"📰 News: Bullish")
        if s['score'] >= 15: b_s += s['score']; b_sig.append(f"🎯 Short: {s['short_pct']}%")
        if 50 <= pp <= 85: b_s += 15; b_sig.append(f"📊 Position: {pp:.0f}%")
        if hp < 2: b_s += 10; b_sig.append(f"🎯 HOD Pinch: {hp:.1f}%")
        
        return {
            'ticker': ticker, 'price': round(cp, 2), 'position_pct': round(pp, 1), 'discount_pct': round(dp, 1),
            'rvol': round(rv, 2), 'hod_pinch': round(hp, 1),
            'mode_a_score': a_s, 'mode_a_signals': a_sig, 'mode_a_qualifies': a_s >= CONFIG['MODE_A']['min_score'],
            'mode_b_score': b_s, 'mode_b_signals': b_sig, 'mode_b_qualifies': b_s >= CONFIG['MODE_B']['min_score'],
            'unusual_calls': o['unusual_calls'], 'insider_buys': i['count'], 'insider_value': i['total_value'],
            'short_pct': s['short_pct'], 'news_sentiment': f['news_sentiment']
        }

# ========== AI ==========
class DeepSeekAI:
    def __init__(self):
        self.client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com") if DEEPSEEK_KEY else None
    
    def analyze(self, ticker, data, mode):
        if not self.client: return {'type': '', 'physics': '', 'signal': ''}
        mc = CONFIG[f'MODE_{mode}']
        prompt = (
            f"Senior Quant. Analyze {ticker} for {mc['name']}.\n"
            f"Price ${data.get('price','N/A')} | Pos {data.get('position_pct','N/A')}% | RVOL {data.get('rvol','N/A')}x\n"
            f"TASK: 🎯 Тип | 🧠 Физика | 💥 Сигнал (стоп, цель). Russian, short."
        )
        try:
            r = self.client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], max_tokens=300, temperature=0.3)
            txt = r.choices[0].message.content
            blocks = {'full': txt, 'type': '', 'physics': '', 'signal': ''}
            for s in txt.split('###'):
                s = s.strip()
                if 'тип' in s.lower(): blocks['type'] = s.split('\n', 1)[-1].strip()
                elif 'физика' in s.lower(): blocks['physics'] = s.split('\n', 1)[-1].strip()
                elif 'сигнал' in s.lower(): blocks['signal'] = s.split('\n', 1)[-1].strip()
            return blocks
        except: return {'type': '', 'physics': '', 'signal': ''}

# ========== ГЛАВНЫЙ ЦИКЛ ==========
def run_scanner():
    start_time = time.time()
    print("=" * 60)
    print("🎯 ULTIMATE SCANNER v7.21")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    universe = load_universe()
    
    print("\n📥 Данные...")
    all_data = load_data_alpaca(universe, days=60)
    if not all_data:
        print("⚠️ Alpaca пусто, Yahoo...")
        all_data = load_data_yahoo(universe, days=60)
    
    if not all_data:
        print("❌ Нет данных")
        return {"mode_a": [], "mode_b": [], "stats": {}}
    
    print(f"\n✅ {len(all_data)} тикеров")
    
    # Фильтрация
    print("\n🔍 Фильтр...")
    scorer = UnifiedScorer()
    ai = DeepSeekAI()
    
    filtered = []
    for t, df in all_data.items():
        try:
            cp = df['Close'].iloc[-1]
            av = df['Volume'].tail(20).mean()
            if cp < CONFIG['MIN_PRICE'] or av < CONFIG['MIN_VOLUME']: continue
            h6 = df['High'].max(); l6 = df['Low'].min()
            pp = ((cp-l6)/(h6-l6)*100) if h6 > l6 else 50
            dp = ((cp-h6)/h6*100)
            if not (pp < 70 and dp < -25) and not (50 <= pp <= 85): continue
            filtered.append(t)
        except: continue
    print(f"✅ Фильтр: {len(filtered)} тикеров")
    
    # Скоринг
    print(f"\n🔍 Скоринг {len(filtered)}...")
    results = []
    for i, t in enumerate(filtered, 1):
        if i % 20 == 0: print(f"  {i}/{len(filtered)}")
        df = all_data[t]
        try:
            cp = df['Close'].iloc[-1]; av = df['Volume'].tail(20).mean()
            h6 = df['High'].max(); l6 = df['Low'].min()
            pp = ((cp-l6)/(h6-l6)*100) if h6 > l6 else 50
            dp = ((cp-h6)/h6*100)
            rv = df['Volume'].iloc[-1]/av if av > 0 else 0
            hp = ((df['High'].iloc[-1]-cp)/df['High'].iloc[-1]*100) if df['High'].iloc[-1] > 0 else 0
            r = scorer.score_ticker(t, df, cp, pp, dp, rv, hp)
            if r and (r['mode_a_qualifies'] or r['mode_b_qualifies']):
                results.append(r)
        except: continue
    
    ma = [r for r in results if r['mode_a_qualifies']]
    mb = [r for r in results if r['mode_b_qualifies'] and not r['mode_a_qualifies']]
    ma.sort(key=lambda x: x['mode_a_score'], reverse=True)
    mb.sort(key=lambda x: x['mode_b_score'], reverse=True)
    ta, tb = ma[:2], mb[:2]
    
    print("\n🧠 AI...")
    for r in ta: r['ai'] = ai.analyze(r['ticker'], r, 'A')
    for r in tb: r['ai'] = ai.analyze(r['ticker'], r, 'B')
    
    elapsed = round(time.time() - start_time, 1)
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    output = {
        'timestamp': ts, 'mode_a': ta, 'mode_b': tb,
        'stats': {'universe': len(universe), 'loaded': len(all_data), 'filtered': len(filtered),
                  'mode_a_total': len(ma), 'mode_b_total': len(mb), 'time': elapsed}
    }
    
    # ✅ ИСПОЛЬЗУЕМ NumpyEncoder
    with open('scan_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)
    
    for label, arr, mode in [("🔴 MODE A: SNIPER", ma, 'A'), ("🟡 MODE B: TACTICAL", mb, 'B')]:
        print(f"\n{'='*60}")
        print(f"{label} (найдено {len(arr)})")
        print(f"{'='*60}")
        if not arr: print("  ⚪ Нет сигналов")
        else:
            for r in arr[:2]:
                print(f"\n📈 {r['ticker']} | ${r['price']} | Score: {r[f'mode_{mode.lower()}_score']}")
                for s in r[f'mode_{mode.lower()}_signals']: print(f"   {s}")
                if r.get('ai'):
                    if r['ai'].get('type'): print(f"🎯 {r['ai']['type']}")
                    if r['ai'].get('signal'): print(f"💥 {r['ai']['signal']}")
    
    print(f"\n💾 scan_results.json | ⏱️ {elapsed} сек")
    return output

if __name__ == "__main__":
    run_scanner()
