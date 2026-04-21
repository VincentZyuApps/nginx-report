import json
import re
import time
import urllib.request

COUNTRY_MAP = {
    "China": "中国", "United States": "美国", "United Kingdom": "英国",
    "Russia": "俄罗斯", "Germany": "德国", "Japan": "日本",
    "South Korea": "韩国", "Singapore": "新加坡", "Hong Kong": "香港",
    "Taiwan": "台湾", "France": "法国", "India": "印度",
    "Canada": "加拿大", "Australia": "澳大利亚", "Brazil": "巴西",
    "Netherlands": "荷兰", "Ireland": "爱尔兰", "Switzerland": "瑞士",
    "South Africa": "南非",
}

ISP_KEYWORDS = ["电信", "联通", "移动", "铁通", "教育网", "科技网"]

def _isp(s):
    if not s:
        return ""
    for k in ISP_KEYWORDS:
        if k in s:
            return k
    return s.strip()[:15]

def _loc(country, region, city, isp=""):
    parts = []
    cn = COUNTRY_MAP.get(country, country)
    if cn == "中国":
        if region:
            parts.append(region)
    elif cn:
        parts.append(cn)
    if region and region != country and cn != "中国":
        parts.append(region)
    if city:
        parts.append(city)
    result = " ".join(parts)
    isp_txt = _isp(isp)
    if isp_txt:
        result += f" [{isp_txt}]"
    return result.strip()

def _get(url, encoding="utf-8", timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode(encoding)

def fetch_cip(ip):
    try:
        text = _get(f"http://www.cip.cc/{ip}")
        addr = re.search(r"地址\s*:\s*(.+)", text)
        isp  = re.search(r"运营商\s*:\s*(.+)", text)
        if addr:
            result = addr.group(1).strip()
            isp_txt = _isp(isp.group(1).strip() if isp else "")
            if isp_txt:
                result += f" [{isp_txt}]"
            return result
    except Exception as e:
        print(f"[cip] {e}")
    return None

def fetch_baidu(ip):
    try:
        data = json.loads(_get(f"https://opendata.baidu.com/api.php?co=&resource_id=6006&oe=utf8&query={ip}"))
        if data.get("status") == "0" and data.get("data"):
            loc = data["data"][0].get("location", "")
            parts = loc.split()
            if parts:
                result = parts[0]
                if len(parts) > 1:
                    isp_txt = _isp(parts[1])
                    if isp_txt:
                        result += f" [{isp_txt}]"
                return result
    except Exception as e:
        print(f"[baidu] {e}")
    return None

def fetch_ipsb(ip):
    try:
        data = json.loads(_get(f"https://api.ip.sb/geoip/{ip}"))
        if data.get("country"):
            return _loc(data.get("country",""), data.get("region",""), data.get("city",""), data.get("isp",""))
    except Exception as e:
        print(f"[ip.sb] {e}")
    return None

def fetch_pconline(ip):
    try:
        data = json.loads(_get(f"https://whois.pconline.com.cn/ipJson.jsp?ip={ip}&json=true", encoding="gbk"))
        if data.get("pro"):
            return f"{data.get('pro','')} {data.get('city','')}".strip()
    except Exception as e:
        print(f"[pconline] {e}")
    return None

def fetch_ipwhois(ip):
    try:
        data = json.loads(_get(f"https://ipwhois.app/json/{ip}"))
        if data.get("country"):
            return _loc(data.get("country",""), data.get("region",""), data.get("city",""), data.get("isp",""))
    except Exception as e:
        print(f"[ipwhois] {e}")
    return None

def fetch_ipapi(ip):
    try:
        data = json.loads(_get(f"http://demo.ip-api.com/json/{ip}?fields=66842623&lang=zh-CN"))
        if data.get("status") == "success":
            return _loc(data.get("country",""), data.get("regionName",""), data.get("city",""), data.get("isp",""))
    except Exception as e:
        print(f"[ip-api] {e}")
    return None

# (name, func, rate_limited)
APIS = [
    ("cip",     fetch_cip,     False),
    ("baidu",   fetch_baidu,   False),
    ("ip.sb",   fetch_ipsb,    False),
    ("pconline",fetch_pconline,False),
    ("ipwhois", fetch_ipwhois, False),
    ("ip-api",  fetch_ipapi,   True),
]

_api_index = 0

def fetch_location_with_source(ip: str):
    """依次尝试所有API，返回 (location, api_name)，全部失败返回 (None, "")"""
    global _api_index
    for i in range(len(APIS)):
        idx = (_api_index + i) % len(APIS)
        name, func, rate_limited = APIS[idx]
        location = func(ip)
        if location:
            _api_index = idx
            if rate_limited:
                time.sleep(1.5)
            return (location, name)
    return (None, "")

def get_current_api():
    return APIS[_api_index][0]
