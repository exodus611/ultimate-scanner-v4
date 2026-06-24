#!/usr/bin/env python3
import os, sys, threading
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from ultimate_scanner import UltimateScanner, DEEPSEEK_KEY

app = FastAPI(title="Scanner Dashboard")
scan_results = {"signals": [], "stats": {}, "timestamp": ""}
scan_lock = threading.Lock()
is_running = False

def run_scanner():
    global scan_results, is_running
    try:
        scanner = UltimateScanner()
        results = scanner.run()
        with scan_lock:
            scan_results = results
    except Exception as e:
        print(f"❌ Scanner error: {e}")
        import traceback; traceback.print_exc()
    finally:
        is_running = False

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return "<h1>Scanner v7.13</h1><p>POST /api/scan to start</p>"

@app.get("/api/results")
async def get_results():
    with scan_lock:
        return JSONResponse(content=scan_results)

@app.get("/api/health")
async def health():
    return {"status":"ok","timestamp":datetime.now().isoformat()}

@app.post("/api/scan")
async def trigger_scan():
    global is_running
    if is_running:
        return {"status":"already_running"}
    is_running = True
    threading.Thread(target=run_scanner, daemon=True).start()
    return {"status":"started"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🌐 Dashboard: http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
