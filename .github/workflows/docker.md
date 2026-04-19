# Docker Build and Publish

> **[📖 简体中文](docker.zh-cn.md)**

## 📋 Overview

Docker images are automatically built and published to Docker Hub and GitHub Container Registry (ghcr.io) via GitHub Actions.

## 🔑 Trigger Keywords

| Commit Keyword | Build Image | Push to DockerHub | Push to ghcr.io |
|---------------|:---:|:---:|:---:|
| `build action` | ✅ | ❌ | ❌ |
| `build publish` | ✅ | ✅ | ✅ |

**Notes:**
- PR always builds but doesn't publish
- `build action` = verify build only (CI test)
- `build publish` = build + push to both registries

## 🚀 Usage Examples

```bash
# Verify build only (PR or CI test)
git commit --allow-empty -m "ci: test build (build action)"

# Build and publish image
git commit --allow-empty -m "ci: publish image (build publish)"

# Regular commit (no build)
git commit -m "fix: update docs"

## 🏗️ Build Flow

```
checkout → buildx → login → build/push → manifest
```

1. **checkout** - Checkout code
2. **buildx** - Set up Docker Buildx
3. **login** - Login to Docker Hub and ghcr.io
4. **build/push** - Multi-stage build Go + Vue, push to registry
5. **manifest** - Generate image metadata (tags)

## 📦 Image Tags

| Trigger | Docker Hub | ghcr.io |
|---------|-----------|--------|
| `master` branch | `nginx-report:latest` | `ghcr.io/{org}/nginx-report:latest` |
| tag `v1.2.3` | `nginx-report:v1.2.3` | `ghcr.io/{org}/nginx-report:v1.2.3` |
| | `nginx-report:v1.2` | `ghcr.io/{org}/nginx-report:v1.2` |
| | `nginx-report:v1` | `ghcr.io/{org}/nginx-report:v1` |

## ⚙️ Configure Secrets

Add these secrets in GitHub repo → Settings → Secrets and variables → Actions:

### Docker Hub

| Secret Name | Description | How to Get |
|-------------|------|----------|
| `DOCKERHUB_USERNAME` | Docker Hub username | Register at [docker.io](https://docker.io) |
| `DOCKERHUB_TOKEN` | Access Token | Docker Hub → Account Settings → Security → New Access Token |

### GitHub Packages

| Secret Name | Description |
|-------------|------|
| `GITHUB_TOKEN` | Auto-provided, no configuration needed |

> **Note:** `GITHUB_TOKEN` is automatically provided by GitHub Actions with package push permissions.

## 🚀 Usage

```bash
# Pull from Docker Hub
docker run -v /var/log/nginx/access.log:/app/log/access.log -p 60418:60418 nginx-report

# Pull from ghcr.io
docker run -v /var/log/nginx/access.log:/app/log/access.log -p 60418:60418 ghcr.io/vincentzyu/nginx-report

# Custom build
cd go
docker build -t my-nginx-report .
docker run -v /var/log/nginx/access.log:/app/log/access.log -p 60418:60418 my-nginx-report
```

## 🔗 Links

- [Docker Hub](https://docker.io)
- [GitHub Container Registry](https://github.com/features/packages)
- [docker/build-push-action](https://github.com/docker/build-push-action)
- [docker/metadata-action](https://github.com/docker/metadata-action)