from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from collections import Counter
import uvicorn
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

LOG_FILE = "/var/log/nginx/access.log"

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
        
    # 终极兼容写法：request 必须是第一个位置参数
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
    uvicorn.run(app, host="0.0.0.0", port=60418)
