# IP查询API列表（按优先级排序）
# 每次查询从第一个开始，失败自动切换下一个

import json
import time
import urllib.request

# 当前使用的API名称（用于显示）
current_api_name = ""

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


def normalize_location(country: str, region: str, city: str, isp: str) -> str:
    """统一格式化位置信息"""
    parts = []
    
    # 统一国家名为中文
    if country:
        country = COUNTRY_MAP.get(country, country)
        if country == "中国" and region:
            # 中国省份用中文
            parts.append(region)
        else:
            parts.append(country)
    
    if region and region != country:
        parts.append(region)
    
    if city:
        parts.append(city)
    
    # ISP只显示电信运营商
    ispTxt = ""
    if isp:
        isp = isp.strip()
        # 提取主要运营商
        for name in ["电信", "联通", "移动", "铁通", "教育网", "科技网"]:
            if name in isp:
                ispTxt = name
                break
        if not ispTxt:
            # 截取前15字符
            ispTxt = isp[:15]
    
    result = " ".join(parts)
    if ispTxt:
        result += f" [{ispTxt}]"
    
    return result.strip()


IP_APIS = [
    {
        "name": "pconline",
        "url": "https://whois.pconline.com.cn/ipJson.jsp?ip={ip}&json=true",
        "parse": lambda d: normalize_location("中国", d.get("pro", ""), d.get("city", ""), d.get("addr", "").split()[0] if d.get("addr") else "") if d.get("pro") else None,
    },
    {
        "name": "ip-api",
        "url": "http://demo.ip-api.com/json/{ip}?fields=66842623&lang=zh-CN",
        "parse": lambda d: normalize_location(d.get("country", ""), d.get("regionName", ""), d.get("city", ""), d.get("isp", "")) if d.get("status") == "success" else None,
    },
    {
        "name": "ipapi-is",
        "url": "https://api.ipapi.is/json/{ip}",
        "parse": lambda d: normalize_location(d.get("country", ""), d.get("region", ""), d.get("city", ""), d.get("isp", "")) if d.get("country") else None,
    },
    {
        "name": "freeipapi",
        "url": "https://freeipapi.com/api/json/{ip}",
        "parse": lambda d: normalize_location(d.get("countryCode", ""), d.get("region", ""), d.get("city", ""), d.get("isp", "")) if d.get("countryCode") else None,
    },
    {
        "name": "ipwhois",
        "url": "https://ipwhois.app/json/?format=json&ip={ip}",
        "parse": lambda d: normalize_location(d.get("country", ""), d.get("region", ""), d.get("city", ""), d.get("isp", "")) if d.get("country") else None,
    },
    {
        "name": "ipncgy",
        "url": "https://ip.nc.gy/json?ip={ip}",
        "parse": lambda d: normalize_location(d.get("country", ""), d.get("region", ""), d.get("city", ""), d.get("isp", "")) if d.get("country") else None,
    },
    {
        "name": "ip2location",
        "url": "https://api.ip2location.io/?ip={ip}",
        "parse": lambda d: normalize_location(d.get("country_name", ""), d.get("region_name", ""), d.get("city_name", ""), d.get("as", "")) if d.get("country_name") else None,
    },
]

# 当前使用的API索引
_api_index = 0


def get_api():
    """获取当前API配置"""
    global _api_index
    return IP_APIS[_api_index % len(IP_APIS)]


def switch_api():
    """切换到下一个API"""
    global _api_index
    _api_index = (_api_index + 1) % len(IP_APIS)
    return IP_APIS[_api_index]["name"]


def fetch_location(ip: str) -> str:
    """使用多个API查询IP属地，失败自动切换，重试间隔指数增长"""
    global _api_index, current_api_name
    
    delay = 2  # 初始重试间隔2秒
    
    for _ in range(len(IP_APIS)):
        api = get_api()
        current_api_name = api["name"]
        try:
            url = api["url"].format(ip=ip)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8"))
                result = api["parse"](data)
                if result and result.strip():
                    return result
        except Exception as e:
            print(f"[{api['name']}] Error: {e}")
        
        # 等待后切换下一个API（指数退避）
        time.sleep(delay)
        delay = min(delay * 2, 1024)  # 最大1024秒
        switch_api()
    
    return None