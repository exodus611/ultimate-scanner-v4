# 🎯 Ultimate Scanner v4.0

Full NASDAQ Scanner (5000+ tickers) — GitHub + Colab Edition

## Режимы:
- **MODE A (SNIPER)**: 2 тикера, +40%, позиция $2000, горизонт 3-7 дней
- **MODE B (TACTICAL)**: 2 тикера, +20%, позиция $1000, горизонт 1-3 дня

## Стоимость:
$0.06/мес (только DeepSeek API)

## Запуск в Colab:

    import os
    os.environ['DEEPSEEK_API_KEY'] = 'sk-...'
    os.environ['FINNHUB_API_KEY'] = '...'
    !python ultimate_scanner.py

## Источники данных (все бесплатные):
- yfinance: опционы, OHLCV, short interest
- Finnhub: новости, earnings
- OpenInsider: инсайдерские покупки
- Senate/House Stock Watcher: конгрессмены
- FINRA ATS: dark pool (1 день задержки)
- DeepSeek AI: анализ