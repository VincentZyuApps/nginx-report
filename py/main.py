# 第三方库
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# 标准库
import asyncio
import gzip
import json
import os
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from collections import Counter

import ip_apis

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 静态文件目录（字体）
app.mount("/static", StaticFiles(directory="static"), "static")

LOG_FILE = "/var/log/nginx/access.log"

def get_all_log_files():
    """获取所有日志文件（当前+轮转）"""
    log_dir = "/var/log/nginx"
    files = []
    
    # 当前日志
    if os.path.exists(LOG_FILE):
        files.append(("current", "当前"))
    
    # 轮转日志 access.log.1, .2, ... 以及 .gz压缩的
    for i in range(1, 20):
        # 未压缩的
        path = f"{log_dir}/access.log.{i}"
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            date = time.strftime("%m-%d", time.localtime(mtime))
            files.append((f"access.log.{i}", f"{i}"))
            continue
        
        # 压缩的
        gz_path = f"{log_dir}/access.log.{i}.gz"
        if os.path.exists(gz_path):
            mtime = os.path.getmtime(gz_path)
            date = time.strftime("%m-%d", time.localtime(mtime))
            files.append((f"access.log.{i}.gz", f"{i}"))
            continue
        
        # 如果都不存在，停止遍历
        if not os.path.exists(path) and not os.path.exists(gz_path):
            # 允许中间有间隙，继续找下一个
            if i < 5:
                continue
            break
    
    return files

# 数据库配置
DB_FILE = "data/data.db"
CACHE_TTL = 30 * 24 * 3600  # 30 天

# 全局查询进度
query_status = {"total": 0, "done": 0, "running": False, "api": ""}
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
        query_status = {"total": len(ips), "done": 0, "running": True, "api": ip_apis.current_api_name}
    
    for ip in ips:
        get_ip_location(ip)
        with query_lock:
            query_status["done"] += 1
            query_status["api"] = ip_apis.current_api_name
        # 每秒最多45个请求 (ip-api限制)
        time.sleep(0.025)
    
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
    return ip_apis.fetch_location(ip)

def get_log_data(log_file):
    """从指定日志文件读取IP统计"""
    if not os.path.exists(log_file):
        return []
    
    try:
        ips = []
        if log_file.endswith('.gz'):
            with gzip.open(log_file, 'rt', encoding='utf-8') as f:
                ips = [line.split()[0] for line in f if line.strip() and len(line.split()) > 0]
        else:
            with open(log_file, "r", encoding="utf-8") as f:
                ips = [line.split()[0] for line in f if line.strip() and len(line.split()) > 0]
        
        if not ips:
            return []
        counter = Counter(ips)
        return [{"ip": ip, "count": count} for ip, count in counter.items()]
    except Exception as e:
        print(f"Log Error: {e}")
        return []

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, sort: str = None, order: str = None, font: str = None, logfile: str = None):
    # 默认重定向到完整参数
    if sort is None or order is None or font is None:
        return RedirectResponse(url=f"/?logfile=current&sort=count&order=desc&font=enabled")
    
    # 获取可选的日志文件列表
    all_log_files = get_all_log_files()
    
    # 默认使用当前日志
    if logfile is None:
        logfile = "current"
    
    # 读取指定日志文件
    if logfile == "current":
        log_path = "/var/log/nginx/access.log"
    else:
        log_path = f"/var/log/nginx/{logfile}"
    
    data = get_log_data(log_path)
    
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
            "use_custom_font": font == "enabled",
            "all_log_files": all_log_files,
            "current_logfile": logfile
        }
    )

@app.get("/status")
async def status():
    """查询进度API"""
    return query_status

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=60418)
