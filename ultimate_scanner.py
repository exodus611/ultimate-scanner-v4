#!/usr/bin/env python3
"""
ULTIMATE SCANNER v7.3 — ALPACA EDITION (FINAL FIX)
Прямое чтение переменных БЕЗ функций-посредников
"""
import os
import io
import time
import json
import sys
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from openai import OpenAI
from typing import Dict, List, Optional
from alpaca.data import StockHistoricalDataClient, StockBarsRequest, TimeFrame

# ============================================================
# ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ: ПРЯМОЕ ЧТЕНИЕ БЕЗ ФУНКЦИЙ
# ============================================================

print("=" * 60)
print("🔍 ULTIMATE SCANNER v7.3 — ПРЯМОЕ ЧТЕНИЕ ПЕРЕМЕННЫХ")
print("=" * 60)

# Инициализируем пустыми строками
DEEPSEEK_KEY = ""
ALPACA_KEY = ""
ALPACA_SECRET = ""
FINNHUB_KEY = ""

# Читаем DEEPSEEK_API_KEY
try:
    raw_val = os.environ['DEEPSEEK_API_KEY']
    if raw_val and len(raw_val.strip()) > 10:
        DEEPSEEK_KEY = raw_val.strip()
        print(f"✅ DEEPSEEK_API_KEY: НАЙДЕН (длина: {len(DEEPSEEK_KEY)} символов)")
    else:
        print(f"❌ DEEPSEEK_API_KEY: значение слишком короткое или пустое (длина: {len(raw_val) if raw_val else 0})")
except KeyError:
    print("❌ DEEPSEEK_API_KEY: переменная отсутствует в окружении")
except Exception as e:
    print(f"❌ DEEPSEEK_API_KEY: ошибка чтения - {e}")

# Читаем ALPACA_API_KEY
try:
    raw_val = os.environ['ALPACA_API_KEY']
    if raw_val and len(raw_val.strip()) > 10:
        ALPACA_KEY = raw_val.strip()
        print(f"✅ ALPACA_API_KEY: НАЙДЕН (длина: {len(ALPACA_KEY)} символов, начало: {ALPACA_KEY[:8]}...)")
    else:
        print(f"❌ ALPACA_API_KEY: значение слишком короткое или пустое (длина: {len(raw_val) if raw_val else 0})")
        # Ищем альтернативные имена
        for alt in ['alpaca_api_key', 'ALPACA_key', 'ALPACA_KEY', 'alpaca_key']:
            if alt in os.environ:
                val = os.environ[alt]
                if val and len(val.strip()) > 10:
                    ALPACA_KEY = val.strip()
                    print(f"   ✅ Найден как '{alt}'! (начало: {ALPACA_KEY[:8]}...)")
                    break
except KeyError:
    print("❌ ALPACA_API_KEY: переменная отсутствует в окружении")
    # Ищем альтернативные имена
    for alt in ['alpaca_api_key', 'ALPACA_key', 'ALPACA_KEY', 'alpaca_key']:
        if alt in os.environ:
            val = os.environ[alt]
            if val and len(val.strip()) > 10:
                ALPACA_KEY = val.strip()
                print(f"   ✅ Найден как '{alt}'! (начало: {ALPACA_KEY[:8]}...)")
                break
except Exception as e:
    print(f"❌ ALPACA_API_KEY: ошибка чтения - {e}")

# Читаем ALPACA_SECRET_KEY
try:
    raw_val = os.environ['ALPACA_SECRET_KEY']
    if raw_val and len(raw_val.strip()) > 10:
        ALPACA_SECRET = raw_val.strip()
        print(f"✅ ALPACA_SECRET_KEY: НАЙДЕН (длина: {len(ALPACA_SECRET)} символов)")
    else:
        print(f"❌ ALPACA_SECRET_KEY: значение слишком короткое или пустое (длина: {len(raw_val) if raw_val else 0})")
        # Ищем альтернативные имена
        for alt in ['alpaca_secret_key', 'ALPACA_secret', 'ALPACA_SECRET', 'alpaca_secret']:
            if alt in os.environ:
                val = os.environ[alt]
                if val and len(val.strip()) > 10:
                    ALPACA_SECRET = val.strip()
                    print(f"   ✅ Найден как '{alt}'!")
                    break
