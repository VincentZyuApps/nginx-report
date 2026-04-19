# Build and Publish Workflow

> **[📖 简体中文](build.zh-cn.md)**

## 📋 Overview

CI/CD pipeline is driven by **keywords in commit messages**. When pushing to `master` branch, include the keywords in commit message and GitHub Actions will do the rest.

## 🔑 Keywords

| Commit Keyword | Build Docker | Push to DockerHub | Push to GitHub Packages |
|---------------|:---:|:---:|:---:|
| `build action` | ✅ | ❌ | ❌ |
| `build publish` | ✅ | ✅ | ✅ |

> **Note:** Pull Requests always trigger build only (no publish).

## 🚀 Usage Examples

```bash
# ============================================================
# Single Keyword
# ============================================================

# Build only, verify compilation
git commit --allow-empty -m "ci: test build (build action)"

# Build + push to DockerHub and GitHub Packages
git commit -m "release: v0.1.0 (build publish)"

# ============================================================
# Regular commit (no build or publish)
# ============================================================

# Update docs only
git commit -m "docs: update README"

# Fix bug
git commit -m "fix: resolve database connection issue"

# Add new feature
git commit -m "feat: add new API endpoint"
```

## 🏗️ Build Targets

| Platform | Base Image | Description |
|----------|-----------|-------------|
| Linux | Debian bookworm-slim | Lightweight Go runtime |

## 📦 Pipeline Stages

```
check ──→ build ──→ publish
  │         │           │
  │         │           ├─ DockerHub: push to vincentzyu/nginx-report
  │         │           │
  │         │           └─ GitHub Packages: push to ghcr.io/vincentzyu/nginx-report
  │         │
  │         └─ Compile Go program
  │            Build Docker image (without push)
  │
  └─→ sync-gitee (parallel with check, triggers on every push)
       Mirror code to Gitee
```

## 🔧 Environment Setup

### DockerHub

Create Access Token on DockerHub:
1. Login [DockerHub](https://hub.docker.com)
2. Go to Account Settings → Security → New Access Token
3. Save username and password after creation

### GitHub Secrets

Configure in repository Settings → Secrets and variables → Actions:

| Secret Name | Description |
|------------|------------|
| `DOCKERHUB_USERNAME` | DockerHub username |
| `DOCKERHUB_TOKEN` | DockerHub Access Token |

> **Note:** GitHub Packages uses `${{ secrets.GITHUB_TOKEN }}` automatically.

## 🚢 Image Tags

| Trigger | Tags |
|---------|------|
| push to master | `latest`, `sha-{commit_sha}` |
| pull request | `pr-{pr_number}` |
| tag | `tag-{tag_name}` |

## 🐳 Usage Examples

```bash
# Pull latest image
docker pull vincentzyu233/nginx-report:latest

# Run container
docker run -d -p 60419:8080 -v /path/to/data.db:/app/data.db vincentzyu233/nginx-report:latest
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
      - ./data.db:/app/data.db
    restart: unless-stopped
```

## 📋 Check CI Status

1. Open repository GitHub Actions page
2. Check latest workflow run
3. View each step status

## 🔄 Update Image

```bash
# Rebuild and publish
git commit --allow-empty -m "ci: rebuild (build publish)"
git push
```