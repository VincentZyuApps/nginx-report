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

# create virtual environment
uv venv --python 3.13

# install dependencies
uv pip install -r requirements.txt

# run
uv run python main.py
```

Access the service at `http://ip:60418`

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
docker run -d -p 60419:60419 -v /var/log/nginx:/var/log/nginx:ro vincentzyu233/nginx-report:latest
# 大陆用户可以使用 DaoCloud 镜像:
docker run -d -p 60419:60419 -v /var/log/nginx:/var/log/nginx:ro m.daocloud.io/docker.io/vincentzyu233/nginx-report:latest 
# with data persistence
docker run -d -p 60419:60419 -v /var/log/nginx:/var/log/nginx:ro -v ./data:/app/data vincentzyu233/nginx-report:latest
```

then open `http://localhost:60419` to access webui~

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
# start
docker compose up -d

# view logs
docker compose logs -f
```

```yaml
version: '3'
services:
  nginx-report:
    image: vincentzyu233/nginx-report:latest
    ports:
      - "60419:60419"
    volumes:
      - /var/log/nginx:/var/log/nginx:ro
      # - ./data:/app/data  # uncomment to persist database
    restart: unless-stopped
```

---

## Preview

## Python Version WebUI Preview
![doc/preview-images/nginx-report-py-version-preview.png](doc/preview-images/nginx-report-py-version-preview.png)