except KeyError:
    print("❌ ALPACA_SECRET_KEY: переменная отсутствует в окружении")
    # Ищем альтернативные имена
    for alt in ['alpaca_secret_key', 'ALPACA_secret', 'ALPACA_SECRET', 'alpaca_secret']:
        if alt in os.environ:
            val = os.environ[alt]
            if val and len(val.strip()) > 10:
                ALPACA_SECRET = val.strip()
                print(f"   ✅ Найден как '{alt}'!")
                break
except Exception as e:
    print(f"❌ ALPACA_SECRET_KEY: ошибка чтения - {e}")

# Читаем FINNHUB_API_KEY
try:
    raw_val = os.environ['FINNHUB_API_KEY']
    if raw_val and len(raw_val.strip()) > 10:
        FINNHUB_KEY = raw_val.strip()
        print(f"✅ FINNHUB_API_KEY: НАЙДЕН (длина: {len(FINNHUB_KEY)} символов)")
    else:
        print(f"❌ FINNHUB_API_KEY: значение слишком короткое или пустое (длина: {len(raw_val) if raw_val else 0})")
except KeyError:
    print("❌ FINNHUB_API_KEY: переменная отсутствует в окружении")
except Exception as e:
    print(f"❌ FINNHUB_API_KEY: ошибка чтения - {e}")

# ДИАГНОСТИКА: выводим все переменные, содержащие KEY или SECRET
print(f"\n📋 ДИАГНОСТИКА: Все переменные с KEY/SECRET/ALPACA в имени:")
found_any = False
for k in sorted(os.environ.keys()):
    if any(x in k.upper() for x in ['ALPACA', 'API', 'SECRET', 'KEY', 'DEEPSEEK', 'FINNHUB']):
        v = os.environ[k]
        found_any = True
        if v:
            print(f"   • {k} = {v[:20]}... (длина: {len(v)})")
        else:
            print(f"   • {k} = ПУСТО")
if not found_any:
    print("   ❌ НЕ НАЙДЕНО НИ ОДНОЙ СВЯЗАННОЙ ПЕРЕМЕННОЙ!")
    print("   📌 Проверьте Railway Variables:")
    print("      - ALPACA_API_KEY")
    print("      - ALPACA_SECRET_KEY")
    print("      - DEEPSEEK_API_KEY")

print(f"\n📊 ИТОГОВЫЙ СТАТУС:")
print(f"  DEEPSEEK_API_KEY: {'✅ ГОТОВ' if DEEPSEEK_KEY else '❌ ОТСУТСТВУЕТ'}")
print(f"  ALPACA_API_KEY: {'✅ ГОТОВ' if ALPACA_KEY else '❌ ОТСУТСТВУЕТ'}")
print(f"  ALPACA_SECRET_KEY: {'✅ ГОТОВ' if ALPACA_SECRET else '❌ ОТСУТСТВУЕТ'}")
print(f"  FINNHUB_API_KEY: {'✅ ГОТОВ' if FINNHUB_KEY else '❌ ОТСУТСТВУЕТ'}")
print("=" * 60)

# СРАЗУ ПРОВЕРЯЕМ И ВЫВОДИМ ПРЕДУПРЕЖДЕНИЕ
if not ALPACA_KEY or not ALPACA_SECRET:
    print("\n" + "!" * 60)
    print("⚠️  ВНИМАНИЕ: Ключи Alpaca не загружены!")
    print("!" * 60)
    print("Сканер запустится, но НЕ сможет загрузить данные через Alpaca.")
    print("Проверьте переменные в Railway и нажмите Redeploy.")
    print("!" * 60 + "\n")

