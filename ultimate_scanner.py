#!/usr/bin/env python3
"""
ULTIMATE SCANNER v4.0 — FULL UNIVERSE (5000+ тикеров)
MODE A (SNIPER): 2 тикера, +40%, позиция $2000
MODE B (TACTICAL): 2 тикера, +20%, позиция $1000
"""

import os
import io
import time
import json
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from openai import OpenAI
from typing import Dict, List, Optional


CONFIG = {
    'DEEPSEEK_API_KEY': os.getenv('DEEPSEEK_API_KEY', ''),
    'FINNHUB_API_KEY': os.getenv('FINNHUB_API_KEY', ''),
    'MODE_A': {
        'name': 'SNIPER',
        'position_size': 2000,
        'target_pct': 0.40,
        'stop_pct': 0.05,
        'min_score': 75,
        'hold_days': '3-7',
        'top_n': 2
    },
    'MODE_B': {
        'name': 'TACTICAL',
        'position_size': 1000,
        'target_pct': 0.20,
        'stop_pct': 0.05,
        'min_score': 55,
        'hold_days': '1-3',
        'top_n': 2
    },
    'MIN_PRICE': 3.0,
    'MIN_VOLUME': 200_000,
    'BANNED_SECTORS': {'Healthcare'},
    'BANNED_INDUSTRIES': {
        'Biotechnology',
        'Drug Manufacturers—General',
        'Drug Manufacturers—Specialty & Generic',
        'Medical Instruments & Supplies',
        'Medical Devices',
        'Diagnostics & Research',
        'Health Information Services',
        'Pharmaceutical Retailers'
    }
}


class DeepSeekAnalyzer:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    def analyze(self, ticker: str, data: Dict, mode: str) -> Dict:
        mode_config = CONFIG[f'MODE_{mode}']
        prompt = (
            f"Ты — Senior Quant Analyst хедж-фонда.\n"
            f"Проанализируй {ticker} для режима {mode_config['name']}.\n\n"
            f"## ДАННЫЕ:\n"
            f"- Цена: ${data.get('price', 'N/A')}\n"
            f"- Позиция в 6М диапазоне: {data.get('position_pct', 'N/A')}%\n"
            f"- Скидка от хая: {data.get('discount_pct', 'N/A')}%\n"
            f"- RVOL сегодня: {data.get('rvol', 'N/A')}x\n"
            f"- Options unusual calls: {data.get('unusual_calls', 0)}\n"
            f"- Insider buys (7д): {data.get('insider_buys', 0)} на ${data.get('insider_value', 0)/1000:.0f}k\n"
            f"- Short Interest: {data.get('short_pct', 'N/A')}%\n"
            f"- Dark Pool ratio: {data.get('dp_ratio', 'N/A')}%\n"
            f"- Congressional buys (30д): {data.get('congress_buys', 0)}\n"
            f"- Earnings surprise: {data.get('earnings_surprise', 'N/A')}%\n"
            f"- News sentiment: {data.get('news_sentiment', 'N/A')}\n\n"
            f"## РЕЖИМ {mode_config['name']}:\n"
            f"- Позиция: ${mode_config['position_size']}\n"
            f"- Цель: +{mode_config['target_pct']*100:.0f}%\n"
            f"- Стоп: -{mode_config['stop_pct']*100:.0f}%\n\n"
            f"## ЗАДАЧА (3 блока, кратко):\n\n"
            f"### 🎯 ТИП СДЕЛКИ:\n"
            f"[MODE {mode}] | [Тип: Options Front-Run / Insider Play / Post-Earnings / Momentum / Squeeze / Policy Play]\n\n"
            f"### 🧠 ФИЗИКА ДВИЖЕНИЯ:\n"
            f"- Что движет цену\n"
            f"- Почему именно сейчас\n"
            f"- Risk/Reward\n\n"
            f"### 💥 СИГНАЛ:\n"
            f"[Сила: Flawless/Strong/Moderate/Weak] | [Входить/Наблюдать/Пропустить] | [Стоп: $X] | [Цель: $X]\n\n"
            f"Будь КРАТКИМ (2-3 предложения на блок)."
        )
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Senior Quant Analyst. Отвечай на русском, кратко."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.3
            )
            text = response.choices[0].message.content
            return self._parse(text)
        except Exception as e:
            return {'full': f"Ошибка AI: {e}", 'type': '', 'physics': '', 'signal': ''}

    def _parse(self, text: str) -> Dict:
        blocks = {'full': text, 'type': '', 'physics': '', 'signal': ''}
        for s in text.split('###'):
            s = s.strip()
            if not s:
                continue
            low = s.lower()
            if 'тип' in low:
                blocks['type'] = s.split('\n', 1)[-1].strip()
            elif 'физика' in low:
                blocks['physics'] = s.split('\n', 1)[-1].strip()
            elif 'сигнал' in low:
                blocks['signal'] = s.split('\n', 1)[-1].strip()
        return blocks


