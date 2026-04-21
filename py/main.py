import asyncio
import gzip
import os
import sqlite3
import threading
import time
from collections import Counter

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api import fetch_location_with_source, get_current_api

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), "static")

LOG_DIR = "/var/log/nginx"
DB_FILE = "data/data.db"
CACHE_TTL = 30 * 24 * 3600

query_status = {"total": 0, "done": 0, "running": False, "api": "", "retry": 0, "next_retry": 0}
query_lock = threading.Lock()


def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""CREATE TABLE IF NOT EXISTS ip_cache (
        ip TEXT PRIMARY KEY, location TEXT, api_source TEXT, timestamp INTEGER)""")
    try:
        conn.execute("SELECT api_source FROM ip_cache LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE ip_cache ADD COLUMN api_source TEXT")
    conn.commit()
    conn.close()


def get_all_log_files():
    """返回 (key, label, filename, date) 列表"""
    files = []
    p = f"{LOG_DIR}/access.log"
    if os.path.exists(p):
        date = time.strftime("%m-%d", time.localtime(os.path.getmtime(p)))
        files.append(("current", "当前", "access.log", date))
    for i in range(1, 20):
        p = f"{LOG_DIR}/access.log.{i}"
        gz = p + ".gz"
        if os.path.exists(p):
            date = time.strftime("%m-%d", time.localtime(os.path.getmtime(p)))
            files.append((f"access.log.{i}", str(i), f"access.log.{i}", date))
        elif os.path.exists(gz):
            date = time.strftime("%m-%d", time.localtime(os.path.getmtime(gz)))
            files.append((f"access.log.{i}.gz", str(i), f"access.log.{i}.gz", date))
        elif i >= 5:
            break
    return files


def get_log_data(log_path):
    if not os.path.exists(log_path):
        return []
    try:
        opener = gzip.open(log_path, "rt", encoding="utf-8") if log_path.endswith(".gz") else open(log_path, encoding="utf-8")
        with opener as f:
            ips = [line.split()[0] for line in f if line.strip()]
        return [{"ip": ip, "count": c} for ip, c in Counter(ips).items()]
    except Exception as e:
        print(f"[log] {e}")
        return []


def db_get(ip):
    conn = sqlite3.connect(DB_FILE)
    row = conn.execute("SELECT location, api_source, timestamp FROM ip_cache WHERE ip=?", (ip,)).fetchone()
    conn.close()
    if row and time.time() - row[2] < CACHE_TTL:
        return (row[0], row[1])
    return None


def db_set(ip, location, api_source):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT OR REPLACE INTO ip_cache VALUES (?,?,?,?)", (ip, location, api_source, int(time.time())))
    conn.commit()
    conn.close()


def query_ips_background(ips):
    global query_status
    with query_lock:
        query_status = {"total": len(ips), "done": 0, "running": True, "api": get_current_api(), "retry": 0, "next_retry": 0}

    for idx, ip in enumerate(ips):
        delay = 1
        attempt = 0
        while True:
            print(f"[{idx+1}/{len(ips)}] attempt {attempt+1} {ip}")
            location, api_used = fetch_location_with_source(ip)
            with query_lock:
                query_status["api"] = api_used or query_status["api"]
                query_status["retry"] = attempt
                query_status["next_retry"] = delay if not location else 0
            if location:
                db_set(ip, location, api_used)
                with query_lock:
                    query_status["done"] += 1
                break
            attempt += 1
            time.sleep(delay)
            delay = min(delay * 2, 32)
        time.sleep(0.05)

    with query_lock:
        query_status["running"] = False


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, sort: str = None, order: str = None, font: str = None, logfile: str = None):
    if sort is None or order is None or font is None:
        return RedirectResponse(url="/?logfile=current&sort=count&order=desc&font=enabled")

    logfile = logfile or "current"
    log_path = f"{LOG_DIR}/access.log" if logfile == "current" else f"{LOG_DIR}/{logfile}"
    data = get_log_data(log_path)

    is_reverse = (order == "desc")
    data.sort(key=lambda x: x["ip"] if sort == "ip" else x["count"], reverse=is_reverse)

    for item in data:
        cached = db_get(item["ip"])
        if cached:
            item["location"], item["api_source"], item["status"] = cached[0], cached[1], "done"
        else:
            item["location"], item["api_source"], item["status"] = "待查询", "", "pending"

    pending = [item["ip"] for item in data if item["status"] == "pending"]
    if pending and not query_status["running"]:
        threading.Thread(target=query_ips_background, args=(pending,), daemon=True).start()

    log_mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(log_path))) if os.path.exists(log_path) else ""

    return templates.TemplateResponse(request, "index.html", {
        "data": data,
        "current_sort": sort,
        "current_order": order,
        "use_custom_font": font == "enabled",
        "all_log_files": get_all_log_files(),
        "current_logfile": logfile,
        "running": query_status["running"],
        "qs": query_status,
        "log_path": log_path,
        "log_mtime": log_mtime,
    })


@app.get("/status")
async def status():
    return query_status


@app.get("/locations")
async def locations(ips: str = ""):
    result = {}
    for ip in ips.split(","):
        ip = ip.strip()
        if ip:
            cached = db_get(ip)
            if cached:
                result[ip] = {"location": cached[0], "api_source": cached[1]}
    return result


if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=60418)
