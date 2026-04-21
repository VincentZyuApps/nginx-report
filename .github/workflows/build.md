# Build and Publish Workflow

This workflow builds and publishes Docker images to Docker Hub and GitHub Container Registry.

## Triggers

The workflow runs on:
- Push to `master` or `main` branches
- Pull requests to `master` or `main` branches
- Manual trigger via `workflow_dispatch`

## Commit Message Convention

**Only commits containing `build action` or `build publish` in the message will trigger a full build.**

Otherwise, the workflow will skip the build and display:
```
✗ Commit message does not contain build trigger
   Skipping build (commit: abc1234)
```

### Examples

**Valid commit messages (will trigger build):**
```
git commit -m "fix: build action to update Dockerfile"
git commit -m "chore: build publish release v2.0"
```

**Invalid commit messages (will skip build):**
```
git commit -m "feat: add new feature"
git commit -m "update readme"
git commit -m "fix typo"
```

## Pipeline Stages

### Stage 1: Check Commit Message

Validates that the commit message contains the required trigger keyword.

- **Runner:** `ubuntu-latest`
- **Output:** `should_build` (boolean)

### Stage 2: Build Docker Image

Compiles the Go application and builds Docker images.

- **Runner:** `ubuntu-latest`
- **Dependencies:** Go 1.21, GCC

**Steps:**
1. Checkout code
2. Set up Go 1.21
3. Install GCC (required for CGO/SQLite)
4. Download Go dependencies
5. Build binary with `CGO_ENABLED=1`
6. Verify build output
7. Login to Docker Hub
8. Login to GitHub Container Registry
9. Generate version tag
10. Build and push Docker images

**Docker Images:**

| Registry | Image | Tags |
|----------|-------|------|
| Docker Hub | `vincentzyu233/nginx-report` | `latest`, `<version>` |
| GHCR | `ghcr.io/vincentzyaapps/nginx-report` | `latest`, `<version>` |

**Version Tag Format:**
```
<commit-sha-7chars>-<timestamp>
Example: abc1234-20260421-193000
```

### Stage 3: Publish to Docker Hub

Updates the Docker Hub repository description.

- **Runner:** `ubuntu-latest`

**Steps:**
1. Checkout code
2. Update Docker Hub README using `peter-evans/dockerhub-description@v3`

## Required Secrets

Configure these secrets in GitHub repository settings:

| Secret | Description |
|--------|-------------|
| `DOCKERHUB_USERNAME` | Docker Hub account username |
| `DOCKERHUB_TOKEN` | Docker Hub access token |

## Permissions

- `contents: read`
- `packages: write`

## Notes

- The Go binary is built with `CGO_ENABLED=1` to support SQLite
- GCC must be installed for the SQLite CGO bindings
- Both `latest` and versioned tags are pushed on each build
