# 构建与发布工作流

> **[📖 English](build.md)**

## 📋 概述

CI/CD 流水线由 **commit 信息中的关键词** 驱动。推送到 `master` 分支时，只需在 commit message 中包含对应关键词，GitHub Actions 会自动完成后续工作。

## 🔑 关键词

| Commit 信息中的关键词 | 构建 Docker | 推送到 DockerHub | 推送到 GitHub Container Registry |
|----------------------|:---:|:---:|:---:|
| `build action` | ✅ | ❌ | ❌ |
| `build publish` | ✅ | ✅ | ✅ |

> **说明:** Pull Request 始终会触发构建（不会发布）。

## 🚀 用法示例

```bash
# ============================================================
# 单个关键词
# ============================================================

# 仅构建，验证编译
git commit --allow-empty -m "ci: test build (build action)"

# 构建 + 推送到 DockerHub 和 GHCR
git commit -m "release: v0.1.0 (build publish)"

# ============================================================
# 常规 commit（不需要构建和发布）
# ============================================================

# 仅更新文档
git commit -m "docs: update README"

# 修复 bug
git commit -m "fix: resolve database connection issue"

# 添加新功能
git commit -m "feat: add new API endpoint"
```

## 🏗️ 构建目标

| 平台 | 基础镜像 | 说明 |
|------|----------|------|
| Linux | Debian bookworm-slim | 轻量级 Go 运行时 |

## 📦 流水线阶段

```
check ──→ build ──→ publish
  │         │           │
  │         │           ├─ DockerHub: 推送到 vincentzyu/nginx-report
  │         │           │
  │         │           └─ GHCR: 推送到 ghcr.io/vincentzyu/nginx-report
  │         │
  │         └─ 编译 Go 程序
  │            构建 Docker 镜像（不上传）
  │
  └─→ sync-gitee（与 check 并行，每次 push 触发）
       镜像代码到 Gitee
```

## 🔧 环境配置

### DockerHub

在 DockerHub 设置 Access Tokens：
1. 登录 [DockerHub](https://hub.docker.com)
2. 进入 Account Settings → Security → New Access Token
3. 创建后保存用户名和密码

### GitHub Secrets

在仓库 Settings → Secrets and variables → Actions 中配置：

| Secret 名称 | 说明 |
|------------|------|
| `DOCKERHUB_USERNAME` | DockerHub 用户名 |
| `DOCKERHUB_TOKEN` | DockerHub Access Token |
| `GHCR_TOKEN` | GitHub Token（自动提供 `${{ secrets.GITHUB_TOKEN }}`）|

## 🚢 镜像标签

| 触发条件 | 标签 |
|----------|------|
| push 到 master | `latest`, `sha-{commit_sha}` |
| pull request | `pr-{pr_number}` |
| tag | `tag-{tag_name}` |

## 🐳 使用示例

```bash
# 拉取最新镜像
docker pull vincentzyu233/nginx-report:latest

# 运行容器
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

## 📋 检查 CI 状态

1. 打开仓库 GitHub Actions 页面
2. 查看最新 workflow run
3. 检查各步骤状态

## 🔄 更新镜像

```bash
# 重新构建并发布
git commit --allow-empty -m "ci: rebuild (build publish)"
git push
```