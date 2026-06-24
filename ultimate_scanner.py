#!/usr/bin/env python3
"""
ULTIMATE SCANNER v7.13 — FIXED YFINANCE LOADING
"""
import os, io, time, json, sys, traceback, requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from openai import OpenAI
from typing import Dict, List
from alpaca.data import StockHistoricalDataClient, StockBarsRequest, TimeFrame

print("=" * 60)
print("ULTIMATE SCANNER v7.13")
print("=" * 60)

# Настройка yfinance
yf.set_tz_cache_location("cache/tz")
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

def get_env_final(var_name: str) -> str:
    candidates = []
    for k, v in os.environ.items():
        if k == var_name:
            candidates.append(v)
    for val in candidates:
        if val and val.strip() and len(val.strip()) > 10:
            return val.strip()
    return ""

DEEPSEEK_KEY = get_env_final('DEEPSEEK_API_KEY')
ALPACA_KEY = get_env_final('ALPACA_API_KEY')
ALPACA_SECRET = get_env_final('ALPACA_SECRET_KEY')
FINNHUB_KEY = get_env_final('FINNHUB_API_KEY')
USE_ALPACA = bool(ALPACA_KEY and ALPACA_SECRET)

print(f"Keys: DEEPSEEK {'✅' if DEEPSEEK_KEY else '❌'}, ALPACA {'✅' if USE_ALPACA else '❌'}")

CONFIG = {
    'DEEPSEEK_API_KEY': DEEPSEEK_KEY,
    'ALPACA_API_KEY': ALPACA_KEY,
    'ALPACA_SECRET_KEY': ALPACA_SECRET,
    'FINNHUB_API_KEY': FINNHUB_KEY,
    'MODE_A': {'name': 'SNIPER', 'position_size': 2000, 'target_pct': 0.40, 'stop_pct': 0.05, 'min_score': 75, 'top_n': 2},
    'MODE_B': {'name': 'TACTICAL', 'position_size': 1000, 'target_pct': 0.20, 'stop_pct': 0.05, 'min_score': 55, 'top_n': 2},
    'MIN_PRICE': 3.0, 'MIN_VOLUME': 200_000,
}

def load_data_yfinance(tickers, days=60):
    """Загрузка через Yahoo Finance небольшими порциями с повторными попытками"""
    print(f"  📡 Yahoo Finance: {len(tickers)} тикеров (чанками по 50)...")
    end = datetime.now()
    start = end - timedelta(days=days)
    all_data = {}
    chunk_size = 50
    total_chunks = (len(tickers) + chunk_size - 1) // chunk_size
    
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i+chunk_size]
        cn = i // chunk_size + 1
        
        if cn % 20 == 0:
            print(f"    Chunk {cn}/{total_chunks}, loaded {len(all_data)} tickers so far", flush=True)
        
        for attempt in range(3):  # 3 попытки
            try:
                df = yf.download(
                    chunk,
                    start=start,
                    end=end,
                    progress=False,
                    group_by='ticker',
                    threads=True,
                    timeout=30
                )
                
                if df.empty:
                    if attempt < 2:
                        time.sleep(2)
                        continue
                    break
                
                for t in chunk:
                    try:
                        if len(chunk) == 1:
                            ticker_df = df
                        else:
                            ticker_df = df[t]
                        
                        if not ticker_df.empty and len(ticker_df) >= 30:
                            ticker_df = ticker_df.reset_index()
                            # Приводим к нужному формату
                            cols = {
                                'Date': 'Date',
                                'Open': 'Open',
                                'High': 'High',
                                'Low': 'Low',
                                'Close': 'Close',
                                'Volume': 'Volume'
                            }
                            ticker_df = ticker_df.rename(columns={
                                c: cols.get(c, c) for c in ticker_df.columns
                            })
                            all_data[t] = ticker_df[['Date','Open','High','Low','Close','Volume']]
                    except:
                        continue
                break  # успешно — выходим из цикла попыток
                
            except Exception as e:
                if attempt < 2:
                    time.sleep(2)
                else:
                    if cn == 1:
                        print(f"    ⚠️ Yahoo error on first chunk: {e}")
    
    print(f"    ✅ Yahoo loaded: {len(all_data)} tickers")
    return all_data