CONFIG = {
    'DEEPSEEK_API_KEY': DEEPSEEK_KEY,
    'FINNHUB_API_KEY': FINNHUB_KEY,
    'ALPACA_API_KEY': ALPACA_KEY,
    'ALPACA_SECRET_KEY': ALPACA_SECRET,
    'MODE_A': {'name': 'SNIPER', 'position_size': 2000, 'target_pct': 0.40, 'stop_pct': 0.05, 'min_score': 75, 'hold_days': '3-7', 'top_n': 2},
    'MODE_B': {'name': 'TACTICAL', 'position_size': 1000, 'target_pct': 0.20, 'stop_pct': 0.05, 'min_score': 55, 'hold_days': '1-3', 'top_n': 2},
    'MIN_PRICE': 3.0, 'MIN_VOLUME': 200_000,
    'BANNED_SECTORS': {'Healthcare'},
    'BANNED_INDUSTRIES': {'Biotechnology', 'Drug Manufacturers—General', 'Drug Manufacturers—Specialty & Generic', 'Medical Instruments & Supplies', 'Medical Devices', 'Diagnostics & Research', 'Health Information Services', 'Pharmaceutical Retailers'}
}

def get_alpaca_client():
    """Создание клиента Alpaca с проверкой ключей"""
    # Используем глобальные переменные НАПРЯМУЮ
    ak = ALPACA_KEY
    sk = ALPACA_SECRET
    
    if not ak or not sk:
        error_msg = f"""
{'='*60}
❌ КРИТИЧЕСКАЯ ОШИБКА: Ключи Alpaca не найдены!
{'='*60}

📋 ДИАГНОСТИКА:
  ALPACA_API_KEY: {'✅' if ak else '❌'} (длина: {len(ak) if ak else 0})
  ALPACA_SECRET_KEY: {'✅' if sk else '❌'} (длина: {len(sk) if sk else 0})

🔧 ЧТО ДЕЛАТЬ:
  1. Перейдите в Railway → проект → Variables
  2. Убедитесь, что есть ТОЧНО такие переменные:
     • ALPACA_API_KEY
     • ALPACA_SECRET_KEY
  3. Проверьте, что значения не пустые
  4. Нажмите Redeploy

💡 ПОДСКАЗКА:
  API Key начинается с "PK..."
  Secret Key — длинная строка
{'='*60}
"""
        print(error_msg)
        raise ValueError("Alpaca keys not configured")
    
    print(f"✅ Создаю клиент Alpaca (API Key: {ak[:8]}...)")
    return StockHistoricalDataClient(ak, sk)

def load_data_via_alpaca(tickers, days=180):
    """Загрузка OHLCV через Alpaca. Возвращает dict {ticker: DataFrame}"""
    try:
        client = get_alpaca_client()
    except ValueError:
        print("❌ Пропускаем загрузку через Alpaca — нет ключей")
        return {}
    
    end = datetime.now()
    start = end - timedelta(days=days)
    all_data = {}
    batch_size = 100
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    
    print(f"  📡 Alpaca: {len(tickers)} тикеров, {total_batches} батчей...")
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        bn = i // batch_size + 1
        
        try:
            request = StockBarsRequest(
                symbol_or_symbols=batch,
                timeframe=TimeFrame.Day,
                start=start,
                end=end,
                limit=5000
            )
            bars = client.get_stock_bars(request)
            
            for symbol in batch:
                if symbol in bars and bars[symbol]:
                    data = []
                    for bar in bars[symbol]:
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
        except Exception as e:
            print(f"    ⚠️ Batch {bn} error: {e}")
    
    return all_data

