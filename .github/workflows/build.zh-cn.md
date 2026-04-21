![nginx-report](https://socialify.git.ci/VincentZyuApps/nginx-report/image?custom_language=Dockerfile&description=1&font=Raleway&forks=1&issues=1&language=1&logo=https%3A%2F%2Ficon.icepanel.io%2FTechnology%2Fsvg%2FGitHub-Actions.svg&name=1&owner=1&pattern=Circuit+Board&pulls=1&stargazers=1&theme=Light)

[English](./build.md) | [中文](./build.zh-cn.md)

# Build and Publish 工作流

此工作流用于构建并发布 Docker 镜像到 Docker Hub 和 GitHub Container Registry。

## 触发条件

工作流在以下情况运行：
- 推送到 `master` 或 `main` 分支
- 向 `master` 或 `main` 分支发起 Pull Request
- 通过 `workflow_dispatch` 手动触发

## Commit 信息规范

**只有 commit 信息包含 `build action` 或 `build publish` 时才会触发完整构建。**

否则工作流将跳过构建并显示：
```
✗ Commit message does not contain build trigger
   Skipping build (commit: abc1234)
```

### 合法的 Commit 信息示例（将触发构建）

```bash
git commit -m "fix: build action to update Dockerfile"
git commit -m "chore: build publish release v2.0"
```

### 非法的 Commit 信息（将跳过构建）

```bash
git commit -m "feat: add new feature"
git commit -m "update readme"
git commit -m "fix typo"
```

## 流水线阶段

### 阶段一：检查 Commit 信息

验证 commit 信息是否包含必需的触发关键词。

- **运行环境：** `ubuntu-latest`
- **输出：** `should_build` (布尔值)

### 阶段二：构建 Docker 镜像

编译 Go 程序并构建 Docker 镜像。

- **运行环境：** `ubuntu-latest`
- **依赖：** Go 1.21, GCC

**执行步骤：**
1. 检出代码
2. 配置 Go 1.21
3. 安装 GCC（用于 CGO/SQLite 编译）
4. 下载 Go 依赖
5. 使用 `CGO_ENABLED=1` 构建二进制文件
6. 验证构建输出
7. 登录 Docker Hub
8. 登录 GitHub Container Registry
9. 生成版本标签
10. 构建并推送 Docker 镜像

**Docker 镜像列表：**

| 仓库 | 镜像 | 标签 |
|------|------|------|
| Docker Hub | `vincentzyu233/nginx-report` | `latest`, `<version>` |
| GHCR | `ghcr.io/vincentzyaapps/nginx-report` | `latest`, `<version>` |

**版本标签格式：**
```
<提交哈希前7位>-<时间戳>
示例：abc1234-20260421-193000
```

### 阶段三：发布到 Docker Hub

更新 Docker Hub 仓库描述。

- **运行环境：** `ubuntu-latest`

**执行步骤：**
1. 检出代码
2. 使用 `peter-evans/dockerhub-description@v3` 更新 Docker Hub README

## 必需的 Secrets

在 GitHub 仓库设置中配置以下密钥：

| 密钥 | 说明 |
|------|------|
| `DOCKERHUB_USERNAME` | Docker Hub 账户用户名 |
| `DOCKERHUB_TOKEN` | Docker Hub 访问令牌 |

## 权限

- `contents: read`
- `packages: write`

## 注意事项

- Go 二进制使用 `CGO_ENABLED=1` 编译以支持 SQLite
- 需要安装 GCC 以编译 SQLite CGO 绑定
- 每次构建都会推送 `latest` 和带版本号的标签
