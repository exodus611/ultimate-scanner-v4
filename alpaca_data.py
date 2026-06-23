"""
Alpaca Markets Data Loader
Заменяет yfinance для загрузки OHLCV данных.
Не блокируется облачными IP (Railway, AWS, GCP).
"""
import os
import pandas as pd
from alpaca.data import StockHistoricalDataClient, StockBarsRequest, TimeFrame
from datetime import datetime, timedelta

def get_client():
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    if not api_key or not secret_key:
        raise ValueError("ALPACA_API_KEY и ALPACA_SECRET_KEY не установлены в переменных окружения!")
    return StockHistoricalDataClient(api_key, secret_key)

def fetch_batch_ohlcv(tickers, days=180):
    """
    Загружает дневные свечи для списка тикеров через Alpaca.
    Возвращает dict {ticker: DataFrame}
    """
    client = get_client()
    end = datetime.now()
    start = end - timedelta(days=days)
    
    all_data = {}
    batch_size = 100  # Alpaca позволяет до ~200, но 100 безопаснее
    
    print(f"  📡 Загрузка через Alpaca: {len(tickers)} тикеров...")
    
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
                    # Конвертируем в DataFrame
                    data = []
                    for bar in bars[symbol]:
                        data.append({
                            'Open': bar.open,
                            'High': bar.high,
                            'Low': bar.low,
                            'Close': bar.close,
                            'Volume': bar.volume
                        })
                    
                    df = pd.DataFrame(data)
                    if not df.empty and len(df) >= 50:
                        all_data[symbol] = df
                        
            if bn % 5 == 0:
                print(f"    Progress: {bn} batches, {len(all_data)} tickers loaded", flush=True)
                
        except Exception as e:
            print(f"    ⚠️ Ошибка батча {bn}: {e}")
            
    return all_data