class DeepSeekAnalyzer:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY не найден! Добавь в Railway Variables.")
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    def analyze(self, ticker: str, data: Dict, mode: str) -> Dict:
        mc = CONFIG[f'MODE_{mode}']
        prompt = (
            f"Senior Quant Analyst. Analyze {ticker} for {mc['name']} mode.\n\n"
            f"DATA: Price ${data.get('price','N/A')} | Position {data.get('position_pct','N/A')}% | Discount {data.get('discount_pct','N/A')}% | RVOL {data.get('rvol','N/A')}x | Options unusual {data.get('unusual_calls',0)} | Insider {data.get('insider_buys',0)} (${data.get('insider_value',0)/1000:.0f}k) | Short {data.get('short_pct','N/A')}% | DarkPool {data.get('dp_ratio','N/A')}% | Congress {data.get('congress_buys',0)} | Earnings {data.get('earnings_surprise','N/A')}% | News {data.get('news_sentiment','N/A')}\n\n"
            f"MODE: ${mc['position_size']} | Target +{mc['target_pct']*100:.0f}% | Stop -{mc['stop_pct']*100:.0f}%\n\n"
            f"TASK (3 blocks, Russian):\n### 🎯 ТИП СДЕЛКИ:\n[MODE {mode}] | [Тип]\n### 🧠 ФИЗИКА:\n- Что движет\n- Почему сейчас\n- R/R\n### 💥 СИГНАЛ:\n[Сила] | [Действие] | [Стоп $X] | [Цель $X]\n\nBe CONCISE (2-3 sentences per block)."
        )
        try:
            r = self.client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":"Senior Quant Analyst. Отвечай на русском, кратко."},{"role":"user","content":prompt}], max_tokens=600, temperature=0.3)
            return self._parse(r.choices[0].message.content)
        except Exception as e:
            return {'full': f"AI Error: {e}", 'type': '', 'physics': '', 'signal': ''}
    
    def _parse(self, text: str) -> Dict:
        blocks = {'full': text, 'type': '', 'physics': '', 'signal': ''}
        for s in text.split('###'):
            s = s.strip()
            if not s: continue
            low = s.lower()
            if 'тип' in low or 'type' in low: blocks['type'] = s.split('\n', 1)[-1].strip()
            elif 'физика' in low or 'physics' in low: blocks['physics'] = s.split('\n', 1)[-1].strip()
            elif 'сигнал' in low or 'signal' in low: blocks['signal'] = s.split('\n', 1)[-1].strip()
        return blocks

