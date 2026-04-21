![nginx-report](https://socialify.git.ci/VincentZyuApps/nginx-report/image?custom_language=Go&description=1&font=Raleway&forks=1&issues=1&language=1&logo=https%3A%2F%2Fupload.wikimedia.org%2Fwikipedia%2Fcommons%2Fthumb%2Fc%2Fc3%2FPython-logo-notext.svg%2F120px-Python-logo-notext.svg.png%3F_%3D20250701090410&name=1&owner=1&pattern=Circuit+Board&pulls=1&stargazers=1&theme=Light)

[English](./readme.md) | [中文](./readme.zh-cn.md)

# Nginx Access Statistics

Nginx access log statistics tool that queries visitor IP locations and displays a leaderboard.

[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/VincentZyuApps/nginx-report)
[![Gitee](https://img.shields.io/badge/Gitee-C71D23?style=for-the-badge&logo=gitee&logoColor=white)](https://gitee.com/vincent-zyu/nginx-report)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://hub.docker.com/r/vincentzyu233/nginx-report)

[![Docker Image Pulls](https://img.shields.io/docker/pulls/vincentzyu233/nginx-report?style=for-the-badge)](https://hub.docker.com/r/vincentzyu233/nginx-report)
[![Docker Image Build and Publish](https://github.com/VincentZyuApps/nginx-report/actions/workflows/build.yml/badge.svg)](https://github.com/VincentZyuApps/nginx-report/actions/workflows/build.yml)

## Python Version

### Quick Start

```bash
# clone repo
git clone https://github.com/VincentZyuApps/nginx-report
# or from Gitee mirror
git clone https://gitee.com/vincent-zyu/nginx-report.git
cd py

# create virtual environment using uv (recommended)
# https://docs.astral.sh/uv/getting-started/installation/
# https://gitee.com/wangnov/uv-custom/releases
uv venv --python 3.13
# install dependencies
uv pip install -r requirements.txt
# run
uv run python main.py
```

Access the service at `http://{your_ip}:60418`

### Configuration

Edit paths in `main.py`:

```python
LOG_DIR = "/var/log/nginx"  # Nginx log directory (supports access.log and rotated logs)
DB_FILE = "data/data.db"    # SQLite database path
```

---

## Go Version

### Docker

```bash
# basic run (data will be lost when container is removed)
docker run -d --name nginx-report -p 60419:60419 -v /var/log/nginx:/var/log/nginx:ro vincentzyu233/nginx-report:latest
# 大陆用户可以使用 DaoCloud 镜像:
docker run -d --name nginx-report -p 60419:60419 -v /var/log/nginx:/var/log/nginx:ro m.daocloud.io/docker.io/vincentzyu233/nginx-report:latest 
# with data persistence
docker run -d --name nginx-report -p 60419:60419 -v /var/log/nginx:/var/log/nginx:ro -v ./data:/app/data vincentzyu233/nginx-report:latest
```

then open `http://{your_ip}:60419` to access webui~

> **Update to latest image:**
> ```bash
> docker pull vincentzyu233/nginx-report:latest
> docker stop nginx-report && docker rm nginx-report
> # docker rmi vincentzyu233/nginx-report:latest # optional: delete old image
> # rerun, use same arg as above
> docker run -d --name nginx-report -p 60419:60419 -v /var/log/nginx:/var/log/nginx:ro vincentzyu233/nginx-report:latest
> docker image prune -f
> ```

> **manually configure docker image registry mirror:**
> ```bash
> nano /etc/docker/daemon.json
> ```
> ```json
> { "registry-mirrors": ["https://docker.1ms.run"] }
> ```
> ```bash
> systemctl restart docker
> ```

### Environment Variables

> For Docker, use `-v` to persist data instead of environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `data/data.db` | SQLite database path (container internal path) |

### Build from Source

```bash
cd go

# download dependencies
go mod download

# build
CGO_ENABLED=1 go build -o server .

# run
./server
# with data persistence, pass env variable:
DB_PATH=/custom/path/data.db ./server
```

### Docker Compose

```bash
nano ./docker-compose.yml
```

```yaml
version: '3'
services:
  nginx-report:
    container_name: nginx-report
    image: vincentzyu233/nginx-report:latest
    ports:
      - "60419:60419"
    volumes:
      - /var/log/nginx:/var/log/nginx:ro
      # - ./data:/app/data  # uncomment to persist database
    restart: unless-stopped
```

```bash
# start
docker compose up -d
# view logs
docker compose logs -f
```

> **Update to latest image:**
> ```bash
> # update to latest image: pull latest, then recreate & start container with new config/image (if updated)
> docker compose pull && docker compose up -d
> docker image prune -f
> ```

---

## Preview

## WebUI Preview
![doc/preview-images/nginx-report-py-version-preview.png](doc/preview-images/nginx-report-py-version-preview.png)
