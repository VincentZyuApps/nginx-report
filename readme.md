# Nginx Access Statistics

Nginx access log statistics tool that queries visitor IP locations and displays a leaderboard.

[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/VincentZyuApps/nginx-report)
[![Gitee](https://img.shields.io/badge/Gitee-C71D23?style=for-the-badge&logo=gitee&logoColor=white)](https://gitee.com/vincent-zyu/nginx-report)
![Build and Publish](https://github.com/VincentZyuApps/nginx-report/workflows/Github-Action-CI-Docker-Image-Build-and-Publish/badge.svg)

## Python Version

### Quick Start

```bash
# clone repo
git clone https://github.com/VincentZyuApps/nginx-report
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
docker pull vincentzyu233/nginx-report:latest
docker run -d -p 60419:60419 -v /var/log/nginx:/var/log/nginx:ro vincentzyu233/nginx-report:latest
```

Access at http://localhost:60419

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `data/data.db` | SQLite database path |

### Build from Source

```bash
cd go

# download dependencies
go mod download

# build
CGO_ENABLED=1 go build -o server .

# run
./server
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
    restart: unless-stopped
```

---

## Preview

## Python Version WebUI Preview
![doc/preview-images/nginx-report-py-version-preview.png](doc/preview-images/nginx-report-py-version-preview.png)
