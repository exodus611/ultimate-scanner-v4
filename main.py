#!/usr/bin/env python3
"""Railway Entry Point — v7.8 Manual Start"""
import os, sys, threading, time
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from ultimate_scanner import UltimateScanner, CONFIG, DEEPSEEK_KEY, ALPACA_KEY, ALPACA_SECRET

app = FastAPI(title="Ultimate Scanner Dashboard")
scan_results = {"mode_a": [], "mode_b": [], "stats": {}, "timestamp": ""}
scan_lock = threading.Lock()

def run_scanner():
    global scan_results
    print("="*70)
    print(f"🚀 Запуск сканера: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    try:
        if not DEEPSEEK_KEY:
            print("❌ DEEPSEEK_API_KEY not found"); return
        if not ALPACA_KEY or not ALPACA_SECRET:
            print("❌ ALPACA keys not found"); return
        scanner = UltimateScanner()
        results = scanner.run()
        with scan_lock:
            scan_results = results
        print("\n✅ Scan completed successfully")
    except Exception as e:
        print(f"❌ Scanner error: {e}")
        import traceback; traceback.print_exc()

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    try:
        with open("dashboard.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "<h1>Dashboard not found</h1>"

@app.get("/api/results")
async def get_results():
    with scan_lock:
        return JSONResponse(content=scan_results)

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.post("/api/scan")
async def trigger_scan():
    threading.Thread(target=run_scanner, daemon=True).start()
    return {"status": "started", "message": "Scan triggered"}

if __name__ == "__main__":
    # НЕ запускаем сканер автоматически
    port = int(os.environ.get("PORT", 8000))
    print(f"🌐 Dashboard: http://0.0.0.0:{port}")
    print("📌 Сканер запускается вручную: POST /api/scan")
    uvicorn.run(app, host="0.0.0.0", port=port)