class DataSources:
    def __init__(self, config): self.config = config
    
    def get_options_anomaly(self, ticker: str) -> Dict:
        try:
            stock = yf.Ticker(ticker)
            exps = stock.options
            if not exps: return {'score': 0, 'unusual_calls': 0, 'max_vol_oi': 0}
            uc, mv = 0, 0
            for ex in exps[:3]:
                try:
                    ch = stock.option_chain(ex).calls
                    ch = ch[ch['volume'] > 50]
                    for _, o in ch.iterrows():
                        v, oi = o['volume'], o['openInterest']
                        if oi > 0:
                            r = v / oi
                            if r > 3.0: uc += 1; mv = max(mv, r)
                except: continue
            sc = 40 if uc > 10 else 30 if uc > 5 else 15 if uc > 2 else 0
            return {'score': sc, 'unusual_calls': uc, 'max_vol_oi': round(mv, 2)}
        except: return {'score': 0, 'unusual_calls': 0, 'max_vol_oi': 0}
    
    def get_insider_activity(self, ticker: str, days: int = 7) -> Dict:
        try:
            url = "http://openinsider.com/screener"
            params = {'t': ticker, 'td': days, 'xc': '1', 'sort': 'value', 'order': 'desc'}
            r = requests.get(url, params=params, timeout=10)
            tables = pd.read_html(r.content)
            if tables:
                df = tables[-1]
                buys = df[df['Value ($)'] > 50000]
                if not buys.empty:
                    tv = buys['Value ($)'].sum()
                    return {'count': len(buys), 'total_value': tv, 'score': 30 if tv > 500000 else 20 if tv > 100000 else 10}
        except: pass
        return {'count': 0, 'total_value': 0, 'score': 0}
    
    def get_finnhub_data(self, ticker: str) -> Dict:
        ak = self.config.get('FINNHUB_API_KEY')
        if not ak: return {'news_sentiment': 'N/A', 'news_count': 0, 'earnings_surprise': None}
        try:
            url = "https://finnhub.io/api/v1/company-news"
            params = {'symbol': ticker, 'from': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'), 'to': datetime.now().strftime('%Y-%m-%d'), 'token': ak}
            r = requests.get(url, params=params, timeout=5)
            news = r.json() if r.status_code == 200 else []
            bkw = ['beat','surge','upgrade','growth','partnership','contract','buy']
            bkw2 = ['miss','cut','downgrade','loss','lawsuit','investigation']
            bl = sum(1 for n in news for k in bkw if k in n.get('headline','').lower())
            br = sum(1 for n in news for k in bkw2 if k in n.get('headline','').lower())
            sent = 'BULLISH' if bl > br else 'BEARISH' if br > bl else 'NEUTRAL'
            es = None
            try:
                ea = yf.Ticker(ticker).quarterly_earnings
                if not ea.empty:
                    l = ea.iloc[0]; a = l.get('Actual',0); e = l.get('Estimate',0)
                    if e and e != 0: es = round(((a-e)/abs(e))*100, 2)
            except: pass
            return {'news_count': len(news), 'news_sentiment': sent, 'earnings_surprise': es}
        except: return {'news_sentiment': 'N/A', 'news_count': 0, 'earnings_surprise': None}
    
    def get_short_data(self, ticker: str) -> Dict:
        try:
            info = yf.Ticker(ticker).info
            sp = info.get('shortPercentOfFloat', 0) * 100
            dc = info.get('shortRatio', 0)
            sc = 25 if sp > 20 else 15 if sp > 15 else 5 if sp > 10 else 0
            return {'short_pct': round(sp, 2), 'days_to_cover': round(dc, 2), 'score': sc}
        except: return {'short_pct': 0, 'days_to_cover': 0, 'score': 0}
    
    def get_dark_pool_data(self, ticker: str, days: int = 10) -> Dict:
        base = "https://cdn.finra.org/equity/regsho/daily/REG%20SHO_{}.csv"
        dp = []; cd = datetime.now(); dc = 0; cb = 0
        while dc < days and cb < 30:
            dt = cd - timedelta(days=cb); cb += 1
            if dt.weekday() >= 5: continue
            ds = dt.strftime('%Y%m%d')
            try:
                r = requests.get(base.format(ds), timeout=10)
                if r.status_code == 200:
                    df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))
                    td = df[df['Symbol'] == ticker]
                    if not td.empty:
                        sv = float(td.iloc[0]['ShortVolume']); tv = float(td.iloc[0]['TotalVolume'])
                        if tv > 0: dp.append({'date': ds, 'dp_ratio': (sv/tv)*100}); dc += 1
                time.sleep(0.2)
            except: cb += 1
        if not dp: return {'dp_ratio': 0, 'trend_5d': 0, 'score': 0}
        df = pd.DataFrame(dp).sort_values('date')
        r5 = df['dp_ratio'].tail(5).mean()
        p5 = df['dp_ratio'].head(5).mean() if len(df) >= 10 else df['dp_ratio'].mean()
        tr = r5 - p5
        sc = 25 if r5 > 50 and tr > 5 else 20 if r5 > 45 and tr > 3 else 10 if r5 > 40 else 0
        return {'dp_ratio': round(df['dp_ratio'].iloc[-1], 1), 'trend_5d': round(tr, 2), 'score': sc}
    
    def get_congress_trading(self, ticker: str, days: int = 30) -> Dict:
        sb = 0; hb = 0; cu = datetime.now() - timedelta(days=days)
        try:
            r = requests.get("https://senatestockwatcher.com/api/data/all", timeout=10)
            if r.status_code == 200:
                for x in r.json():
                    if x.get('ticker') == ticker:
                        try:
                            td = datetime.strptime(x.get('transaction_date',''), '%Y-%m-%d')
                            if td >= cu and x.get('type','').lower() == 'purchase': sb += 1
                        except: pass
        except: pass
        try:
            r = requests.get("https://housestockwatcher.com/api/data/all", timeout=10)
            if r.status_code == 200:
                for x in r.json():
                    if x.get('ticker') == ticker:
                        try:
                            td = datetime.strptime(x.get('transaction_date',''), '%Y-%m-%d')
                            if td >= cu and x.get('type','').lower() == 'purchase': hb += 1
                        except: pass
        except: pass
        tb = sb + hb
        sc = 25 if tb >= 3 else 20 if tb >= 2 else 15 if tb >= 1 else 0
        return {'senate_buys': sb, 'house_buys': hb, 'total_buys': tb, 'score': sc}

