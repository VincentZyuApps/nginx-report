# Docker 构建与发布

> **[📖 English](docker.md)**

## 📋 概述

Docker 镜像通过 GitHub Actions 自动构建并发布到 Docker Hub 和 GitHub Container Registry (ghcr.io)。

## 🔑 触发关键词

| Commit 关键词 | 构建镜像 | 推送到 DockerHub | 推送到 ghcr.io |
|---------------|:---:|:---:|:---:|
| `build action` | ✅ | ❌ | ❌ |
| `build publish` | ✅ | ✅ | ✅ |

**说明：**
- PR 始终只构建，不发布
- `build action` = 仅验证构建（CI测试用）
- `build publish` = 构建 + 推送到双仓库

## 🚀 使用示例

```bash
# 仅验证构建（PR 或 CI 测试）
git commit --allow-empty -m "ci: test build (build action)"

# 构建并发布镜像
git commit --allow-empty -m "ci: publish image (build publish)"

# 普通提交（不构建）
git commit -m "fix: update docs"
```

## 🏗️ 构建流程

```
checkout → buildx → login → build/push → manifest
```

1. **checkout** - 检出代码
2. **buildx** - 设置 Docker Buildx
3. **login** - 登录 Docker Hub 和 ghcr.io
4. **build/push** - 多阶段构建 Go + Vue，推送到仓库
5. **manifest** - 生成镜像元数据（标签）

## 📦 镜像标签

| 触发 | Docker Hub | ghcr.io |
|------|-----------|--------|
| `build publish` | `nginx-report:latest` | `ghcr.io/{org}/nginx-report:latest` |

## ⚙️ 配置 Secrets

在 GitHub 仓库设置中添加以下 secrets：

### Docker Hub

| Secret 名称 | 说明 | 获取方式 |
|-------------|------|----------|
| `DOCKERHUB_USERNAME` | Docker Hub 用户名 | [docker.io](https://docker.io) 注册 |
| `DOCKERHUB_TOKEN` | Access Token | Docker Hub → Account Settings → Security → New Access Token |

### GitHub Packages

| Secret 名称 | 说明 |
|-------------|------|
| `GITHUB_TOKEN` | 自动提供，无需配置 |

> **注意:** `GITHUB_TOKEN` 是 GitHub Actions 自动提供的默认 token，权限已包含推送包的权限。

## 🚀 使用方式

```bash
# 从 Docker Hub 拉取
docker run -v /var/log/nginx/access.log:/app/log/access.log -p 60418:60418 nginx-report

# 从 ghcr.io 拉取
docker run -v /var/log/nginx/access.log:/app/log/access.log -p 60418:60418 ghcr.io/vincentzyuapps/nginx-report

# 自定义构建
cd go
docker build -t my-nginx-report .
docker run -v /var/log/nginx/access.log:/app/log/access.log -p 60418:60418 my-nginx-report
```

## 📝 Docker Hub 配置步骤

1. 登录 [Docker Hub](https://docker.io)
2. **Account Settings** → **Security** → **New Access Token**
3. 描述填写 `GitHub Actions`，权限选择 **Read, Write, Delete**
4. 复制生成的 token
5. 打开 GitHub 仓库 → **Settings** → **Secrets and variables** → **Actions**
6. 添加 `DOCKERHUB_USERNAME`（你的 Docker Hub 用户名）
7. 添加 `DOCKERHUB_TOKEN`（刚才生成的 token）

## 🔗 相关链接

- [Docker Hub](https://docker.io)
- [GitHub Container Registry](https://github.com/features/packages)
- [docker/build-push-action](https://github.com/docker/build-push-action)
- [docker/metadata-action](https://github.com/docker/metadata-action)# Docker 构建与发布

> **[📖 English](docker.md)**

## 📋 概述

Docker 镜像通过 GitHub Actions 自动构建并发布到 Docker Hub 和 GitHub Container Registry (ghcr.io)。

## 🔑 触发关键词

| Commit 关键词 | 构建镜像 | 推送到 DockerHub | 推送到 ghcr.io |
|---------------|:---:|:---:|:---:|
| `build action` | ✅ | ❌ | ❌ |
| `build publish` | ✅ | ✅ | ✅ |

**说明：**
- PR 始终只构建，不发布
- `build action` = 仅验证构建（CI测试用）
- `build publish` = 构建 + 推送到双仓库

## 🚀 使用示例

```bash
# 仅验证构建（PR 或 CI 测试）
git commit --allow-empty -m "ci: test build (build action)"

# 构建并发布镜像
git commit --allow-empty -m "ci: publish image (build publish)"

# 普通提交（不构建）
git commit -m "fix: update docs"

## 🏗️ 构建流程

```
checkout → buildx → login → build/push → manifest
```

1. **checkout** - 检出代码
2. **buildx** - 设置 Docker Buildx
3. **login** - 登录 Docker Hub 和 ghcr.io
4. **build/push** - 多阶段构建 Go + Vue，推送到仓库
5. **manifest** - 生成镜像元数据（标签）

## 📦 镜像标签

| 触发 | Docker Hub | ghcr.io |
|------|-----------|--------|
| `master` 分支 | `nginx-report:latest` | `ghcr.io/{org}/nginx-report:latest` |
| tag `v1.2.3` | `nginx-report:v1.2.3` | `ghcr.io/{org}/nginx-report:v1.2.3` |
| | `nginx-report:v1.2` | `ghcr.io/{org}/nginx-report:v1.2` |
| | `nginx-report:v1` | `ghcr.io/{org}/nginx-report:v1` |

## ⚙️ 配置 Secrets

在 GitHub 仓库设置中添加以下 secrets：

### Docker Hub

| Secret 名称 | 说明 | 获取方式 |
|-------------|------|----------|
| `DOCKERHUB_USERNAME` | Docker Hub 用户名 | [docker.io](https://docker.io) 注册 |
| `DOCKERHUB_TOKEN` | Access Token | Docker Hub → Account Settings → Security → New Access Token |

### GitHub Packages

| Secret 名称 | 说明 |
|-------------|------|
| `GITHUB_TOKEN` | 自动提供，无需配置 |

> **注意:** `GITHUB_TOKEN` 是 GitHub Actions 自动提供的默认 token，权限已包含推送包的权限。

## 🚀 使用方式

```bash
# 从 Docker Hub 拉取
docker run -v /var/log/nginx/access.log:/app/log/access.log -p 60418:60418 nginx-report

# 从 ghcr.io 拉取
docker run -v /var/log/nginx/access.log:/app/log/access.log -p 60418:60418 ghcr.io/vincentzyu/nginx-report

# 自定义构建
cd go
docker build -t my-nginx-report .
docker run -v /var/log/nginx/access.log:/app/log/access.log -p 60418:60418 my-nginx-report
```

## 📝 Docker Hub 配置步骤

1. 登录 [Docker Hub](https://docker.io)
2. **Account Settings** → **Security** → **New Access Token**
3. 描述填写 `GitHub Actions`，权限选择 **Read, Write, Delete**
4. 复制生成的 token
5. 打开 GitHub 仓库 → **Settings** → **Secrets and variables** → **Actions**
6. 添加 `DOCKERHUB_USERNAME`（你的 Docker Hub 用户名）
7. 添加 `DOCKERHUB_TOKEN`（刚才生成的 token）

## 🔗 相关链接

- [Docker Hub](https://docker.io)
- [GitHub Container Registry](https://github.com/features/packages)
- [docker/build-push-action](https://github.com/docker/build-push-action)
- [docker/metadata-action](https://github.com/docker/metadata-action)