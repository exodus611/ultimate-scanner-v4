#!/usr/bin/env python3
"""
ULTIMATE SCANNER v7.14 — СТАБИЛЬНАЯ ВЕРСИЯ
"""
import os, time, json
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

print("=" * 60)
print("ULTIMATE SCANNER v7.14")
print("=" * 60)

# ========== КОНФИГУРАЦИЯ ==========
CONFIG = {
    'MODE_A': {'name': 'SNIPER', 'min_score': 75, 'top_n': 2},
    'MODE_B': {'name': 'TACTICAL', 'min_score': 55, 'top_n': 2},
    'MIN_PRICE': 3.0,
    'MIN_VOLUME': 200_000,
}

# ========== ЗАГРУЗКА ДАННЫХ ==========
def load_data(tickers, days=60):
    """Загрузка через Yahoo Finance чанками по 50"""
    print(f"📡 Загрузка {len(tickers)} тикеров...")
    end = datetime.now()
    start = end - timedelta(days=days)
    all_data = {}
    chunk_size = 50
    
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i+chunk_size]
        cn = i // chunk_size + 1
        
        try:
            df = yf.download(chunk, start=start, end=end, progress=False, group_by='ticker', threads=True)
            
            for t in chunk:
                try:
                    if len(chunk) == 1:
                        td = df
                    else:
                        td = df[t]
                    
                    if not td.empty and len(td) >= 30:
                        td = td.reset_index()
                        all_data[t] = td
                except:
                    pass
            
            if cn % 10 == 0:
                print(f"  {cn}/{(len(tickers)+chunk_size-1)//chunk_size} чанков, загружено {len(all_data)} тикеров")
        except Exception as e:
            print(f"  ⚠️ Ошибка чанка {cn}: {e}")
            time.sleep(2)
    
    print(f"✅ Загружено: {len(all_data)} тикеров")
    return all_data

# ========== ФИЛЬТР ==========
def find_springs(data):
    """Поиск "пружин" — акции в нижней части диапазона с повышенным объёмом"""
    signals = []
    
    for t, df in data.items():
        try:
            close = df['Close'].iloc[-1]
            volume = df['Volume'].iloc[-1]
            avg_volume = df['Volume'].tail(20).mean()
            
            # Базовые фильтры
            if close < CONFIG['MIN_PRICE'] or avg_volume < CONFIG['MIN_VOLUME']:
                continue
            
            # Позиция в 60-дневном диапазоне
            high_60 = df['High'].tail(60).max()
            low_60 = df['Low'].tail(60).min()
            
            if high_60 <= low_60:
                continue
            
            position = (close - low_60) / (high_60 - low_60) * 100
            discount = (close - high_60) / high_60 * 100
            
            # Объём относительно среднего
            rvol = volume / avg_volume if avg_volume > 0 else 0
            
            # HOD Pinch (закрытие близко к максимуму дня)
            high_day = df['High'].iloc[-1]
            pinch = (high_day - close) / high_day * 100 if high_day > 0 else 0
            
            # === MODE A: SNIPER (инсайдерские сигналы) ===
            # Ищем: позиция 20-50%, RVOL > 2, закрытие у хая дня
            mode_a_score = 0
            mode_a_signals = []
            
            if 20 <= position <= 50:
                mode_a_score += 30
                mode_a_signals.append(f"📍 Позиция {position:.0f}% (нижняя половина)")
            
            if rvol > 2.0:
                mode_a_score += 25
                mode_a_signals.append(f"📈 RVOL: {rvol:.1f}x")
            
            if pinch < 2:
                mode_a_score += 15
                mode_a_signals.append(f"🎯 HOD Pinch: {pinch:.1f}%")
            
            if discount < -10:
                mode_a_score += 20
                mode_a_signals.append(f"📉 Дисконт: {discount:.1f}%")
            
            # === MODE B: TACTICAL (трендовые) ===
            mode_b_score = 0
            mode_b_signals = []
            
            if 50 <= position <= 85:
                mode_b_score += 30
                mode_b_signals.append(f"📍 Позиция {position:.0f}% (верхняя половина)")
            
            if rvol > 1.5:
                mode_b_score += 25
                mode_b_signals.append(f"📈 RVOL: {rvol:.1f}x")
            
            if pinch < 3:
                mode_b_score += 15
                mode_b_signals.append(f"🎯 HOD Pinch: {pinch:.1f}%")
            
            if mode_a_score >= CONFIG['MODE_A']['min_score'] or mode_b_score >= CONFIG['MODE_B']['min_score']:
                signals.append({
                    'ticker': t,
                    'price': round(close, 2),
                    'position_pct': round(position, 1),
                    'discount_pct': round(discount, 1),
                    'rvol': round(rvol, 2),
                    'hod_pinch': round(pinch, 1),
                    'mode_a_score': mode_a_score,
                    'mode_a_signals': mode_a_signals,
                    'mode_a_qualifies': mode_a_score >= CONFIG['MODE_A']['min_score'],
                    'mode_b_score': mode_b_score,
                    'mode_b_signals': mode_b_signals,
                    'mode_b_qualifies': mode_b_score >= CONFIG['MODE_B']['min_score'],
                })
        except:
            continue
    
    return signals

