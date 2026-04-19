# Nginx 访问统计

Nginx access log 统计工具，查询访客 IP 属地并展示排行榜。

![Build and Publish](https://github.com/VincentZyuApps/nginx-report/workflows/Build%20and%20Publish/badge.svg)

## Python 版本

### 快速开始

```bash
# clone repo
git clone https://github.com/VincentZyuApps/nginx-report
# 或者从gitee
git clone https://gitee.com/vincent-zyu/nginx-report.git
cd py

# 创建虚拟环境
uv venv --python 3.13

# 安装依赖
uv pip install -r requirements.txt

# 运行
uv run python main.py
```

服务启动后访问 `http://ip:60418`

### 配置

修改 `main.py` 中的路径：

```python
LOG_FILE = "/var/log/nginx/access.log"  # Nginx 日志路径
DB_FILE = "data/data.db"                 # SQLite 数据库路径
```

---

## Go 版本

### Docker 运行

```bash
docker pull vincentzyu233/nginx-report:latest
docker run -d -p 60419:8080 -v /path/to/access.log:/var/log/nginx/access.log vincentzyu233/nginx-report:latest
```

访问 http://localhost:60419

### 本地编译

```bash
cd go

# 下载依赖
go mod download

# 编译
CGO_ENABLED=1 go build -o server .

# 运行
./server
```

### Docker Compose

```yaml
version: '3'
services:
  nginx-report:
    image: vincentzyu233/nginx-report:latest
    ports:
      - "60419:8080"
    volumes:
      - /var/log/nginx/access.log:/var/log/nginx/access.log
    restart: unless-stopped
```

---

## 效果预览

<img src="https://raw.githubusercontent.com/VincentZyuApps/nginx-report/master/screenshot.png" width="800">

