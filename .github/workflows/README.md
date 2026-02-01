# GitHub Actions Workflows

This directory contains CI/CD workflows for the Digital Actors project.

## Workflows

### ci.yml - Continuous Integration

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Jobs:**

1. **test** - Run tests and generate coverage
   - Sets up Python 3.12
   - Installs dependencies from `pyproject.toml`
   - Runs ruff code quality checks
   - Runs pytest with coverage reporting
   - Uploads coverage to Codecov
   - Stores coverage artifacts for 30 days

2. **lint** - Code quality checks
   - Runs ruff linter
   - Outputs results in GitHub format (inline annotations)

**Requirements:**
- No secrets required (uses mock API keys for testing)
- Optional: `CODECOV_TOKEN` secret for coverage uploads

**Expected Runtime:** 2-5 minutes

### docker.yml - Docker Build and Publish

**Triggers:**
- Push to `main` branch
- Version tags (e.g., `v1.0.0`)
- Pull requests to `main` (build only, no push)

**Jobs:**

1. **build** - Build and publish Docker images
   - Builds multi-platform images (amd64, arm64)
   - Pushes to GitHub Container Registry (ghcr.io)
   - Creates attestations for supply chain security
   - Caches layers for faster builds

**Image Tags:**
- `latest` - Latest main branch build
- `<branch>-<sha>` - Branch with commit SHA (e.g., `main-a1b2c3d`)
- `v<version>` - Semantic version tags (e.g., `v1.0.0`)

**Requirements:**
- Uses `GITHUB_TOKEN` (automatically provided)
- Permissions: `contents: read`, `packages: write`

**Expected Runtime:** 5-15 minutes

## Setup Instructions

### 1. Enable Actions

GitHub Actions are enabled by default for public repositories. For private repositories:

1. Go to repository Settings > Actions > General
2. Enable "Allow all actions and reusable workflows"

### 2. Configure Codecov (Optional)

For coverage reports:

1. Sign up at https://codecov.io/
2. Add your repository
3. Copy the upload token
4. Add as repository secret: `CODECOV_TOKEN`

### 3. Pull Docker Images

Images are published to GitHub Container Registry:

```bash
# Pull latest
docker pull ghcr.io/johnny-z13/digital-actors:latest

# Pull specific version
docker pull ghcr.io/johnny-z13/digital-actors:v1.0.0

# Pull branch build
docker pull ghcr.io/johnny-z13/digital-actors:main-a1b2c3d
```

## Local Testing

Test workflows locally before pushing:

### Test CI Jobs

```bash
# Install dependencies
pip install -e .[dev]

# Run ruff checks
ruff check .
ruff format --check .

# Run tests with coverage
pytest --cov --cov-report=xml --cov-report=term
```

### Test Docker Build

```bash
# Build image
docker build -t digital-actors:test .

# Run container
docker run -p 8888:8888 \
  -e ANTHROPIC_API_KEY=your-key \
  -e ELEVENLABS_API_KEY=your-key \
  digital-actors:test
```

## Monitoring

### Check Workflow Status

- View in GitHub UI: Actions tab
- Status badges in README.md show current status
- Email notifications on workflow failures (configurable in GitHub settings)

### View Logs

1. Go to repository > Actions
2. Click on a workflow run
3. Click on a job to view detailed logs

### Coverage Reports

- View on Codecov: https://codecov.io/gh/johnny-z13/digital-actors
- Download artifacts from Actions tab (HTML reports)
- Local HTML reports: `open htmlcov/index.html`

## Troubleshooting

### Workflow Fails on Dependency Installation

Check that `pyproject.toml` has all required dependencies:
```bash
pip install -e .[dev]
```

### Docker Build Fails

Common issues:
- Missing files (check `.dockerignore`)
- Build context too large (optimize `.dockerignore`)
- Platform compatibility (test locally with `docker buildx`)

### Tests Fail in CI but Pass Locally

Possible causes:
- Environment-specific differences (paths, OS)
- Missing environment variables
- Race conditions in async tests

Use same Python version locally (3.12) and mock API keys:
```bash
export ANTHROPIC_API_KEY=mock-key-for-testing
export ELEVENLABS_API_KEY=mock-key-for-testing
pytest
```

## Security

### Secrets

Never commit secrets to workflows. Use GitHub Secrets:
- Settings > Secrets and variables > Actions
- Reference in workflow: `${{ secrets.SECRET_NAME }}`

### Permissions

Workflows use minimal required permissions:
- `contents: read` - Read repository code
- `packages: write` - Push Docker images
- `GITHUB_TOKEN` - Automatically provided, scoped to repository

### Dependencies

Dependencies are pinned in `pyproject.toml` with version constraints.
Regular updates via Dependabot (configured separately).

## Future Enhancements

Potential additions:
- [ ] Deploy workflow for production environments
- [ ] Performance testing workflow
- [ ] Security scanning (SAST, dependency audit)
- [ ] Automated release creation
- [ ] Integration test workflow with test database
- [ ] Notification integrations (Slack, Discord)