# ========== ВСЕЛЕННАЯ ==========
def load_universe():
    """Загрузка списка тикеров (S&P 500 + Nasdaq-100 + популярные)"""
    cache_file = 'universe_cache.csv'
    
    if os.path.exists(cache_file) and (time.time() - os.path.getmtime(cache_file)) < 86400:
        tickers = pd.read_csv(cache_file)['Symbol'].tolist()
        print(f"✅ Вселенная из кеша: {len(tickers)} тикеров")
        return tickers
    
    print("🔄 Загрузка вселенной...")
    tickers = []
    
    # S&P 500 через Wikipedia
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        tickers.extend(sp500['Symbol'].tolist())
        print(f"  S&P 500: {len(sp500)} тикеров")
    except:
        pass
    
    # Nasdaq-100 через Wikipedia
    try:
        nasdaq = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]
        tickers.extend(nasdaq['Ticker'].tolist())
        print(f"  Nasdaq-100: {len(nasdaq)} тикеров")
    except:
        pass
    
    # Убираем дубликаты, точку в тикерах BRK.B и т.п.
    tickers = list(set([t.replace('.', '-') for t in tickers if isinstance(t, str)]))
    
    pd.DataFrame({'Symbol': tickers}).to_csv(cache_file, index=False)
    print(f"✅ Вселенная: {len(tickers)} тикеров")
    return tickers

# ========== ГЛАВНЫЙ ЦИКЛ ==========
def run_scanner():
    start_time = time.time()
    
    print("=" * 60)
    print("🎯 ULTIMATE SCANNER v7.14")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. Вселенная
    universe = load_universe()
    
    # 2. Данные
    data = load_data(universe, days=60)
    if not data:
        print("❌ Нет данных")
        return {"mode_a": [], "mode_b": [], "stats": {}}
    
    # 3. Сигналы
    print("\n🔍 Поиск сигналов...")
    signals = find_springs(data)
    
    ma = [s for s in signals if s['mode_a_qualifies']]
    mb = [s for s in signals if s['mode_b_qualifies'] and not s['mode_a_qualifies']]
    
    ma.sort(key=lambda x: x['mode_a_score'], reverse=True)
    mb.sort(key=lambda x: x['mode_b_score'], reverse=True)
    
    ta = ma[:CONFIG['MODE_A']['top_n']]
    tb = mb[:CONFIG['MODE_B']['top_n']]
    
    print(f"\n🎯 MODE A (SNIPER): найдено {len(ma)}, топ-{len(ta)}")
    print(f"⚡ MODE B (TACTICAL): найдено {len(mb)}, топ-{len(tb)}")
    
    # 4. Вывод
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    output = {
        'timestamp': ts,
        'mode_a': ta,
        'mode_b': tb,
        'stats': {
            'universe_size': len(universe),
            'loaded': len(data),
            'filtered': len(signals),
            'mode_a_total': len(ma),
            'mode_b_total': len(mb),
            'scan_time_sec': round(time.time() - start_time, 1)
        }
    }
    
    with open('scan_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("🔴 MODE A: SNIPER")
    print("=" * 60)
    if not ta:
        print("  ⚪ Нет сигналов")
    else:
        for s in ta:
            print(f"\n📈 {s['ticker']} | ${s['price']} | Score: {s['mode_a_score']}")
            for sig in s['mode_a_signals']:
                print(f"   {sig}")
    
    print("\n" + "=" * 60)
    print("🟡 MODE B: TACTICAL")
    print("=" * 60)
    if not tb:
        print("  ⚪ Нет сигналов")
    else:
        for s in tb:
            print(f"\n📈 {s['ticker']} | ${s['price']} | Score: {s['mode_b_score']}")
            for sig in s['mode_b_signals']:
                print(f"   {sig}")
    
    print(f"\n💾 scan_results.json | ⏱️ {time.time() - start_time:.1f} сек")
    return output

if __name__ == "__main__":
    run_scanner()
