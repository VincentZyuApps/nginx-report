# IP查询API列表（按优先级排序）
# 每次查询从第一个开始，失败自动切换下一个

import json
import urllib.request

# 当前使用的API名称（用于显示）
current_api_name = ""

IP_APIS = [
    {
        "name": "pconline",
        "url": "https://whois.pconline.com.cn/ipJson.jsp?ip={ip}&json=true",
        "parse": lambda d: f"{d.get('pro', '')} {d.get('city', '')} [{d.get('addr', '').split()[0] if d.get('addr') else ''}]" if d.get("pro") else None,
    },
    {
        "name": "geojs",
        "url": "https://get.geojs.io/v1/ip/geo/{ip}",
        "parse": lambda d: f"{d.get('country', '')} {d.get('region', '')} {d.get('city', '')} [{d.get('isp', '')}]" if d.get("country") else None,
    },
    {
        "name": "ip-api",
        "url": "http://demo.ip-api.com/json/{ip}?fields=66842623&lang=zh-CN",
        "parse": lambda d: f"{d.get('country', '')} {d.get('regionName', '')} {d.get('city', '')} [{d.get('isp', '')}]" if d.get("status") == "success" else None,
    },
    {
        "name": "ip-sb",
        "url": "https://api.ip.sb/geoip/{ip}",
        "parse": lambda d: f"{d.get('country', '')} {d.get('region', '')} {d.get('city', '')} [{d.get('isp', '')}]" if d.get("country") else None,
    },
    {
        "name": "ipapi-is",
        "url": "https://api.ipapi.is/json/{ip}",
        "parse": lambda d: f"{d.get('country', '')} {d.get('region', '')} {d.get('city', '')} [{d.get('isp', '')}]" if d.get("country") else None,
    },
    {
        "name": "freeipapi",
        "url": "https://freeipapi.com/api/json/{ip}",
        "parse": lambda d: f"{d.get('countryCode', '')} {d.get('region', '')} {d.get('city', '')} [{d.get('isp', '')}]" if d.get("countryCode") else None,
    },
    {
        "name": "ipwhois",
        "url": "https://ipwhois.app/json/?format=json&ip={ip}",
        "parse": lambda d: f"{d.get('country', '')} {d.get('region', '')} {d.get('city', '')} [{d.get('isp', '')}]" if d.get("country") else None,
    },
    {
        "name": "ipncgy",
        "url": "https://ip.nc.gy/json?ip={ip}",
        "parse": lambda d: f"{d.get('country', '')} {d.get('region', '')} {d.get('city', '')} [{d.get('isp', '')}]" if d.get("country") else None,
    },
    {
        "name": "ip2location",
        "url": "https://api.ip2location.io/?ip={ip}",
        "parse": lambda d: f"{d.get('country_name', '')} {d.get('region_name', '')} {d.get('city_name', '')} [{d.get('as', '')}]" if d.get("country_name") else None,
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
    """使用多个API查询IP属地，失败自动切换"""
    global _api_index, current_api_name
    
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
        
        # 当前API失败，切换下一个
        switch_api()
    
    return None