class SignalScorer:
    def __init__(self, ds): self.ds = ds
    
    def is_biopharma(self, ticker: str) -> bool:
        try:
            i = yf.Ticker(ticker).info
            return i.get('sector','') in CONFIG['BANNED_SECTORS'] or i.get('industry','') in CONFIG['BANNED_INDUSTRIES']
        except: return False
    
    def score_ticker_with_data(self, ticker, df, cp, pp, dp, rv, hp):
        o = self.ds.get_options_anomaly(ticker)
        i = self.ds.get_insider_activity(ticker)
        f = self.ds.get_finnhub_data(ticker)
        s = self.ds.get_short_data(ticker)
        dk = self.ds.get_dark_pool_data(ticker)
        c = self.ds.get_congress_trading(ticker)
        a_s, a_sig = 0, []
        if o['score'] >= 30: a_s += o['score']; a_sig.append(f"⚡ Options: {o['unusual_calls']} unusual (Vol/OI: {o['max_vol_oi']}x)")
        if i['score'] >= 20: a_s += i['score']; a_sig.append(f"💼 Insider: {i['count']} buys (${i['total_value']/1000:.0f}k)")
        if dk['score'] >= 15: a_s += dk['score']; a_sig.append(f"🌑 Dark Pool: {dk['dp_ratio']}% (trend: {dk['trend_5d']:+.1f}%)")
        if c['score'] >= 15: a_s += c['score']; a_sig.append(f"🏛️ Congress: {c['total_buys']} buys")
        b_s, b_sig = 0, []
        if rv > 2.5: b_s += 25; b_sig.append(f"📈 RVOL: {rv:.1f}x")
        elif rv > 2.0: b_s += 15; b_sig.append(f"📈 RVOL: {rv:.1f}x")
        if f['earnings_surprise'] and f['earnings_surprise'] > 10: b_s += 25; b_sig.append(f"💰 Earnings Beat: +{f['earnings_surprise']:.1f}%")
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
            'short_pct': s['short_pct'], 'dp_ratio': dk['dp_ratio'], 'congress_buys': c['total_buys'],
            'earnings_surprise': f['earnings_surprise'], 'news_sentiment': f['news_sentiment']
        }

