#!/usr/bin/env python3
import subprocess
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

TARGET = "http://localhost:3000"
LOGIN_URL = f"{TARGET}/rest/user/login"
WORDLIST_URL = (
    "https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/"
    "refs/heads/master/SQL%20Injection/Intruder/SQL-Injection"
)
WORDLIST_FILE = "sqli-payloads.txt"
RESULT_FILE = "ffuf-result.json"
DEBUG_FILE = "ffuf-debug.log"
# Путь к ffuf, установленному через go install
FFUF_BIN = os.path.expanduser("~/go/bin/ffuf")

def wait_for_service():
    print("[*] Waiting for Juice Shop...")
    for i in range(1, 91):
        try:
            urllib.request.urlopen(f"{TARGET}/rest/products", timeout=5)
            print(f"[+] Juice Shop is ready (attempt {i})")
            return True
        except Exception:
            if i == 90:
                print("::error::Juice Shop did not start within 6 minutes")
                return False
            time.sleep(4)
    return False

def download_wordlist():
    print("[*] Downloading SQLi wordlist...")
    urllib.request.urlretrieve(WORDLIST_URL, WORDLIST_FILE)
    with open(WORDLIST_FILE, encoding="utf-8") as f:
        lines = sum(1 for _ in f)
    print(f"[+] Wordlist: {lines} payloads")
    return lines

def run_ffuf():
    print("[*] Running ffuf...")
    cmd = [
        FFUF_BIN,
        "-u", LOGIN_URL,
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", '{"email":"FUZZ","password":"anothervalue"}',
        "-w", WORDLIST_FILE,
        "-mc", "200",
        "-mr", "authentication",
        "-t", "10",
        "-o", RESULT_FILE,
        "-of", "json",
        "-debug-log", DEBUG_FILE,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    # Если ffuf упал — покажем stderr, чтобы было понятно, в чём проблема
    if res.returncode != 0 and res.stderr:
        print("FFUF stderr:")
        print(res.stderr)

    if not Path(RESULT_FILE).exists():
        print("::error::ffuf did not produce results")
        return []

    with open(RESULT_FILE, encoding="utf-8") as f:
        data = json.load(f)
    results = data.get("results", [])

    if results:
        print("\n[!] Vulnerable payloads found:")
        for i, r in enumerate(results, 1):
            payload = r.get("input", {}).get("FUZZ", "N/A")
            status = r.get("status", "N/A")
            length = r.get("length", "N/A")
            print(f"  [{i}] {payload} -> HTTP {status}, {length} bytes")
        print()

    return results

def main():
    # Проверка наличия ffuf
    if not os.path.isfile(FFUF_BIN):
        print(f"::error::ffuf binary not found at {FFUF_BIN}. Did you run 'go install'?")
        sys.exit(1)

    if not wait_for_service():
        sys.exit(1)

    download_wordlist()
    results = run_ffuf()
    count = len(results)

    print(f"\nTotal hits: {count}")

    if count > 0:
        print(f"::error::SQL Injection detected: {count} payloads bypassed authentication")
        sys.exit(1)
    else:
        print("::notice::No SQLi detected")
        sys.exit(0)

if __name__ == "__main__":
    main()