class DataSources:
    def __init__(self, config):
        self.config = config

    def get_options_anomaly(self, ticker: str) -> Dict:
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options
            if not expirations:
                return {'score': 0, 'unusual_calls': 0, 'max_vol_oi': 0}
            unusual_calls = 0
            max_vol_oi = 0
            for expiry in expirations[:3]:
                try:
                    chain = stock.option_chain(expiry)
                    calls = chain.calls[chain.calls['volume'] > 50]
                    for _, opt in calls.iterrows():
                        vol = opt['volume']
                        oi = opt['openInterest']
                        if oi > 0:
                            ratio = vol / oi
                            if ratio > 3.0:
                                unusual_calls += 1
                                max_vol_oi = max(max_vol_oi, ratio)
                except:
                    continue
            score = 0
            if unusual_calls > 10: score += 40
            elif unusual_calls > 5: score += 30
            elif unusual_calls > 2: score += 15
            return {'score': score, 'unusual_calls': unusual_calls, 'max_vol_oi': round(max_vol_oi, 2)}
        except:
            return {'score': 0, 'unusual_calls': 0, 'max_vol_oi': 0}

    def get_insider_activity(self, ticker: str, days: int = 7) -> Dict:
        try:
            url = "http://openinsider.com/screener"
            params = {'t': ticker, 'td': days, 'xc': '1', 'sort': 'value', 'order': 'desc'}
            response = requests.get(url, params=params, timeout=10)
            tables = pd.read_html(response.content)
            if tables:
                df = tables[-1]
                buys = df[df['Value ($)'] > 50000]
                if not buys.empty:
                    total_value = buys['Value ($)'].sum()
                    return {
                        'count': len(buys),
                        'total_value': total_value,
                        'score': 30 if total_value > 500000 else 20 if total_value > 100000 else 10
                    }
        except:
            pass
        return {'count': 0, 'total_value': 0, 'score': 0}

    def get_finnhub_data(self, ticker: str) -> Dict:
        api_key = self.config.get('FINNHUB_API_KEY')
        if not api_key:
            return {'news_sentiment': 'N/A', 'news_count': 0, 'earnings_surprise': None}
        try:
            url = "https://finnhub.io/api/v1/company-news"
            params = {
                'symbol': ticker,
                'from': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
                'to': datetime.now().strftime('%Y-%m-%d'),
                'token': api_key
            }
            response = requests.get(url, params=params, timeout=5)
            news = response.json() if response.status_code == 200 else []
            bullish_kw = ['beat', 'surge', 'upgrade', 'growth', 'partnership', 'contract', 'buy']
            bearish_kw = ['miss', 'cut', 'downgrade', 'loss', 'lawsuit', 'investigation']
            bullish = sum(1 for n in news for kw in bullish_kw if kw in n.get('headline', '').lower())
            bearish = sum(1 for n in news for kw in bearish_kw if kw in n.get('headline', '').lower())
            sentiment = 'BULLISH' if bullish > bearish else 'BEARISH' if bearish > bullish else 'NEUTRAL'
            stock = yf.Ticker(ticker)
            earnings = stock.quarterly_earnings
            earnings_surprise = None
            if earnings is not None and not earnings.empty:
                last = earnings.iloc[0]
                actual = last.get('Actual', 0)
                estimate = last.get('Estimate', 0)
                if estimate and estimate != 0:
                    earnings_surprise = round(((actual - estimate) / abs(estimate)) * 100, 2)
            return {'news_count': len(news), 'news_sentiment': sentiment, 'earnings_surprise': earnings_surprise}
        except:
            return {'news_sentiment': 'N/A', 'news_count': 0, 'earnings_surprise': None}

    def get_short_data(self, ticker: str) -> Dict:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            short_pct = info.get('shortPercentOfFloat', 0) * 100
            days_to_cover = info.get('shortRatio', 0)
            score = 0
            if short_pct > 20: score += 25
            elif short_pct > 15: score += 15
            elif short_pct > 10: score += 5
            return {'short_pct': round(short_pct, 2), 'days_to_cover': round(days_to_cover, 2), 'score': score}
        except:
            return {'short_pct': 0, 'days_to_cover': 0, 'score': 0}

    def get_dark_pool_data(self, ticker: str, days: int = 10) -> Dict:
        base_url = "https://cdn.finra.org/equity/regsho/daily/REG%20SHO_{}.csv"
        data_points = []
        current_date = datetime.now()
        days_checked = 0
        calendar_days_back = 0
        while days_checked < days and calendar_days_back < 30:
            date = current_date - timedelta(days=calendar_days_back)
            if date.weekday() >= 5:
                calendar_days_back += 1
                continue
            date_str = date.strftime('%Y%m%d')
            url = base_url.format(date_str)
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
                    ticker_data = df[df['Symbol'] == ticker]
                    if not ticker_data.empty:
                        row = ticker_data.iloc[0]
                        short_vol = float(row['ShortVolume'])
                        total_vol = float(row['TotalVolume'])
                        if total_vol > 0:
                            dp_ratio = (short_vol / total_vol) * 100
                            data_points.append({'date': date_str, 'dp_ratio': dp_ratio})
                            days_checked += 1
                calendar_days_back += 1
                time.sleep(0.2)
            except:
                calendar_days_back += 1
                continue
        if not data_points:
            return {'dp_ratio': 0, 'trend_5d': 0, 'score': 0}
        df = pd.DataFrame(data_points).sort_values('date')
        recent_5d = df['dp_ratio'].tail(5).mean()
        prev_5d = df['dp_ratio'].head(5).mean() if len(df) >= 10 else df['dp_ratio'].mean()
        trend = recent_5d - prev_5d
        score = 0
        if recent_5d > 50 and trend > 5: score += 25
        elif recent_5d > 45 and trend > 3: score += 20
        elif recent_5d > 40: score += 10
        return {'dp_ratio': round(df['dp_ratio'].iloc[-1], 1), 'trend_5d': round(trend, 2), 'score': score}

    def get_congress_trading(self, ticker: str, days: int = 30) -> Dict:
        senate_buys = 0
        house_buys = 0
        cutoff_date = datetime.now() - timedelta(days=days)
        try:
            url = "https://senatestockwatcher.com/api/data/all"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                for trade in response.json():
                    if trade.get('ticker') == ticker:
                        try:
                            td = datetime.strptime(trade.get('transaction_date', ''), '%Y-%m-%d')
                            if td >= cutoff_date and trade.get('type', '').lower() == 'purchase':
                                senate_buys += 1
                        except:
                            pass
        except:
            pass
        try:
            url = "https://housestockwatcher.com/api/data/all"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                for trade in response.json():
                    if trade.get('ticker') == ticker:
                        try:
                            td = datetime.strptime(trade.get('transaction_date', ''), '%Y-%m-%d')
                            if td >= cutoff_date and trade.get('type', '').lower() == 'purchase':
                                house_buys += 1
                        except:
                            pass
        except:
            pass
        total_buys = senate_buys + house_buys
        score = 0
        if total_buys >= 3: score += 25
        elif total_buys >= 2: score += 20
        elif total_buys >= 1: score += 15
        return {'senate_buys': senate_buys, 'house_buys': house_buys, 'total_buys': total_buys, 'score': score}