class UltimateScanner:
    def __init__(self):
        self.ai = DeepSeekAnalyzer(CONFIG['DEEPSEEK_API_KEY']) if DEEPSEEK_KEY else None
        self.universe = self._load_universe()
    
    def _load_universe(self):
        # Загружаем только основные тикеры
        tickers = [
            'AAPL','MSFT','GOOGL','AMZN','NVDA','META','TSLA','AMD','INTC',
            'PYPL','SQ','COIN','PLTR','SOFI','UBER','LYFT','ABNB','DASH',
            'ROKU','ZM','NFLX','QCOM','AVGO','CRM','ADBE','ORCL','CSCO',
            'SNOW','DDOG','NET','MDB','CRWD','ZS','PANW','FTNT','NOW',
            'BA','CAT','GE','F','GM','TSLA','NIO','RIVN','LCID',
            'JPM','BAC','WFC','GS','MS','C','V','MA','AXP',
            'XOM','CVX','COP','EOG','PXD','SLB','OXY',
            'JNJ','PFE','MRK','ABT','TMO','DHR',
            'WMT','TGT','COST','HD','LOW','MCD','SBUX',
            'DIS','NKE','LULU','ULTA',
            'SPY','QQQ','IWM','DIA','TLT','GLD','SLV','USO',
        ]
        # Убираем дубликаты
        tickers = list(set(tickers))
        print(f"✅ Universe: {len(tickers)} tickers (S&P 500 + popular)")
        return tickers
    
    def run(self):
        start_time = time.time()
        print("=" * 60)
        print("🎯 ULTIMATE SCANNER v7.13")
        print("=" * 60)
        print(f"📊 Universe: {len(self.universe)} tickers")
        
        # Загрузка данных
        all_data = load_data_yfinance(self.universe, days=60)
        if not all_data:
            print("❌ Не удалось загрузить данные ни из одного источника.")
            return {"mode_a": [], "mode_b": [], "stats": {}}
        
        print(f"\n✅ Loaded: {len(all_data)} tickers")
        
        # Простейший фильтр
        print("\n🔍 Filtering...")
        signals = []
        for t, df in all_data.items():
            try:
                close = df['Close'].iloc[-1]
                volume = df['Volume'].tail(20).mean()
                if close < CONFIG['MIN_PRICE'] or volume < CONFIG['MIN_VOLUME']:
                    continue
                
                # Простой сигнал: цена в нижней половине 60-дневного диапазона + объём выше среднего
                high_60 = df['High'].max()
                low_60 = df['Low'].min()
                position = (close - low_60) / (high_60 - low_60) * 100 if high_60 > low_60 else 50
                rvol = df['Volume'].iloc[-1] / volume if volume > 0 else 0
                
                if 20 <= position <= 50 and rvol > 1.5:
                    signals.append({
                        'ticker': t,
                        'price': round(close, 2),
                        'position': round(position, 1),
                        'rvol': round(rvol, 2),
                    })
            except:
                continue
        
        print(f"✅ Found {len(signals)} potential signals")
        
        # Вывод результатов
        signals.sort(key=lambda x: x['rvol'], reverse=True)
        top_signals = signals[:10]
        
        output = {
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M'),
            'signals': top_signals,
            'stats': {
                'universe_size': len(self.universe),
                'loaded': len(all_data),
                'signals_found': len(signals),
                'scan_time_sec': round(time.time() - start_time, 1)
            }
        }
        
        with open('scan_results.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print("\n" + "=" * 60)
        print("🔴 TOP SIGNALS (пружины перед движением)")
        print("=" * 60)
        for s in top_signals[:5]:
            print(f"📈 {s['ticker']} | ${s['price']} | Pos: {s['position']}% | RVOL: {s['rvol']}x")
        
        print(f"\n💾 Saved: scan_results.json | ⏱️ {time.time() - start_time:.1f} sec")
        return output

if __name__ == "__main__":
    pass