class UltimateScanner:
    def __init__(self):
        self.ds = DataSources(CONFIG)
        self.scorer = SignalScorer(self.ds)
        self.ai = DeepSeekAnalyzer(CONFIG['DEEPSEEK_API_KEY'])
        self.universe = self._load_universe()
    
    def _load_universe(self) -> List[str]:
        cache = 'universe_cache.csv'
        if os.path.exists(cache) and (time.time() - os.path.getmtime(cache)) < 604800:
            t = pd.read_csv(cache)['Symbol'].tolist()
            print(f"✅ From cache: {len(t)} tickers"); return t
        print("🔄 Loading universe...")
        at = []
        h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        for ex in ['NASDAQ', 'NYSE', 'AMEX']:
            try:
                url = f"https://api.nasdaq.com/api/screener/stocks?tableType=traded&exchange={ex}&limit=10000"
                r = requests.get(url, headers=h, timeout=30)
                if r.status_code == 200:
                    rows = r.json().get('data', {}).get('rows', [])
                    t = [x['symbol'] for x in rows if x.get('symbol')]
                    at.extend(t); print(f"  ✅ {ex}: {len(t)}")
            except Exception as e: print(f"  ⚠️ {ex}: {e}")
        if len(at) < 100:
            print("⚠️ Using built-in list...")
            bi = ['AAPL','MSFT','GOOGL','AMZN','NVDA','META','TSLA','AMD','INTC','PYPL','SQ','COIN','MARA','RIOT','PLTR','SOFI','UPST','RIVN','LCID','NIO','XPEV','SNAP','PINS','UBER','LYFT','ABNB','DASH','ROKU','ZM','NFLX','QCOM','AVGO','TXN','AMAT','LRCX','KLAC','ASML','ARM','SMCI','DELL','PANW','CRWD','ZS','FTNT','NOW','ADBE','CRM','ORCL','CSCO','SOUN','OKLO','SMR','BBAI','AI','SHOP','SE','BABA','JD','PDD','BIDU','TSM','BILI','IQ','TCOM','VIPS','W','ETSY','AFRM','HOOD','RBLX','U','SNOW','DDOG','NET','MDB','OKTA','WDAY','TEAM','HUBS','TTD','SPOT','SE','CPNG']
            at.extend(bi); print(f"  ✅ Built-in: {len(bi)}")
        at = list(set(at))
        pd.DataFrame({'Symbol': at}).to_csv(cache, index=False)
        print(f"✅ TOTAL: {len(at)} tickers"); return at
    
    def run(self) -> Dict:
        start = time.time()
        print("="*70)
        print("🎯 ULTIMATE SCANNER v7.3 — ALPACA EDITION (FINAL FIX)")
        print("="*70)
        print(f"📊 Universe: {len(self.universe)} tickers")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n📥 STAGE 1: Loading via Alpaca Markets...")
        try:
            all_data = load_data_via_alpaca(self.universe, days=180)
        except Exception as e:
            print(f"❌ Alpaca error: {e}")
            all_data = {}
        
        print(f"\n✅ Loaded: {len(all_data)} tickers via Alpaca")
        
        print("\n🔍 STAGE 2: Filtering...")
        filtered = []
        for t, df in all_data.items():
            try:
                cp = df['Close'].iloc[-1]; av = df['Volume'].tail(20).mean()
                if cp < CONFIG['MIN_PRICE'] or av < CONFIG['MIN_VOLUME']: continue
                h6 = df['High'].max(); l6 = df['Low'].min()
                pp = ((cp-l6)/(h6-l6)*100) if h6 > l6 else 50
                dp = ((cp-h6)/h6*100)
                if not (pp < 70 and dp < -25) and not (50 <= pp <= 85): continue
                filtered.append(t)
            except: continue
        print(f"✅ After filtering: {len(filtered)} tickers")
        
        print(f"\n🔍 STAGE 3: Scoring {len(filtered)} tickers...")
        results = []
        for i, t in enumerate(filtered, 1):
            if i % 20 == 0: print(f"  Progress: {i}/{len(filtered)}...", flush=True)
            df = all_data[t]
            if self.scorer.is_biopharma(t): continue
            try:
                cp = df['Close'].iloc[-1]; av = df['Volume'].tail(20).mean()
                h6 = df['High'].max(); l6 = df['Low'].min()
                pp = ((cp-l6)/(h6-l6)*100) if h6 > l6 else 50
                dp = ((cp-h6)/h6*100)
                rv = df['Volume'].iloc[-1] / av if av > 0 else 0
                td = df.iloc[-1]
                hp = ((td['High']-td['Close'])/td['High']*100) if td['High'] > 0 else 0
                r = self.scorer.score_ticker_with_data(t, df, cp, pp, dp, rv, hp)
                if r and (r['mode_a_qualifies'] or r['mode_b_qualifies']):
                    m = 'A' if r['mode_a_qualifies'] else 'B'
                    sc = r[f'mode_{m.lower()}_score']
                    print(f"    ✅ {t} — MODE {m} (score: {sc})")
                    results.append(r)
            except: continue
        
        ma = [r for r in results if r['mode_a_qualifies']]
        mb = [r for r in results if r['mode_b_qualifies'] and not r['mode_a_qualifies']]
        ma.sort(key=lambda x: x['mode_a_score'], reverse=True)
        mb.sort(key=lambda x: x['mode_b_score'], reverse=True)
        ta = ma[:CONFIG['MODE_A']['top_n']]; tb = mb[:CONFIG['MODE_B']['top_n']]
        print(f"\n🎯 MODE A (SNIPER): {len(ma)} found, top-{len(ta)}")
        print(f"⚡ MODE B (TACTICAL): {len(mb)} found, top-{len(tb)}")
        
        print("\n🧠 STAGE 4: DeepSeek AI...")
        for r in ta: print(f"  🔴 [A] {r['ticker']}..."); r['ai'] = self.ai.analyze(r['ticker'], r, 'A')
        for r in tb: print(f"  🟡 [B] {r['ticker']}..."); r['ai'] = self.ai.analyze(r['ticker'], r, 'B')
        
        ts = datetime.now().strftime('%Y%m%d_%H%M')
        output = {
            'timestamp': ts, 'mode_a': ta, 'mode_b': tb,
            'stats': {'universe_size': len(self.universe), 'loaded': len(all_data), 'filtered': len(filtered), 'mode_a_total': len(ma), 'mode_b_total': len(mb), 'scan_time_sec': round(time.time() - start, 1)}
        }
        with open('scan_results.json', 'w', encoding='utf-8') as f: json.dump(output, f, ensure_ascii=False, indent=2)
        with open(f'scan_{ts}.json', 'w', encoding='utf-8') as f: json.dump(output, f, ensure_ascii=False, indent=2)
        
        print("\n" + "="*70)
        print("🔴 MODE A: SNIPER (2 tickers, +40%, $2000)")
        print("="*70)
        if not ma: print("  ⚪ No signals today")
        else:
            for r in ma:
                print(f"\n{'─'*70}")
                print(f"📈 {r['ticker']} | ${r['price']} | Score: {r['mode_a_score']}")
                print(f"   Position: {r['position_pct']}% | Discount: {r['discount_pct']}% | RVOL: {r['rvol']}x")
                for s in r['mode_a_signals'][:5]: print(f"   {s}")
                print(f"{'─'*70}")
                if r.get('ai'):
                    if r['ai']['type']: print(f"🎯 {r['ai']['type']}")
                    if r['ai']['physics']: print(f"🧠 {r['ai']['physics']}")
                    if r['ai']['signal']: print(f"💥 {r['ai']['signal']}")
        
        print("\n" + "="*70)
        print("🟡 MODE B: TACTICAL (2 tickers, +20%, $1000)")
        print("="*70)
        if not mb: print("  ⚪ No signals today")
        else:
            for r in mb:
                print(f"\n{'─'*70}")
                print(f"📈 {r['ticker']} | ${r['price']} | Score: {r['mode_b_score']}")
                print(f"   Position: {r['position_pct']}% | Discount: {r['discount_pct']}% | RVOL: {r['rvol']}x")
                for s in r['mode_b_signals'][:5]: print(f"   {s}")
                print(f"{'─'*70}")
                if r.get('ai'):
                    if r['ai']['type']: print(f"🎯 {r['ai']['type']}")
                    if r['ai']['physics']: print(f"🧠 {r['ai']['physics']}")
                    if r['ai']['signal']: print(f"💥 {r['ai']['signal']}")
        
        print(f"\n💾 Saved: scan_results.json")
        print(f"⏱️  Time: {time.time() - start:.1f} sec")
        return output

