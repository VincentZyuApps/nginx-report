from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from collections import Counter
import uvicorn
import os
import time
import sqlite3

app = FastAPI()
templates = Jinja2Templates(directory="templates")

LOG_FILE = "/var/log/nginx/access.log"
DB_FILE = "data/data.db"
CACHE_TTL = 30 * 24 * 3600  # 30 天

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
async def index(request: Request, sort: str = "count", order: str = "desc"):
    data = get_log_data()
    
    # 排序逻辑
    is_reverse = (order == "desc")
    if sort == "ip":
        data.sort(key=lambda x: x["ip"], reverse=is_reverse)
    else:
        data.sort(key=lambda x: x["count"], reverse=is_reverse)
    
    # 后端查询 IP 属地（带缓存）
    for item in data:
        item["location"] = get_ip_location(item["ip"])
        
    return templates.TemplateResponse(
        request, 
        "index.html", 
        {
            "data": data,
            "current_sort": sort,
            "current_order": order
        }
    )

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=60418)
