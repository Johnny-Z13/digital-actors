# Docker Deployment Guide

This guide explains how to build and deploy the Digital Actors application using Docker.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Building the Image](#building-the-image)
- [Running in Production](#running-in-production)
- [Running in Development](#running-in-development)
- [Environment Variables](#environment-variables)
- [Volumes and Persistence](#volumes-and-persistence)
- [Health Checks](#health-checks)
- [Troubleshooting](#troubleshooting)
- [Image Optimization](#image-optimization)

## Quick Start

### Production Deployment

```bash
# 1. Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys

# 2. Build and start the application
docker-compose up -d

# 3. View logs
docker-compose logs -f

# 4. Access the application
# Open http://localhost:8888 in your browser
```

### Development Mode

```bash
# Start with hot-reload enabled
docker-compose --profile dev up

# The dev service mounts your source code, so changes are reflected immediately
```

## Prerequisites

- Docker Engine 20.10 or later
- Docker Compose 2.0 or later (comes with Docker Desktop)
- At least 2GB of free disk space for the image
- Valid API keys for:
  - Anthropic Claude API (required)
  - ElevenLabs API (required for voice synthesis)
  - OpenAI API (optional)
  - Google API (optional)

## Building the Image

### Multi-Stage Build Architecture

The Dockerfile uses a multi-stage build to optimize image size:

1. **Builder Stage**: Installs build dependencies and compiles Python packages
2. **Production Stage**: Contains only runtime dependencies and application code

### Build the Image Manually

```bash
# Build with default tag
docker build -t digital-actors:latest .

# Build with specific tag
docker build -t digital-actors:v1.0.0 .

# Build with build arguments (if needed)
docker build --build-arg PYTHON_VERSION=3.12 -t digital-actors:latest .
```

### Image Size Optimization

The production image is optimized through:

- Multi-stage builds (separates build and runtime dependencies)
- Python 3.12-slim base image (minimal OS footprint)
- `.dockerignore` file (excludes unnecessary files)
- Non-root user for security
- No cache for pip installations
- Virtual environment isolation

Expected image size: ~800-1200MB (includes ML dependencies)

## Running in Production

### Using Docker Compose (Recommended)

```bash
# Start the application
docker-compose up -d

# Stop the application
docker-compose down

# Restart the application
docker-compose restart

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### Using Docker Run

```bash
docker run -d \
  --name digital-actors \
  -p 8888:8888 \
  -e ANTHROPIC_API_KEY=your-key-here \
  -e ELEVENLABS_API_KEY=your-key-here \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/voicecache:/app/voicecache \
  -v $(pwd)/audio:/app/audio \
  digital-actors:latest
```

## Running in Development

Development mode mounts your source code into the container for hot-reload:

```bash
# Start development service (includes source code mounting)
docker-compose --profile dev up

# Build and start in one command
docker-compose --profile dev up --build

# Run with specific service
docker-compose run --rm digital-actors-dev python -m pytest
```

### Development Features

- Source code mounted as volume (changes reflected immediately)
- Debug logging enabled (LOG_LEVEL=DEBUG)
- Console-formatted logs (easier to read during development)
- All Python cache directories excluded from mount

### Running Tests in Docker

```bash
# Run all tests
docker-compose run --rm digital-actors-dev python -m pytest

# Run with coverage
docker-compose run --rm digital-actors-dev python -m pytest --cov=. --cov-report=html

# Run specific test file
docker-compose run --rm digital-actors-dev python -m pytest tests/test_player_memory.py

# Run with verbose output
docker-compose run --rm digital-actors-dev python -m pytest -v
```

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models | `sk-ant-...` |
| `ELEVENLABS_API_KEY` | ElevenLabs API key for TTS | `your-elevenlabs-key` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | WebSocket server port | `8888` |
| `OPENAI_API_KEY` | OpenAI API key (if using GPT models) | - |
| `GOOGLE_API_KEY` | Google API key (if using Gemini models) | - |
| `ELEVENLABS_MODEL` | ElevenLabs TTS model | `eleven_turbo_v2_5` |
| `ELEVENLABS_PRESERVE_AUDIO_TAGS` | Preserve audio tags like [laughs] | `true` |
| `SENTRY_DSN` | Sentry error tracking DSN | - |
| `SENTRY_ENVIRONMENT` | Sentry environment name | `production` |
| `SENTRY_TRACES_SAMPLE_RATE` | Sentry performance monitoring rate | `0.1` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `LOG_FORMAT` | Log format (json/console) | `json` |

### Setting Environment Variables

#### Using .env File (Recommended)

```bash
# 1. Copy example environment file
cp .env.example .env

# 2. Edit .env with your API keys
nano .env

# 3. Docker Compose automatically loads .env
docker-compose up -d
```

#### Using Docker Run

```bash
docker run -d \
  --env-file .env \
  -p 8888:8888 \
  digital-actors:latest
```

## Volumes and Persistence

The application uses three persistent volumes:

### Volume Mappings

| Container Path | Host Path | Purpose |
|----------------|-----------|---------|
| `/app/data` | `./data` | SQLite database (player memory, sessions) |
| `/app/voicecache` | `./voicecache` | Cached TTS audio files |
| `/app/audio` | `./audio` | Audio assets |

### Data Persistence

```bash
# Backup data
docker-compose down
tar -czf backup-$(date +%Y%m%d).tar.gz data/ voicecache/

# Restore data
tar -xzf backup-20260130.tar.gz

# Clear caches (not database)
rm -rf voicecache/*
```

### Database Management

```bash
# Access SQLite database
docker-compose exec digital-actors sqlite3 /app/data/digital_actors.db

# Backup database
docker-compose exec digital-actors sqlite3 /app/data/digital_actors.db ".backup /app/data/backup.db"

# Copy database out of container
docker cp digital-actors:/app/data/digital_actors.db ./backup/
```

## Health Checks

### Health Check Endpoint

The application exposes a `/health` endpoint for container orchestration:

```bash
# Check health manually
curl http://localhost:8888/health

# Response
{
  "status": "healthy",
  "service": "digital-actors",
  "timestamp": 1738281234.567
}
```

### Docker Health Status

```bash
# View health status
docker-compose ps

# Check health in docker inspect
docker inspect digital-actors | grep Health -A 10

# View health check logs
docker inspect digital-actors --format='{{json .State.Health}}' | jq
```

### Health Check Configuration

The Dockerfile includes a HEALTHCHECK instruction:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8888}/health || exit 1
```

- **Interval**: Check every 30 seconds
- **Timeout**: Wait up to 10 seconds for response
- **Start Period**: Allow 40 seconds for application startup
- **Retries**: Mark unhealthy after 3 consecutive failures

## Troubleshooting

### Container Won't Start

```bash
# Check container logs
docker-compose logs digital-actors

# Check if port is already in use
lsof -i :8888

# Check if API keys are set
docker-compose exec digital-actors env | grep API_KEY
```

### Permission Issues

```bash
# Fix data directory permissions
sudo chown -R $USER:$USER data/ voicecache/ audio/

# Or run with proper user ID
docker-compose exec --user $(id -u):$(id -g) digital-actors bash
```

### Out of Memory

```bash
# Increase Docker memory limit (Docker Desktop > Settings > Resources)
# Or limit container memory
docker-compose run --memory="2g" digital-actors
```

### Health Check Failing

```bash
# Test health endpoint manually
docker-compose exec digital-actors curl -f http://localhost:8888/health

# Check application logs
docker-compose logs -f digital-actors

# Verify port is listening
docker-compose exec digital-actors netstat -tlnp
```

### Development Hot-Reload Not Working

```bash
# Ensure you're using the dev profile
docker-compose --profile dev up

# Check if source code is mounted
docker-compose exec digital-actors-dev ls -la /app

# Rebuild if needed
docker-compose --profile dev up --build
```

### Database Locked Error

```bash
# Stop all containers
docker-compose down

# Remove SQLite lock files
rm -f data/*.db-journal

# Restart
docker-compose up -d
```

## Image Optimization

### Check Image Size

```bash
# View image sizes
docker images digital-actors

# Analyze image layers
docker history digital-actors:latest

# Use dive for detailed analysis
dive digital-actors:latest
```

### Optimization Techniques Used

1. **Multi-stage builds**: Separate build and runtime environments
2. **Slim base image**: `python:3.12-slim` (vs full `python:3.12`)
3. **Virtual environment**: Isolated dependency installation
4. **`.dockerignore`**: Exclude unnecessary files from build context
5. **No pip cache**: `--no-cache-dir` flag during installation
6. **Minimal runtime deps**: Only `ca-certificates` and `curl`
7. **Non-root user**: Security best practice with minimal overhead

### Further Optimization Ideas

```dockerfile
# Use Python Alpine (smaller but may require more build dependencies)
FROM python:3.12-alpine

# Use distroless for even smaller images (no shell)
FROM gcr.io/distroless/python3-debian12

# Multi-architecture builds
docker buildx build --platform linux/amd64,linux/arm64 -t digital-actors:latest .
```

## Advanced Configuration

### Custom Dockerfile

If you need to customize the Dockerfile:

```dockerfile
# Example: Add additional system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*
```

### Docker Compose Override

Create `docker-compose.override.yml` for local customization:

```yaml
version: '3.8'

services:
  digital-actors:
    environment:
      - LOG_LEVEL=DEBUG
    ports:
      - "9999:8888"
```

### Production Deployment with Traefik

```yaml
services:
  digital-actors:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.digital-actors.rule=Host(`actors.example.com`)"
      - "traefik.http.services.digital-actors.loadbalancer.server.port=8888"
```

## Security Best Practices

1. **Never commit `.env` file**: Contains sensitive API keys
2. **Use secrets management**: For production, use Docker secrets or vault
3. **Regular updates**: Keep base image and dependencies updated
4. **Non-root user**: Already configured in Dockerfile
5. **Read-only filesystem**: Consider adding `read_only: true` to compose
6. **Network isolation**: Use custom networks to isolate services

## Support

For issues, questions, or contributions:

- GitHub Issues: [Report a bug](https://github.com/your-repo/digital-actors/issues)
- Documentation: [README.md](README.md)
- Discord: [Community Server](https://discord.gg/your-invite)

## License

See [LICENSE](LICENSE) file for details.