if __name__ == "__main__":
    # ПРОВЕРКА КЛЮЧЕЙ ПЕРЕД ЗАПУСКОМ
    if not DEEPSEEK_KEY:
        print("❌ ОШИБКА: DEEPSEEK_API_KEY не найден!")
        print("   Добавь в Railway Variables: DEEPSEEK_API_KEY")
        exit(1)
    
    if not ALPACA_KEY or not ALPACA_SECRET:
        print("❌ ОШИБКА: Ключи Alpaca не найдены!")
        print("\n📋 ПРОВЕРЬ СЛЕДУЮЩЕЕ:")
        print("1. Зайди в Railway → твой проект → Variables")
        print("2. Убедись что добавлены ДВЕ переменные (ТОЧНО ТАК):")
        print("   • ALPACA_API_KEY (значение начинается с PK...)")
        print("   • ALPACA_SECRET_KEY (длинная строка)")
        print("3. Нажми Redeploy после добавления")
        print(f"\nТекущие значения:")
        print(f"  ALPACA_API_KEY: {ALPACA_KEY[:15] + '...' if ALPACA_KEY else 'ПУСТО'}")
        print(f"  ALPACA_SECRET_KEY: {ALPACA_SECRET[:15] + '...' if ALPACA_SECRET else 'ПУСТО'}")
        exit(1)
    
    print("✅ Все ключи найдены! Запуск сканера...")
    UltimateScanner().run()
