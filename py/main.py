from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from collections import Counter
import uvicorn
import os
import time
import sqlite3
import asyncio

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 静态文件目录（字体）
app.mount("/static", StaticFiles(directory="static"), "static")

LOG_FILE = "/var/log/nginx/access.log"
DB_FILE = "data/data.db"
CACHE_TTL = 30 * 24 * 3600  # 30 天

# 全局查询进度
import threading

query_status = {"total": 0, "done": 0, "running": False}
query_lock = threading.Lock()

def init_db():
    """初始化数据库"""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ip_cache (
            ip TEXT PRIMARY KEY,
            location TEXT,
            timestamp INTEGER
        )
    """)
    conn.commit()
    conn.close()

def query_ips_background(ips: list):
    """后台查询IP属地"""
    global query_status
    with query_lock:
        query_status = {"total": len(ips), "done": 0, "running": True}
    
    for ip in ips:
        get_ip_location(ip)
        with query_lock:
            query_status["done"] += 1
    
    with query_lock:
        query_status["running"] = False

async def run_background_query(ips: list):
    """异步后台查询"""
    await asyncio.to_thread(query_ips_background, ips)

def get_cached_location(ip: str) -> tuple:
    """获取缓存的IP属地"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT location, timestamp FROM ip_cache WHERE ip = ?", (ip,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        location, timestamp = row
        if time.time() - timestamp < CACHE_TTL:
            return (location, timestamp)
    return None

def save_location(ip: str, location: str):
    """保存IP属地到缓存"""
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT OR REPLACE INTO ip_cache (ip, location, timestamp) VALUES (?, ?, ?)",
        (ip, location, int(time.time()))
    )
    conn.commit()
    conn.close()

def get_ip_location(ip: str) -> str:
    """查询IP属地，支持缓存"""
    cached = get_cached_location(ip)
    if cached:
        return cached[0]
    
    location = fetch_from_api(ip)
    if location:
        save_location(ip, location)
    return location or "查询失败"

def fetch_from_api(ip: str) -> str:
    """从IP-API获取属地"""
    try:
        import urllib.request
        import urllib.error
        import json
        url = f"http://ip-api.com/json/{ip}?lang=zh-CN"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("status") == "success":
                return f"{data.get('country', '')} {data.get('regionName', '')} {data.get('city', '')} [{data.get('isp', '')}]"
    except Exception as e:
        print(f"Fetch error: {e}")
    return None

def get_log_data():
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            ips = [line.split()[0] for line in f if line.strip() and len(line.split()) > 0]
        counter = Counter(ips)
        return [{"ip": ip, "count": count} for ip, count in counter.items()]
    except Exception as e:
        print(f"Log Error: {e}")
        return []

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, sort: str = "count", order: str = "desc", font: str = "disabled"):
    data = get_log_data()
    
    # 排序逻辑
    is_reverse = (order == "desc")
    if sort == "ip":
        data.sort(key=lambda x: x["ip"], reverse=is_reverse)
    else:
        data.sort(key=lambda x: x["count"], reverse=is_reverse)
    
    # 为每个IP填充属地（已有缓存的直接返回，无缓存返回"待查询"）
    for item in data:
        cached = get_cached_location(item["ip"])
        if cached:
            item["location"] = cached[0]
            item["status"] = "done"
        else:
            item["location"] = "待查询"
            item["status"] = "pending"
    
    # 启动后台查询
    ips = [item["ip"] for item in data if item["status"] == "pending"]
    if ips and not query_status["running"]:
        query_status["total"] = len(ips)
        query_status["done"] = 0
        query_status["running"] = True
        # 用 asyncio 在后台运行查询
        asyncio.create_task(run_background_query(ips))
    
    return templates.TemplateResponse(
        request, 
        "index.html", 
        {
            "data": data,
            "current_sort": sort,
            "current_order": order,
            "total": str(query_status["total"]),
            "done": str(query_status["done"]),
            "running": query_status["running"],
            "use_custom_font": font == "enabled"
        }
    )

@app.get("/status")
async def status():
    """查询进度API"""
    return query_status

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=60418)
