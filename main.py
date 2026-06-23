#!/usr/bin/env python3
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ultimate_scanner import UltimateScanner, CONFIG

def main():
    print("="*70)
    print("🚀 ULTIMATE SCANNER — Railway")
    print("="*70)
    if not CONFIG['DEEPSEEK_API_KEY']:
        print("❌ DEEPSEEK_API_KEY not found"); sys.exit(1)
    scanner = UltimateScanner()
    results = scanner.run()
    print("\n✅ Done")

if __name__ == "__main__":
    main()