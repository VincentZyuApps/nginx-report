# IP查询API模块
# 支持多种API，按优先级自动切换

import json
import re
import time
import urllib.error
import urllib.request

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

def normalize_location(country: str, region: str, city: str, isp: str = "") -> str:
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


# ==================== 各API实现 ====================

def fetch_from_ipapi(ip: str):
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


def fetch_from_pconline(ip: str):
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


def fetch_from_ipsb(ip: str):
    """ip.sb - 免费无限制，返回: 国家/省/城市/ISP"""
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


def fetch_from_ipwhois(ip: str):
    """ipwhois.app - 返回: 国家/省/城市/ISP"""
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


def fetch_from_cip(ip: str):
    """cip.cc - 返回: 国家/省/城市/ISP (文本格式)"""
    try:
        url = f"http://www.cip.cc/{ip}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            text = response.read().decode("utf-8")
            # 解析 "地址    : 中国 福建 厦门"
            addr_match = re.search(r"地址\s*:\s*(.+)", text)
            # 解析 "运营商  : 移动"
            isp_match = re.search(r"运营商\s*:\s*(.+)", text)
            
            if addr_match:
                addr = addr_match.group(1).strip()
                isp = isp_match.group(1).strip() if isp_match else ""
                
                # 简化ISP
                ispTxt = ""
                if isp:
                    for name in ["电信", "联通", "移动", "铁通", "教育网", "科技网"]:
                        if name in isp:
                            ispTxt = name
                            break
                    if not ispTxt:
                        ispTxt = isp[:15]
                
                result = addr
                if ispTxt:
                    result += f" [{ispTxt}]"
                return result
    except Exception as e:
        print(f"[cip] Error: {e}")
    return None


# ==================== API列表 ====================
# (名称, 函数, 是否有速率限制)
APIS = [
    ("ip-api", fetch_from_ipapi, True),      # 45次/分钟
    ("cip", fetch_from_cip, False),
    ("pconline", fetch_from_pconline, False),
    ("ip.sb", fetch_from_ipsb, False),
    ("ipwhois", fetch_from_ipwhois, False),
]


# 当前使用的API索引
_api_index = 0
_api_name = "ip-api"


def fetch_location(ip: str):
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


def get_current_api():
    """获取当前使用的API名称"""
    return _api_name