class SignalScorer:
    def __init__(self, data_sources):
        self.ds = data_sources

    def is_biopharma(self, ticker: str) -> bool:
        try:
            info = yf.Ticker(ticker).info
            sector = info.get('sector', '')
            industry = info.get('industry', '')
            return sector in CONFIG['BANNED_SECTORS'] or industry in CONFIG['BANNED_INDUSTRIES']
        except:
            return False

    def score_ticker_with_data(self, ticker: str, df: pd.DataFrame,
                               current_price: float, position_pct: float,
                               discount_pct: float, rvol: float, hod_pinch: float) -> Optional[Dict]:
        options = self.ds.get_options_anomaly(ticker)
        insider = self.ds.get_insider_activity(ticker)
        finnhub = self.ds.get_finnhub_data(ticker)
        short = self.ds.get_short_data(ticker)
        dark_pool = self.ds.get_dark_pool_data(ticker)
        congress = self.ds.get_congress_trading(ticker)

        mode_a_score = 0
        mode_a_signals = []
        if options['score'] >= 30:
            mode_a_score += options['score']
            mode_a_signals.append(f"⚡ Options: {options['unusual_calls']} unusual (max Vol/OI: {options['max_vol_oi']}x)")
        if insider['score'] >= 20:
            mode_a_score += insider['score']
            mode_a_signals.append(f"💼 Insider: {insider['count']} buys (${insider['total_value']/1000:.0f}k)")
        if dark_pool['score'] >= 15:
            mode_a_score += dark_pool['score']
            mode_a_signals.append(f"🌑 Dark Pool: {dark_pool['dp_ratio']}% (тренд: {dark_pool['trend_5d']:+.1f}%)")
        if congress['score'] >= 15:
            mode_a_score += congress['score']
            mode_a_signals.append(f"🏛️ Congress: {congress['total_buys']} buys (S:{congress['senate_buys']} H:{congress['house_buys']})")

        mode_b_score = 0
        mode_b_signals = []
        if rvol > 2.5:
            mode_b_score += 25
            mode_b_signals.append(f"📈 RVOL: {rvol:.1f}x")
        elif rvol > 2.0:
            mode_b_score += 15
            mode_b_signals.append(f"📈 RVOL: {rvol:.1f}x")
        if finnhub['earnings_surprise'] and finnhub['earnings_surprise'] > 10:
            mode_b_score += 25
            mode_b_signals.append(f"💰 Earnings Beat: +{finnhub['earnings_surprise']:.1f}%")
        if finnhub['news_sentiment'] == 'BULLISH':
            mode_b_score += 15
            mode_b_signals.append(f"📰 News: Bullish")
        if short['score'] >= 15:
            mode_b_score += short['score']
            mode_b_signals.append(f"🎯 Short: {short['short_pct']}%")
        if 50 <= position_pct <= 85:
            mode_b_score += 15
            mode_b_signals.append(f"📊 Position: {position_pct:.0f}%")
        if hod_pinch < 2:
            mode_b_score += 10
            mode_b_signals.append(f"🎯 HOD Pinch: {hod_pinch:.1f}%")

        return {
            'ticker': ticker,
            'price': round(current_price, 2),
            'position_pct': round(position_pct, 1),
            'discount_pct': round(discount_pct, 1),
            'rvol': round(rvol, 2),
            'hod_pinch': round(hod_pinch, 1),
            'mode_a_score': mode_a_score,
            'mode_a_signals': mode_a_signals,
            'mode_a_qualifies': mode_a_score >= CONFIG['MODE_A']['min_score'],
            'mode_b_score': mode_b_score,
            'mode_b_signals': mode_b_signals,
            'mode_b_qualifies': mode_b_score >= CONFIG['MODE_B']['min_score'],
            'unusual_calls': options['unusual_calls'],
            'insider_buys': insider['count'],
            'insider_value': insider['total_value'],
            'short_pct': short['short_pct'],
            'dp_ratio': dark_pool['dp_ratio'],
            'congress_buys': congress['total_buys'],
            'earnings_surprise': finnhub['earnings_surprise'],
            'news_sentiment': finnhub['news_sentiment']
        }


