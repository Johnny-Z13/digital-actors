# Deployment Guide

This guide covers production deployment of the Digital Actors system, including configuration, security, monitoring, and troubleshooting.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start Deployment](#quick-start-deployment)
- [Production Configuration Checklist](#production-configuration-checklist)
- [Deployment Options](#deployment-options)
  - [Docker Compose (Recommended)](#docker-compose-recommended)
  - [Manual Python Deployment](#manual-python-deployment)
  - [Cloud Providers](#cloud-providers)
- [Environment Variables Reference](#environment-variables-reference)
- [Database Setup](#database-setup)
- [TLS/SSL Configuration](#tlsssl-configuration)
- [Reverse Proxy Setup](#reverse-proxy-setup)
- [Security Best Practices](#security-best-practices)
- [Monitoring and Logging](#monitoring-and-logging)
- [Backup and Disaster Recovery](#backup-and-disaster-recovery)
- [Troubleshooting](#troubleshooting)
- [Scaling Considerations](#scaling-considerations)

---

## Prerequisites

Before deploying Digital Actors, ensure you have:

### System Requirements

- **Operating System**: Linux (Ubuntu 22.04+ recommended), macOS, or Windows with WSL2
- **Python**: 3.12 or higher
- **Memory**: Minimum 2GB RAM, 4GB recommended
- **Storage**: Minimum 1GB free disk space
- **Network**: Outbound HTTPS access to API providers

### API Keys

You must obtain API keys from the following providers:

1. **Anthropic API Key** (Required)
   - Sign up at: https://console.anthropic.com/
   - Used for: Claude AI models (dialogue generation, decision making)
   - Cost: Pay-per-use, ~$0.001 per dialogue interaction with Haiku model

2. **ElevenLabs API Key** (Required for voice synthesis)
   - Sign up at: https://elevenlabs.io/
   - Used for: Text-to-speech (TTS) for character voices
   - Cost: Free tier available, then pay-per-character

3. **Sentry DSN** (Optional, recommended for production)
   - Sign up at: https://sentry.io/
   - Used for: Error tracking and monitoring
   - Cost: Free tier available

### Software Dependencies

For Docker deployment:
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

For manual deployment:
- **Python**: 3.12+
- **pip** or **uv** (Python package manager)
- **curl** (for health checks)

---

## Quick Start Deployment

The fastest way to get Digital Actors running in production:

### Using Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/Johnny-Z13/digital-actors.git
cd digital-actors

# 2. Create .env file with your API keys
cp .env.example .env
nano .env  # Add your API keys

# 3. Start the application
docker-compose up -d

# 4. Check logs
docker-compose logs -f

# 5. Access the application
# Open http://localhost:8888
```

The application will be available at `http://localhost:8888` within 40 seconds.

---

## Production Configuration Checklist

Before deploying to production, complete this checklist:

- [ ] Set all required environment variables (see `.env.example`)
- [ ] Configure `SENTRY_DSN` for error tracking
- [ ] Set `SENTRY_ENVIRONMENT=production`
- [ ] Configure structured logging: `LOG_FORMAT_JSON=true`
- [ ] Set appropriate log level: `LOG_LEVEL=INFO`
- [ ] Set up TLS/SSL certificate (Let's Encrypt recommended)
- [ ] Configure reverse proxy (nginx or Caddy)
- [ ] Enable firewall (allow only ports 80, 443, and 22)
- [ ] Set up automated backups for `/app/data` directory
- [ ] Configure log rotation for container logs
- [ ] Test health check endpoint: `curl http://localhost:8888/health`
- [ ] Document API key rotation procedures
- [ ] Set up monitoring alerts (CPU, memory, disk, errors)
- [ ] Configure rate limiting in reverse proxy
- [ ] Test disaster recovery procedures
- [ ] Review and harden security settings

---

## Deployment Options

### Docker Compose (Recommended)

Docker Compose is the recommended deployment method for production. It provides:
- Automated container orchestration
- Built-in health checks
- Persistent data volumes
- Easy rollback and updates

#### Production Deployment

```bash
# 1. Prepare environment
cp .env.example .env
nano .env  # Configure all variables

# 2. Deploy
docker-compose up -d

# 3. Verify deployment
docker-compose ps
docker-compose logs -f digital-actors

# 4. Test health check
curl http://localhost:8888/health
```

#### Development Mode with Hot Reload

```bash
# Start development service with source code mounting
docker-compose --profile dev up digital-actors-dev

# Code changes are automatically reloaded
```

#### Updating the Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart containers
docker-compose build --no-cache
docker-compose up -d

# Verify update
docker-compose logs -f
```

#### Stopping the Application

```bash
# Stop gracefully
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

---

### Manual Python Deployment

For environments without Docker, deploy directly with Python:

#### Installation

```bash
# 1. Clone repository
git clone https://github.com/Johnny-Z13/digital-actors.git
cd digital-actors

# 2. Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -e .

# For Kokoro TTS support (optional):
pip install -e ".[kokoro]"

# 4. Configure environment
cp .env.example .env
nano .env  # Add your API keys
```

#### Running with systemd

Create a systemd service for automatic startup and management:

```bash
# Create service file
sudo nano /etc/systemd/system/digital-actors.service
```

```ini
[Unit]
Description=Digital Actors AI Narrative System
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/digital-actors
Environment="PATH=/opt/digital-actors/.venv/bin"
EnvironmentFile=/opt/digital-actors/.env
ExecStart=/opt/digital-actors/.venv/bin/python web_server.py
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/digital-actors/data /opt/digital-actors/voicecache /opt/digital-actors/audio

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable digital-actors
sudo systemctl start digital-actors

# Check status
sudo systemctl status digital-actors

# View logs
sudo journalctl -u digital-actors -f
```

#### Manual Startup Script

Alternatively, use the provided startup script:

```bash
# Make script executable
chmod +x start-web.sh

# Run in foreground
./start-web.sh

# Run in background with nohup
nohup ./start-web.sh > logs/digital-actors.log 2>&1 &
```

---

### Cloud Providers

#### AWS Elastic Container Service (ECS)

Deploy Digital Actors on AWS ECS with Fargate for serverless container management.

**Prerequisites:**
- AWS CLI installed and configured
- ECR repository created for Docker images

**Steps:**

```bash
# 1. Authenticate with ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# 2. Tag and push image
docker tag digital-actors:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/digital-actors:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/digital-actors:latest

# 3. Create ECS task definition (task-definition.json)
{
  "family": "digital-actors",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "digital-actors",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/digital-actors:latest",
      "portMappings": [
        {
          "containerPort": 8888,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "PORT", "value": "8888"},
        {"name": "LOG_LEVEL", "value": "INFO"},
        {"name": "LOG_FORMAT_JSON", "value": "true"},
        {"name": "SENTRY_ENVIRONMENT", "value": "production"}
      ],
      "secrets": [
        {"name": "ANTHROPIC_API_KEY", "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:anthropic-api-key"},
        {"name": "ELEVENLABS_API_KEY", "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:elevenlabs-api-key"},
        {"name": "SENTRY_DSN", "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:sentry-dsn"}
      ],
      "mountPoints": [
        {
          "sourceVolume": "data",
          "containerPath": "/app/data"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/digital-actors",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "volumes": [
    {
      "name": "data",
      "efsVolumeConfiguration": {
        "fileSystemId": "fs-xxxxxxxx",
        "transitEncryption": "ENABLED"
      }
    }
  ]
}

# 4. Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 5. Create ECS service
aws ecs create-service \
  --cluster digital-actors-cluster \
  --service-name digital-actors-service \
  --task-definition digital-actors \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxxx],securityGroups=[sg-xxxxxx],assignPublicIp=ENABLED}"

# 6. Configure Application Load Balancer (ALB) for WebSocket support
# - Create target group with protocol HTTP, port 8888
# - Enable stickiness (session affinity)
# - Set health check path to /health
# - Attach ALB to ECS service
```

**Storage:**
- Use Amazon EFS for persistent SQLite database and cache storage
- Mount EFS volume to `/app/data`, `/app/voicecache`, and `/app/audio`

**Monitoring:**
- CloudWatch Logs for structured JSON logs
- CloudWatch Container Insights for metrics
- X-Ray for distributed tracing (optional)

---

#### Google Cloud Platform (Cloud Run)

Deploy Digital Actors on GCP Cloud Run for fully managed serverless containers.

**Prerequisites:**
- gcloud CLI installed and configured
- GCP project created

**Steps:**

```bash
# 1. Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/<project-id>/digital-actors

# 2. Deploy to Cloud Run
gcloud run deploy digital-actors \
  --image gcr.io/<project-id>/digital-actors \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8888 \
  --memory 2Gi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 10 \
  --timeout 3600 \
  --set-env-vars "PORT=8888,LOG_LEVEL=INFO,LOG_FORMAT_JSON=true,SENTRY_ENVIRONMENT=production" \
  --set-secrets "ANTHROPIC_API_KEY=anthropic-api-key:latest,ELEVENLABS_API_KEY=elevenlabs-api-key:latest,SENTRY_DSN=sentry-dsn:latest"

# 3. Get service URL
gcloud run services describe digital-actors --region us-central1 --format 'value(status.url)'
```

**Storage:**
- Use Cloud Filestore for persistent database (NFS mount)
- Or use Cloud SQL for PostgreSQL (requires code changes)
- Cloud Storage for backups

**Monitoring:**
- Cloud Logging for structured logs
- Cloud Monitoring for metrics and alerts
- Cloud Trace for request tracing

**Important Notes:**
- Cloud Run may restart containers frequently; ensure database handles concurrent access
- WebSocket connections may be limited to 60 minutes; implement reconnection logic
- Consider Cloud Run for Anthos for more control

---

#### Azure Container Instances (ACI)

Deploy Digital Actors on Azure Container Instances for simple container hosting.

**Prerequisites:**
- Azure CLI installed and configured
- Azure Container Registry (ACR) created

**Steps:**

```bash
# 1. Login to ACR
az acr login --name <registry-name>

# 2. Tag and push image
docker tag digital-actors:latest <registry-name>.azurecr.io/digital-actors:latest
docker push <registry-name>.azurecr.io/digital-actors:latest

# 3. Create Azure Key Vault for secrets
az keyvault create --name digital-actors-vault --resource-group digital-actors-rg --location eastus
az keyvault secret set --vault-name digital-actors-vault --name anthropic-api-key --value "<your-key>"
az keyvault secret set --vault-name digital-actors-vault --name elevenlabs-api-key --value "<your-key>"

# 4. Create container instance
az container create \
  --resource-group digital-actors-rg \
  --name digital-actors \
  --image <registry-name>.azurecr.io/digital-actors:latest \
  --registry-login-server <registry-name>.azurecr.io \
  --registry-username <username> \
  --registry-password <password> \
  --dns-name-label digital-actors \
  --ports 8888 \
  --cpu 1 \
  --memory 2 \
  --environment-variables \
    PORT=8888 \
    LOG_LEVEL=INFO \
    LOG_FORMAT_JSON=true \
    SENTRY_ENVIRONMENT=production \
  --secure-environment-variables \
    ANTHROPIC_API_KEY=<from-keyvault> \
    ELEVENLABS_API_KEY=<from-keyvault> \
  --azure-file-volume-account-name <storage-account> \
  --azure-file-volume-account-key <storage-key> \
  --azure-file-volume-share-name digital-actors-data \
  --azure-file-volume-mount-path /app/data

# 5. Get container FQDN
az container show --resource-group digital-actors-rg --name digital-actors --query ipAddress.fqdn
```

**Storage:**
- Use Azure Files for persistent volumes
- Mount to `/app/data`, `/app/voicecache`, and `/app/audio`

**Monitoring:**
- Azure Monitor for logs and metrics
- Application Insights for detailed telemetry
- Log Analytics workspace for structured log queries

---

## Environment Variables Reference

All environment variables can be configured in the `.env` file or passed directly to containers.

See [.env.example](../.env.example) for a complete reference. Key variables:

### Required Variables

```bash
# Anthropic API Key (Required)
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# ElevenLabs API Key (Required for TTS)
ELEVENLABS_API_KEY=your-elevenlabs-api-key-here
```

### Server Configuration

```bash
# Server port (default: 8888 in Docker, 8080 for manual deployment)
PORT=8888
```

### Logging Configuration

```bash
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Log format: console (readable) or json (structured)
LOG_FORMAT_JSON=true

# Environment name (appears in logs and Sentry)
ENV=production
```

### Sentry Error Tracking (Optional but Recommended)

```bash
# Sentry DSN for error tracking
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Sentry environment (e.g., production, staging, development)
SENTRY_ENVIRONMENT=production

# Traces sample rate (0.0 to 1.0, default: 0.1 = 10%)
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### ElevenLabs Voice Configuration (Optional)

```bash
# Default TTS model
ELEVENLABS_MODEL=eleven_turbo_v2_5

# Preserve audio tags like [laughs], [sighs] for expressive voices
ELEVENLABS_PRESERVE_AUDIO_TAGS=true

# Custom voice IDs (optional overrides)
ELEVENLABS_VOICE_ENGINEER=pNInz6obpgDQGcFmaJgB
ELEVENLABS_VOICE_CAPTAIN_HALE=SOYHLrjzK2X1ezoPC6cr
ELEVENLABS_VOICE_MARA_VANE=21m00Tcm4TlvDq8ikWAM
ELEVENLABS_VOICE_WIZARD=VR6AewLTigWG4xSOukaG
ELEVENLABS_VOICE_DETECTIVE=ErXwobaYiN019PkySvjV
```

### Alternative LLM Providers (Optional)

```bash
# OpenAI API Key (if using OpenAI models)
OPENAI_API_KEY=your-openai-api-key-here

# Google API Key (if using Gemini models)
GOOGLE_API_KEY=your-google-api-key-here
```

---

## Database Setup

Digital Actors uses SQLite for player memory and session tracking. The database is automatically created on first run.

### Database Schema

The system creates the following tables automatically:

1. **players**: Player profiles and statistics
2. **sessions**: Player sessions and playtime tracking
3. **scene_attempts**: Individual scene attempt records
4. **personality_profiles**: Player personality traits
5. **relationships**: Player-character relationship tracking

### Database Location

Default database paths:

- **Docker**: `/app/data/player_memory.db`
- **Manual deployment**: `./data/player_memory.db`

### Initial Setup

No manual database initialization is required. The database is created automatically when the application starts:

```python
# Initialization happens in player_memory.py
# Tables are created with CREATE TABLE IF NOT EXISTS
```

### Database Migration

The current system does not require migrations. Schema changes are handled with `CREATE TABLE IF NOT EXISTS` for backward compatibility.

If you need to migrate data:

```bash
# Backup existing database
cp data/player_memory.db data/player_memory.db.backup

# Apply manual migrations (example)
sqlite3 data/player_memory.db < migrations/001_add_column.sql
```

### Database Maintenance

```bash
# Vacuum database to reclaim space
sqlite3 data/player_memory.db "VACUUM;"

# Check database integrity
sqlite3 data/player_memory.db "PRAGMA integrity_check;"

# View database size
ls -lh data/player_memory.db
```

---

## TLS/SSL Configuration

For production deployments, always use HTTPS with valid TLS certificates.

### Let's Encrypt with Certbot

Let's Encrypt provides free TLS certificates with automatic renewal.

```bash
# Install Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate (nginx must be running)
sudo certbot --nginx -d yourdomain.com

# Certificates are stored in: /etc/letsencrypt/live/yourdomain.com/
# - fullchain.pem: Certificate + intermediate certificates
# - privkey.pem: Private key

# Test automatic renewal
sudo certbot renew --dry-run
```

Certbot automatically configures nginx to use the certificate and sets up auto-renewal.

---

## Reverse Proxy Setup

Use a reverse proxy to handle TLS termination, rate limiting, and WebSocket upgrades.

### Nginx (Recommended)

Nginx provides excellent performance for WebSocket proxying.

**Installation:**

```bash
sudo apt-get update
sudo apt-get install nginx
```

**Configuration:**

Create `/etc/nginx/sites-available/digital-actors`:

```nginx
# Rate limiting zone
limit_req_zone $binary_remote_addr zone=digital_actors_limit:10m rate=10r/s;

# Upstream backend
upstream digital_actors_backend {
    server 127.0.0.1:8888;
    keepalive 64;
}

# HTTP redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com;

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com;

    # TLS configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    # Modern TLS configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;

    # HSTS (optional, uncomment after testing)
    # add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Rate limiting
    limit_req zone=digital_actors_limit burst=20 nodelay;

    # Timeouts for WebSocket connections
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;

    # Root location
    location / {
        proxy_pass http://digital_actors_backend;
        proxy_http_version 1.1;

        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Disable buffering for WebSocket
        proxy_buffering off;
    }

    # Health check endpoint (no rate limiting)
    location /health {
        proxy_pass http://digital_actors_backend/health;
        proxy_http_version 1.1;
        access_log off;
    }

    # Access and error logs
    access_log /var/log/nginx/digital-actors-access.log;
    error_log /var/log/nginx/digital-actors-error.log;
}
```

**Enable and restart nginx:**

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/digital-actors /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx

# Enable nginx at boot
sudo systemctl enable nginx
```

---

### Caddy (Alternative)

Caddy provides automatic HTTPS with simpler configuration.

**Installation:**

```bash
# Install Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

**Configuration:**

Create `/etc/caddy/Caddyfile`:

```caddyfile
yourdomain.com {
    # Automatic HTTPS with Let's Encrypt

    # Rate limiting
    rate_limit {
        zone digital_actors {
            key {remote_host}
            events 10
            window 1s
        }
    }

    # Reverse proxy to backend
    reverse_proxy localhost:8888 {
        # WebSocket support (automatic)

        # Timeouts
        transport http {
            read_timeout 3600s
            write_timeout 3600s
        }
    }

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    # Logging
    log {
        output file /var/log/caddy/digital-actors.log
        format json
    }
}
```

**Start Caddy:**

```bash
# Reload configuration
sudo systemctl reload caddy

# Enable at boot
sudo systemctl enable caddy
```

---

## Security Best Practices

### Firewall Configuration

Configure firewall to allow only necessary ports:

```bash
# Using UFW (Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (redirects to HTTPS)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Verify rules
sudo ufw status verbose
```

### API Key Security

1. **Never commit API keys to version control**
   - Add `.env` to `.gitignore`
   - Use environment variables or secrets managers

2. **Rotate API keys regularly**
   - Anthropic: Generate new key in console, update `.env`, restart service
   - ElevenLabs: Same process

3. **Use secrets managers for production**
   - AWS Secrets Manager
   - GCP Secret Manager
   - Azure Key Vault
   - HashiCorp Vault

4. **Monitor API key usage**
   - Check Anthropic dashboard for unusual usage
   - Set up billing alerts

### Container Security

```bash
# Run container as non-root user (already configured in Dockerfile)
USER appuser

# Use read-only root filesystem where possible
docker run --read-only --tmpfs /tmp digital-actors

# Limit container resources
docker run --memory=2g --cpus=1 digital-actors

# Scan images for vulnerabilities
docker scan digital-actors
```

### Rate Limiting

Implement rate limiting at the reverse proxy level (see nginx configuration above) to prevent:
- API abuse
- DDoS attacks
- Excessive LLM API costs

### WebSocket Authentication

The application implements session-based authentication for WebSocket connections:

1. Client requests session ID via `/api/session`
2. Server generates secure session token
3. Client authenticates WebSocket with token
4. Server validates token before accepting connection

Ensure `secrets.token_urlsafe()` is used for token generation (already implemented).

### Data Encryption

For sensitive deployments:

1. **Encrypt database at rest**
   ```bash
   # Use encrypted EBS volumes (AWS)
   # Use encrypted persistent disks (GCP)
   # Use Azure Disk Encryption (Azure)
   ```

2. **Enable TLS for all connections**
   - Already covered in reverse proxy setup

3. **Sanitize logs**
   - Never log API keys, tokens, or PII
   - Use structured logging to control log output

---

## Monitoring and Logging

### Structured Logging

Digital Actors uses structured JSON logging for production. See [LOGGING.md](LOGGING.md) for details.

**Enable JSON logging:**

```bash
# In .env file
LOG_FORMAT_JSON=true
LOG_LEVEL=INFO
ENV=production
```

**Log aggregation:**

Structured logs can be sent to:
- **Datadog**: Automatic JSON parsing
- **Splunk**: Use `_json` sourcetype
- **ELK Stack**: Elasticsearch recognizes `@timestamp` field
- **CloudWatch Logs**: Query with CloudWatch Insights

**Example CloudWatch Insights query:**

```sql
fields @timestamp, severity, event_type, session_id, response_time_ms
| filter event_type = "dialogue_generated"
| stats avg(response_time_ms) by bin(5m)
```

---

### Error Tracking with Sentry

Sentry provides real-time error tracking and performance monitoring.

**Setup:**

1. Create Sentry account at https://sentry.io/
2. Create new project (Python/Flask)
3. Copy DSN from project settings
4. Configure environment variables:

```bash
SENTRY_DSN=https://your-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% of transactions
```

5. Restart application

**Features:**

- Automatic exception capture
- Request/response context
- User session tracking
- Performance monitoring
- Release tracking
- Error alerting (email, Slack, PagerDuty)

**View errors:**

Visit Sentry dashboard to see:
- Error frequency and trends
- Stack traces with context
- Affected users
- Release versions

---

### Health Checks

The application provides a health check endpoint at `/health`:

```bash
# Check application health
curl http://localhost:8888/health

# Expected response: {"status": "ok"}
```

**Integration with orchestration:**

- **Docker Compose**: Built-in health check (see docker-compose.yml)
- **Kubernetes**: Configure liveness and readiness probes
- **AWS ECS**: Configure health check in task definition
- **Uptime monitoring**: Use UptimeRobot, Pingdom, or StatusCake

---

### Metrics and Monitoring

Digital Actors includes built-in Prometheus metrics for comprehensive monitoring. See [MONITORING.md](MONITORING.md) for complete setup and configuration details.

**Quick Start:**

```bash
# Access metrics endpoint
curl http://localhost:8888/metrics

# Start monitoring stack with Docker Compose
docker-compose -f docker-compose.yml up -d prometheus grafana
```

**Key metrics tracked:**
- Request count by scene/character
- Response time distribution (p50, p95, p99)
- LLM API latency by provider/model
- TTS processing time
- Error rate by type
- Active session count
- Database query time

**Monitoring tools:**
- **Prometheus + Grafana**: Built-in metrics and dashboard (see [MONITORING.md](MONITORING.md))
- **Datadog**: Full-stack monitoring with APM
- **New Relic**: Application performance monitoring
- **AWS CloudWatch**: Native AWS monitoring
- **GCP Cloud Monitoring**: Native GCP monitoring
- **Azure Monitor**: Native Azure monitoring

**System Metrics to monitor:**
- CPU usage (should be < 70%)
- Memory usage (should be < 80%)
- Disk usage (monitor `/app/data` growth)
- Network I/O (LLM API traffic)

---

### Alert Configuration

Set up alerts for critical conditions:

**Application Alerts:**
- Error rate > 5% (5 minutes)
- Response time > 10 seconds (95th percentile)
- WebSocket disconnection rate > 10%
- TTS failures > 10%

**System Alerts:**
- CPU usage > 80% (5 minutes)
- Memory usage > 90% (5 minutes)
- Disk usage > 85%
- Health check failures (3 consecutive)

**API Alerts:**
- Anthropic API errors > 5%
- ElevenLabs API errors > 5%
- API rate limit approaching

**Example alert (Sentry):**

```python
# Sentry automatically sends alerts for:
# - New errors
# - Error frequency spikes
# - Release regressions
```

---

## Backup and Disaster Recovery

### Backup Strategy

**What to back up:**

1. **Player database**: `/app/data/player_memory.db` (critical)
2. **Voice cache** (optional): `/app/voicecache/` (can be regenerated)
3. **Configuration**: `.env` file (store securely)
4. **Audio files** (optional): `/app/audio/` (if using local audio storage)

### Automated Backups

#### Docker Volume Backup

```bash
#!/bin/bash
# backup.sh - Automated backup script

BACKUP_DIR="/backups/digital-actors"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONTAINER_NAME="digital-actors"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
docker exec $CONTAINER_NAME sqlite3 /app/data/player_memory.db ".backup '/app/data/player_memory.db.backup'"
docker cp $CONTAINER_NAME:/app/data/player_memory.db.backup "$BACKUP_DIR/player_memory_$TIMESTAMP.db"

# Compress backup
gzip "$BACKUP_DIR/player_memory_$TIMESTAMP.db"

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "player_memory_*.db.gz" -mtime +30 -delete

# Upload to S3 (optional)
# aws s3 cp "$BACKUP_DIR/player_memory_$TIMESTAMP.db.gz" s3://my-backups/digital-actors/

echo "Backup completed: player_memory_$TIMESTAMP.db.gz"
```

**Schedule with cron:**

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /opt/digital-actors/backup.sh >> /var/log/digital-actors-backup.log 2>&1
```

#### Cloud Storage Backups

**AWS S3:**

```bash
# Install AWS CLI
sudo apt-get install awscli

# Configure credentials
aws configure

# Sync data directory to S3 daily
aws s3 sync /app/data s3://my-backups/digital-actors/data/ --delete
```

**GCP Cloud Storage:**

```bash
# Install gsutil
curl https://sdk.cloud.google.com | bash

# Sync to GCS
gsutil -m rsync -r /app/data gs://my-backups/digital-actors/data/
```

**Azure Blob Storage:**

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Upload backup
az storage blob upload \
  --account-name mystorageaccount \
  --container-name backups \
  --file /backups/player_memory_20260130.db.gz \
  --name digital-actors/player_memory_20260130.db.gz
```

---

### Disaster Recovery

#### Restore from Backup

```bash
# 1. Stop the application
docker-compose down

# 2. Restore database
gunzip -c /backups/player_memory_20260130.db.gz > data/player_memory.db

# 3. Verify database integrity
sqlite3 data/player_memory.db "PRAGMA integrity_check;"

# 4. Restart application
docker-compose up -d

# 5. Verify health
curl http://localhost:8888/health
```

#### Database Corruption Recovery

```bash
# 1. Stop application
docker-compose down

# 2. Attempt to recover
sqlite3 data/player_memory.db ".recover" > recovered.sql
sqlite3 data/player_memory_recovered.db < recovered.sql

# 3. Replace corrupted database
mv data/player_memory.db data/player_memory.db.corrupted
mv data/player_memory_recovered.db data/player_memory.db

# 4. Restart
docker-compose up -d
```

#### Complete System Recovery

If the entire server is lost:

1. **Provision new server** (same OS, Docker, etc.)
2. **Clone repository**: `git clone https://github.com/Johnny-Z13/digital-actors.git`
3. **Restore .env file** from secure storage
4. **Restore database** from backup: `cp /backups/player_memory.db data/`
5. **Deploy**: `docker-compose up -d`
6. **Verify**: Check logs and health endpoint

**Recovery Time Objective (RTO)**: Target 30 minutes
**Recovery Point Objective (RPO)**: Target 24 hours (daily backups)

---

## Troubleshooting

### Common Deployment Issues

#### 1. Container fails to start

**Symptom:**

```bash
docker-compose logs digital-actors
# Error: ANTHROPIC_API_KEY not set
```

**Solution:**

```bash
# Check .env file exists and contains keys
cat .env | grep ANTHROPIC_API_KEY

# Verify Docker can read .env
docker-compose config
```

---

#### 2. Health check failing

**Symptom:**

```bash
curl http://localhost:8888/health
# Connection refused or timeout
```

**Solution:**

```bash
# Check if container is running
docker-compose ps

# Check container logs
docker-compose logs -f digital-actors

# Check if port is bound
netstat -tulpn | grep 8888

# Test from inside container
docker exec digital-actors curl -f http://localhost:8888/health
```

---

#### 3. WebSocket connections failing

**Symptom:**

Browser console shows: `WebSocket connection to 'ws://...' failed`

**Solution:**

```bash
# Check nginx WebSocket configuration
sudo nginx -t

# Verify proxy_set_header Upgrade and Connection are set
grep -A 5 "Upgrade" /etc/nginx/sites-available/digital-actors

# Check nginx error log
sudo tail -f /var/log/nginx/digital-actors-error.log

# Test WebSocket directly (bypassing proxy)
wscat -c ws://localhost:8888/ws
```

---

#### 4. Slow response times

**Symptom:**

Dialogue responses take > 10 seconds

**Solution:**

```bash
# Check LLM API latency in logs
docker-compose logs digital-actors | grep llm_response_time_ms

# Verify using Claude Haiku (not Sonnet/Opus)
docker-compose logs | grep "ClaudeHaikuModel"

# Check network latency to Anthropic API
curl -w "@curl-format.txt" -o /dev/null -s https://api.anthropic.com/

# Monitor container resources
docker stats digital-actors
```

---

#### 5. Database locked errors

**Symptom:**

```
sqlite3.OperationalError: database is locked
```

**Solution:**

```bash
# Check for multiple processes accessing database
lsof data/player_memory.db

# Increase SQLite timeout (in player_memory.py)
# conn.execute("PRAGMA busy_timeout = 5000")

# Consider migrating to PostgreSQL for concurrent access
```

---

#### 6. Out of memory errors

**Symptom:**

```
docker-compose logs
# Killed (out of memory)
```

**Solution:**

```bash
# Increase container memory limit
# Edit docker-compose.yml
services:
  digital-actors:
    mem_limit: 4g

# Restart container
docker-compose up -d

# Monitor memory usage
docker stats digital-actors

# Check for memory leaks in application logs
```

---

#### 7. TLS certificate issues

**Symptom:**

```
NET::ERR_CERT_AUTHORITY_INVALID
```

**Solution:**

```bash
# Verify certificate installation
sudo certbot certificates

# Check nginx TLS configuration
sudo nginx -t

# Test TLS certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Force certificate renewal
sudo certbot renew --force-renewal
```

---

#### 8. API rate limiting

**Symptom:**

```
anthropic.RateLimitError: 429 Too Many Requests
```

**Solution:**

```bash
# Check Anthropic dashboard for rate limits
# Implement exponential backoff (already in code)

# Monitor API usage
docker-compose logs | grep "RateLimitError"

# Consider upgrading Anthropic plan
# Or implement request queuing/throttling
```

---

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Edit .env
LOG_LEVEL=DEBUG
LOG_FORMAT_JSON=false  # Readable format for debugging

# Restart
docker-compose restart

# View detailed logs
docker-compose logs -f digital-actors
```

---

### Getting Help

If you encounter issues not covered here:

1. **Check logs**: `docker-compose logs -f digital-actors`
2. **Search GitHub Issues**: https://github.com/Johnny-Z13/digital-actors/issues
3. **Review documentation**: [README.md](../README.md), [docs/](.)
4. **Open an issue**: Provide logs, environment details, and steps to reproduce

---

## Scaling Considerations

### Vertical Scaling

For increased load, scale up resources:

```bash
# Increase container resources
docker run --memory=4g --cpus=2 digital-actors

# Or in docker-compose.yml:
services:
  digital-actors:
    mem_limit: 4g
    cpus: 2
```

**When to scale vertically:**
- Response times degrading
- CPU usage consistently > 70%
- Memory usage approaching limit

---

### Horizontal Scaling

The current architecture is designed for single-instance deployment due to:
- SQLite database (file-based, not multi-instance)
- WebSocket session affinity requirements
- Local caching (voice cache, query cache)

**To enable horizontal scaling:**

1. **Migrate to PostgreSQL or MySQL**
   - Replace SQLite with PostgreSQL for concurrent access
   - Update `player_memory.py` with SQLAlchemy

2. **Implement distributed caching**
   - Use Redis for query cache and session storage
   - Use S3/GCS/Azure Blob for voice cache

3. **Session affinity**
   - Configure load balancer with sticky sessions
   - Or implement session replication with Redis

4. **Stateless architecture**
   - Store all state in external database/cache
   - Avoid local file storage

**Example load-balanced setup (future):**

```
          Internet
              |
         Load Balancer (ALB/NGINX)
        /      |      \
   Instance1 Instance2 Instance3
        \      |      /
      PostgreSQL + Redis
```

---

### Performance Optimization

**Current optimizations:**
- Claude Haiku 3.5 for fast responses (1-2s vs 4-6s)
- Reduced token limits (800 vs 1500)
- Async/await architecture
- Response cancellation system
- WebSocket connection pooling

**Additional optimizations:**

1. **Enable CDN for static assets**
   ```bash
   # Serve /web/* through CloudFlare or AWS CloudFront
   ```

2. **Implement LLM response streaming**
   ```python
   # Stream Claude responses for perceived lower latency
   async for chunk in stream_response(prompt):
       await websocket.send_json({"chunk": chunk})
   ```

3. **Cache frequent queries**
   ```python
   # Already implemented in query_system.py with MD5 hashing
   ```

4. **Optimize database queries**
   ```python
   # Add indexes for frequent lookups
   CREATE INDEX idx_player_id ON scene_attempts(player_id);
   CREATE INDEX idx_session_id ON sessions(player_id, started_at);
   ```

---

## Summary

This guide covered:

- Prerequisites and system requirements
- Quick start deployment with Docker Compose
- Production configuration checklist
- Deployment options (Docker, manual, AWS, GCP, Azure)
- Environment variables reference
- Database setup and maintenance
- TLS/SSL configuration with Let's Encrypt
- Reverse proxy setup with nginx and Caddy
- Security best practices (firewall, API keys, rate limiting)
- Monitoring and logging with Sentry and structured logs
- Backup and disaster recovery procedures
- Troubleshooting common deployment issues
- Scaling considerations

For additional documentation, see:

- [README.md](../README.md) - Project overview and features
- [.env.example](../.env.example) - Complete environment variable reference
- [LOGGING.md](LOGGING.md) - Structured logging details
- [DOCKER.md](../DOCKER.md) - Docker-specific documentation

For production support, consider:
- Setting up monitoring and alerting
- Implementing automated backups
- Documenting runbooks for common operations
- Conducting disaster recovery drills

---

**Version**: 1.0
**Last Updated**: 2026-01-30
**Maintainer**: Digital Actors Team
