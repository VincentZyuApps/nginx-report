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

# IP查询API
# 国家名中英对照
COUNTRY_MAP = {
    "China": "中国", "CN": "中国",
    "United States": "美国", "US": "美国",
    "United Kingdom": "英国", "UK": "英国",
    "Russia": "俄罗斯", "RU": "俄罗斯",
    "Germany": "德国", "DE": "德国",
    "Japan": "日本", "JP": "日本",
    "South Korea": "韩国", "KR": "韩国",
    "Singapore": "新加坡", "SG": "新加坡",
    "Hong Kong": "香港", "HK": "香港",
    "Taiwan": "台湾", "TW": "台湾",
    "France": "法国", "FR": "法国",
    "India": "印度", "IN": "印度",
    "Canada": "加拿大", "CA": "加拿大",
    "Australia": "澳大利亚", "AU": "澳大利亚",
    "Brazil": "巴西", "BR": "巴西",
    "Netherlands": "荷兰", "NL": "荷兰",
    "Ireland": "爱尔兰", "IE": "爱尔兰",
    "Switzerland": "瑞士", "CH": "瑞士",
    "South Africa": "南非", "ZA": "南非",
}

current_api_name = "ip-api"

def normalize_location(country: str, region: str, city: str, isp: str) -> str:
    """统一格式化位置信息"""
    parts = []
    
    if country:
        country = COUNTRY_MAP.get(country, country)
        if country == "中国" and region:
            parts.append(region)
        else:
            parts.append(country)
    
    if region and region != country:
        parts.append(region)
    
    if city:
        parts.append(city)
    
    ispTxt = ""
    if isp:
        isp = isp.strip()
        for name in ["电信", "联通", "移动", "铁通", "教育网", "科技网"]:
            if name in isp:
                ispTxt = name
                break
        if not ispTxt:
            ispTxt = isp[:15]
    
    result = " ".join(parts)
    if ispTxt:
        result += f" [{ispTxt}]"
    
    return result.strip()

# ==================== 多API支持 ====================
# 按优先级排序：ip-api(限速) -> pconline -> ipsb -> ipwhois

def fetch_from_ipapi(ip: str) -> str:
    """ip-api.com - 免费版45次/分钟，返回: 国家/省/城市/ISP"""
    try:
        url = f"http://demo.ip-api.com/json/{ip}?fields=66842623&lang=zh-CN"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("status") == "success":
                return normalize_location(
                    data.get("country", ""),
                    data.get("regionName", ""),
                    data.get("city", ""),
                    data.get("isp", "")
                )
    except Exception as e:
        print(f"[ip-api] Error: {e}")
    return None

def fetch_from_pconline(ip: str) -> str:
    """pconline.com.cn - 淘宝IP库，返回: 省/城市"""
    try:
        url = f"https://whois.pconline.com.cn/ipJson.jsp?ip={ip}&json=true"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("gbk"))
            if data.get("pro"):
                pro = data.get("pro", "")
                city = data.get("city", "")
                return f"{pro} {city}".strip()
    except Exception as e:
        print(f"[pconline] Error: {e}")
    return None

def fetch_from_ipsb(ip: str) -> str:
    """ip.sb - 免费无限制，返回: 国家/省/城市/ISP/AS"""
    try:
        url = f"https://api.ip.sb/geoip/{ip}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("country"):
                return normalize_location(
                    data.get("country", ""),
                    data.get("region", ""),
                    data.get("city", ""),
                    data.get("isp", "")
                )
    except Exception as e:
        print(f"[ip.sb] Error: {e}")
    return None

def fetch_from_ipwhois(ip: str) -> str:
    """ipwhois.app - 返回: 国家/省/城市/ISP/经纬度"""
    try:
        url = f"https://ipwhois.app/json/{ip}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("country"):
                return normalize_location(
                    data.get("country", ""),
                    data.get("region", ""),
                    data.get("city", ""),
                    data.get("isp", "")
                )
    except Exception as e:
        print(f"[ipwhois] Error: {e}")
    return None

def fetch_from_ipapi2location(ip: str) -> str:
    """ip2location.io - 免费版5000次/天，返回: 国家/省/城市/ISP"""
    try:
        url = f"https://api.ip2location.io/?key=demo&ip={ip}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("country_code"):
                return normalize_location(
                    data.get("country_name", ""),
                    data.get("region_name", ""),
                    data.get("city_name", ""),
                    data.get("isp", "")
                )
    except Exception as e:
        print(f"[ip2location] Error: {e}")
    return None

# API列表: (名称, 函数, 是否有速率限制)
APIS = [
    ("ip-api", fetch_from_ipapi, True),      # 45次/分钟
    ("pconline", fetch_from_pconline, False),
    ("ip.sb", fetch_from_ipsb, False),
    ("ipwhois", fetch_from_ipwhois, False),
]

# 当前使用的API索引
_api_index = 0
_api_name = "ip-api"

def fetch_from_api(ip: str) -> str:
    """尝试多个API获取IP属地，按顺序遍历直到成功"""
    global _api_index, _api_name
    
    for i in range(len(APIS)):
        idx = (_api_index + i) % len(APIS)
        api_name, api_func, has_rate_limit = APIS[idx]
        
        location = api_func(ip)
        if location:
            _api_index = idx
            _api_name = api_name
            # 如果刚用了限速API，等待
            if has_rate_limit:
                time.sleep(0.025)
            return location
    
    return None

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
query_status = {"total": 0, "done": 0, "running": False, "api": "", "retry": 0, "next_retry": 0}
query_lock = threading.Lock()

def init_db():
    """初始化数据库"""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ip_cache (
            ip TEXT PRIMARY KEY,
            location TEXT,
            api_source TEXT,
            timestamp INTEGER
        )
    """)
    # 如果api_source列不存在，添加它
    try:
        conn.execute("SELECT api_source FROM ip_cache LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE ip_cache ADD COLUMN api_source TEXT")
    conn.commit()
    conn.close()

def query_ips_background(ips: list):
    """后台查询IP属地"""
    global query_status
    delay = 2
    retry_count = 0
    
    with query_lock:
        query_status = {"total": len(ips), "done": 0, "running": True, "api": _api_name, "retry": 0, "next_retry": 0}
    
    for ip in ips:
        location = fetch_from_api(ip)
        retry_count = retry_count + (1 if location is None else -retry_count)
        
        with query_lock:
            query_status["done"] += 1
            query_status["api"] = _api_name
            query_status["retry"] = max(0, retry_count)
            query_status["next_retry"] = delay if location is None else 0
        
        if location is None:
            # 未查到，等待后重试
            time.sleep(delay)
            delay = min(delay * 2, 1024)
        else:
            delay = 2
            retry_count = 0
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
    cursor.execute("SELECT location, api_source, timestamp FROM ip_cache WHERE ip = ?", (ip,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        location, api_source, timestamp = row
        if time.time() - timestamp < CACHE_TTL:
            return (location, api_source, timestamp)
    return None

def save_location(ip: str, location: str, api_source: str):
    """保存IP属地到缓存"""
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT OR REPLACE INTO ip_cache (ip, location, api_source, timestamp) VALUES (?, ?, ?, ?)",
        (ip, location, api_source, int(time.time()))
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
        save_location(ip, location, _api_name)
    return location or "查询失败"

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
            item["api_source"] = cached[1]
            item["status"] = "done"
        else:
            item["location"] = "待查询"
            item["api_source"] = ""
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
            "retry": str(query_status.get("retry", 0)),
            "next_retry": str(round(query_status.get("next_retry", 0), 1)),
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