class UltimateScanner:
    def __init__(self):
        self.ds = DataSources(CONFIG)
        self.scorer = SignalScorer(self.ds)
        self.ai = DeepSeekAnalyzer(CONFIG['DEEPSEEK_API_KEY'])
        self.universe = self._load_universe()

    def _load_universe(self) -> List[str]:
        cache_file = 'universe_cache.csv'
        if os.path.exists(cache_file) and (time.time() - os.path.getmtime(cache_file)) < 604800:
            tickers = pd.read_csv(cache_file)['Symbol'].tolist()
            print(f"✅ Из кэша: {len(tickers)} тикеров")
            return tickers
        print("🔄 Загрузка полной вселенной...")
        all_tickers = []
        headers = {'User-Agent': 'Mozilla/5.0'}
        for ex in ['NASDAQ', 'NYSE', 'AMEX']:
            try:
                url = f"https://api.nasdaq.com/api/screener/stocks?tableType=traded&exchange={ex}&limit=10000"
                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code == 200:
                    rows = response.json().get('data', {}).get('rows', [])
                    tickers_ex = [r['symbol'] for r in rows if r.get('symbol')]
                    all_tickers.extend(tickers_ex)
                    print(f"  ✅ {ex}: {len(tickers_ex)}")
            except Exception as e:
                print(f"  ⚠️ {ex}: {e}")
        all_tickers = list(set(all_tickers))
        pd.DataFrame({'Symbol': all_tickers}).to_csv(cache_file, index=False)
        print(f"✅ ВСЕГО: {len(all_tickers)} тикеров")
        return all_tickers

    def run(self) -> Dict:
        start = time.time()
        print("="*70)
        print("🎯 ULTIMATE SCANNER v4.0 — FULL UNIVERSE")
        print("="*70)
        print(f"📊 Universe: {len(self.universe)} тикеров")
        print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n📥 ЭТАП 1: Batch загрузка (пачками по 500)...")
        batch_size = 500
        all_data = {}
        total_batches = (len(self.universe) + batch_size - 1) // batch_size
        for i in range(0, len(self.universe), batch_size):
            batch = self.universe[i:i+batch_size]
            batch_num = i // batch_size + 1
            print(f"  Батч {batch_num}/{total_batches} ({len(batch)} тикеров)...", end=' ', flush=True)
            try:
                df = yf.download(batch, period='6mo', interval='1d', progress=False, threads=True)
                for ticker in batch:
                    try:
                        if isinstance(df.columns, pd.MultiIndex):
                            if ticker in df.columns.get_level_values(1):
                                ticker_data = df.xs(ticker, axis=1, level=1).dropna()
                                if not ticker_data.empty and len(ticker_data) >= 100:
                                    all_data[ticker] = ticker_data
                    except:
                        continue
                print("✅")
            except Exception as e:
                print(f"❌ {e}")
            time.sleep(1)
        print(f"\n✅ Загружено: {len(all_data)} тикеров")

        print("\n🔍 ЭТАП 2: Фильтрация (цена, объём)...")
        filtered = []
        for ticker, df in all_data.items():
            try:
                current_price = df['Close'].iloc[-1]
                avg_vol = df['Volume'].tail(20).mean()
                if current_price < CONFIG['MIN_PRICE']:
                    continue
                if avg_vol < CONFIG['MIN_VOLUME']:
                    continue
                high_6m = df['High'].max()
                low_6m = df['Low'].min()
                position_pct = ((current_price - low_6m) / (high_6m - low_6m) * 100) if high_6m > low_6m else 50
                discount_pct = ((current_price - high_6m) / high_6m * 100)
                if not (position_pct < 70 and discount_pct < -25) and not (50 <= position_pct <= 85):
                    continue
                filtered.append(ticker)
            except:
                continue
        print(f"✅ После фильтрации: {len(filtered)} тикеров")

        print(f"\n🔍 ЭТАП 3: Детальный скоринг {len(filtered)} тикеров...")
        results = []
        for i, ticker in enumerate(filtered, 1):
            if i % 50 == 0:
                print(f"  Прогресс: {i}/{len(filtered)}...", flush=True)
            df = all_data[ticker]
            if self.scorer.is_biopharma(ticker):
                continue
            try:
                current_price = df['Close'].iloc[-1]
                avg_vol = df['Volume'].tail(20).mean()
                high_6m = df['High'].max()
                low_6m = df['Low'].min()
                position_pct = ((current_price - low_6m) / (high_6m - low_6m) * 100) if high_6m > low_6m else 50
                discount_pct = ((current_price - high_6m) / high_6m * 100)
                rvol = df['Volume'].iloc[-1] / avg_vol if avg_vol > 0 else 0
                today = df.iloc[-1]
                hod_pinch = ((today['High'] - today['Close']) / today['High'] * 100) if today['High'] > 0 else 0
                result = self.scorer.score_ticker_with_data(
                    ticker, df, current_price, position_pct, discount_pct, rvol, hod_pinch
                )
                if result and (result['mode_a_qualifies'] or result['mode_b_qualifies']):
                    mode = 'A' if result['mode_a_qualifies'] else 'B'
                    score = result[f'mode_{mode.lower()}_score']
                    print(f"    ✅ {ticker} — MODE {mode} (score: {score})")
                    results.append(result)
            except:
                continue

        mode_a = [r for r in results if r['mode_a_qualifies']]
        mode_b = [r for r in results if r['mode_b_qualifies'] and not r['mode_a_qualifies']]
        mode_a.sort(key=lambda x: x['mode_a_score'], reverse=True)
        mode_b.sort(key=lambda x: x['mode_b_score'], reverse=True)
        top_a = mode_a[:CONFIG['MODE_A']['top_n']]
        top_b = mode_b[:CONFIG['MODE_B']['top_n']]
        print(f"\n🎯 MODE A (SNIPER): {len(mode_a)} найдено, берём топ-{len(top_a)}")
        print(f"⚡ MODE B (TACTICAL): {len(mode_b)} найдено, берём топ-{len(top_b)}")

        print("\n🧠 ЭТАП 4: DeepSeek AI анализ...")
        for r in top_a:
            print(f"  🔴 [A] {r['ticker']}...")
            r['ai'] = self.ai.analyze(r['ticker'], r, 'A')
        for r in top_b:
            print(f"  🟡 [B] {r['ticker']}...")
            r['ai'] = self.ai.analyze(r['ticker'], r, 'B')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        output = {
            'timestamp': timestamp,
            'mode_a': top_a,
            'mode_b': top_b,
            'stats': {
                'universe_size': len(self.universe),
                'loaded': len(all_data),
                'filtered': len(filtered),
                'mode_a_total': len(mode_a),
                'mode_b_total': len(mode_b),
                'scan_time_sec': round(time.time() - start, 1)
            }
        }
        with open('scan_results.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        with open(f'scan_{timestamp}.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        self._print_results(top_a, top_b)
        print(f"\n💾 Сохранено: scan_results.json, scan_{timestamp}.json")
        print(f"⏱️  Время: {time.time() - start:.1f} сек")
        return output

    def _print_results(self, mode_a, mode_b):
        print("\n" + "="*70)
        print("🔴 MODE A: SNIPER (2 тикера, +40%, позиция $2000)")
        print("="*70)
        if not mode_a:
            print("  ⚪ Нет сигналов сегодня")
        else:
            for r in mode_a:
                print(f"\n{'─'*70}")
                print(f"📈 {r['ticker']} | ${r['price']} | Score: {r['mode_a_score']}")
                print(f"   Позиция: {r['position_pct']}% | Скидка: {r['discount_pct']}% | RVOL: {r['rvol']}x")
                for sig in r['mode_a_signals'][:5]:
                    print(f"   {sig}")
                print(f"{'─'*70}")
                if r.get('ai'):
                    if r['ai']['type']: print(f"🎯 {r['ai']['type']}")
                    if r['ai']['physics']: print(f"🧠 {r['ai']['physics']}")
                    if r['ai']['signal']: print(f"💥 {r['ai']['signal']}")
        print("\n" + "="*70)
        print("🟡 MODE B: TACTICAL (2 тикера, +20%, позиция $1000)")
        print("="*70)
        if not mode_b:
            print("  ⚪ Нет сигналов сегодня")
        else:
            for r in mode_b:
                print(f"\n{'─'*70}")
                print(f"📈 {r['ticker']} | ${r['price']} | Score: {r['mode_b_score']}")
                print(f"   Позиция: {r['position_pct']}% | Скидка: {r['discount_pct']}% | RVOL: {r['rvol']}x")
                for sig in r['mode_b_signals'][:5]:
                    print(f"   {sig}")
                print(f"{'─'*70}")
                if r.get('ai'):
                    if r['ai']['type']: print(f"🎯 {r['ai']['type']}")
                    if r['ai']['physics']: print(f"🧠 {r['ai']['physics']}")
                    if r['ai']['signal']: print(f"💥 {r['ai']['signal']}")


if __name__ == "__main__":
    if not CONFIG['DEEPSEEK_API_KEY']:
        print("❌ DEEPSEEK_API_KEY не найден")
        print("   В Colab: os.environ['DEEPSEEK_API_KEY'] = 'sk-...'")
        exit(1)
    if not CONFIG['FINNHUB_API_KEY']:
        print("⚠️  FINNHUB_API_KEY не найден (опционально)")
    scanner = UltimateScanner()
    scanner.run()
