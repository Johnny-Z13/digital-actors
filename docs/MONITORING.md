# Monitoring Guide

This guide covers setting up monitoring for Digital Actors using Prometheus and Grafana.

## Overview

Digital Actors exposes Prometheus metrics that track:
- Request count by scene/character
- Response time distribution
- LLM API latency
- TTS processing time
- Error rate by type
- Active session count
- Database query time

## Architecture

```
Digital Actors (/metrics endpoint)
    ↓
Prometheus (scrapes metrics every 15s)
    ↓
Grafana (visualizes metrics)
```

## Quick Start

### Using Docker Compose

The easiest way to set up monitoring is with Docker Compose:

```bash
# Start the full stack with monitoring
docker-compose -f docker-compose.yml up -d

# Or start only monitoring services
docker-compose -f docker-compose.yml up -d prometheus grafana
```

Access the services:
- Digital Actors: http://localhost:8888
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

### Manual Setup

#### 1. Install Prometheus

**macOS:**
```bash
brew install prometheus
```

**Linux:**
```bash
wget https://github.com/prometheus/prometheus/releases/download/v2.48.0/prometheus-2.48.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*
```

**Windows:**
Download from: https://prometheus.io/download/

#### 2. Configure Prometheus

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'digital-actors'
    static_configs:
      - targets: ['localhost:8888']
    metrics_path: '/metrics'
```

#### 3. Start Prometheus

```bash
prometheus --config.file=prometheus.yml
```

Access Prometheus UI at: http://localhost:9090

#### 4. Install Grafana

**macOS:**
```bash
brew install grafana
brew services start grafana
```

**Linux:**
```bash
sudo apt-get install -y adduser libfontconfig1
wget https://dl.grafana.com/enterprise/release/grafana-enterprise_10.2.2_amd64.deb
sudo dpkg -i grafana-enterprise_10.2.2_amd64.deb
sudo systemctl start grafana-server
```

**Windows:**
Download from: https://grafana.com/grafana/download

#### 5. Configure Grafana

1. Access Grafana at: http://localhost:3000 (admin/admin)
2. Add Prometheus data source:
   - Go to Configuration → Data Sources
   - Click "Add data source"
   - Select "Prometheus"
   - URL: `http://localhost:9090`
   - Click "Save & Test"

3. Import Dashboard:
   - Go to Dashboards → Import
   - Upload `grafana-dashboard.json` from the project root
   - Select the Prometheus data source
   - Click "Import"

## Available Metrics

### Counters

#### `digital_actors_requests_total`
Total number of requests processed.

**Labels:**
- `scene`: Scene ID (e.g., "welcome", "life_raft")
- `character`: Character ID (e.g., "clippy", "submariner")
- `status`: Request status ("success", "error")

**Example queries:**
```promql
# Request rate per second
rate(digital_actors_requests_total[5m])

# Total requests by scene
sum(digital_actors_requests_total) by (scene)

# Success rate
sum(rate(digital_actors_requests_total{status="success"}[5m])) /
sum(rate(digital_actors_requests_total[5m]))
```

#### `digital_actors_errors_total`
Total number of errors encountered.

**Labels:**
- `error_type`: Type of error (e.g., "validation_error", "llm_call_error", "tts_synthesis_error")

**Example queries:**
```promql
# Error rate per second
rate(digital_actors_errors_total[5m])

# Errors by type
sum(digital_actors_errors_total) by (error_type)
```

### Histograms

#### `digital_actors_response_time_seconds`
Time taken to process a complete request (includes LLM and TTS).

**Labels:**
- `scene`: Scene ID
- `character`: Character ID

**Example queries:**
```promql
# 95th percentile response time
histogram_quantile(0.95, rate(digital_actors_response_time_seconds_bucket[5m]))

# Average response time by scene
rate(digital_actors_response_time_seconds_sum[5m]) /
rate(digital_actors_response_time_seconds_count[5m])
```

#### `digital_actors_llm_latency_seconds`
Time taken for LLM API calls.

**Labels:**
- `provider`: LLM provider (e.g., "anthropic", "openai", "google")
- `model`: Model name (e.g., "claude-haiku", "gpt-4")

**Example queries:**
```promql
# 99th percentile LLM latency
histogram_quantile(0.99, rate(digital_actors_llm_latency_seconds_bucket[5m]))

# Average LLM latency by provider
rate(digital_actors_llm_latency_seconds_sum[5m]) by (provider) /
rate(digital_actors_llm_latency_seconds_count[5m]) by (provider)
```

#### `digital_actors_tts_latency_seconds`
Time taken for TTS processing.

**Example queries:**
```promql
# Median TTS latency
histogram_quantile(0.50, rate(digital_actors_tts_latency_seconds_bucket[5m]))

# TTS call rate
rate(digital_actors_tts_latency_seconds_count[5m])
```

#### `digital_actors_db_query_time_seconds`
Time taken for database queries.

**Labels:**
- `operation`: Database operation (e.g., "insert", "select", "update", "delete")

**Example queries:**
```promql
# 95th percentile query time by operation
histogram_quantile(0.95, rate(digital_actors_db_query_time_seconds_bucket[5m])) by (operation)
```

### Gauges

#### `digital_actors_active_sessions`
Current number of active chat sessions.

**Example queries:**
```promql
# Current active sessions
digital_actors_active_sessions

# Average active sessions over last hour
avg_over_time(digital_actors_active_sessions[1h])
```

## Alert Rules

Create alert rules in Prometheus (`alerts.yml`):

```yaml
groups:
  - name: digital_actors
    interval: 30s
    rules:
      # Alert if error rate exceeds 5%
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(digital_actors_errors_total[5m]))
            /
            sum(rate(digital_actors_requests_total[5m]))
          ) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # Alert if 95th percentile response time exceeds 10s
      - alert: SlowResponses
        expr: |
          histogram_quantile(0.95,
            rate(digital_actors_response_time_seconds_bucket[5m])
          ) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow response times detected"
          description: "95th percentile response time is {{ $value }}s"

      # Alert if LLM latency is too high
      - alert: SlowLLMCalls
        expr: |
          histogram_quantile(0.95,
            rate(digital_actors_llm_latency_seconds_bucket[5m])
          ) > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "LLM API calls are slow"
          description: "95th percentile LLM latency is {{ $value }}s"

      # Alert if TTS processing is too slow
      - alert: SlowTTSProcessing
        expr: |
          histogram_quantile(0.95,
            rate(digital_actors_tts_latency_seconds_bucket[5m])
          ) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "TTS processing is slow"
          description: "95th percentile TTS latency is {{ $value }}s"

      # Alert if no requests in last 10 minutes (service might be down)
      - alert: NoRequests
        expr: |
          rate(digital_actors_requests_total[5m]) == 0
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "No requests received"
          description: "No requests in the last 10 minutes"

      # Alert if database queries are slow
      - alert: SlowDatabaseQueries
        expr: |
          histogram_quantile(0.95,
            rate(digital_actors_db_query_time_seconds_bucket[5m])
          ) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database queries are slow"
          description: "95th percentile DB query time is {{ $value }}s"
```

Add to `prometheus.yml`:
```yaml
rule_files:
  - 'alerts.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']
```

## Troubleshooting

### Metrics not appearing in Prometheus

1. Check if the metrics endpoint is accessible:
```bash
curl http://localhost:8888/metrics
```

2. Verify Prometheus is scraping the target:
- Go to http://localhost:9090/targets
- Check if `digital-actors` target is UP

3. Check Prometheus logs:
```bash
# Docker
docker-compose logs prometheus

# Systemd
sudo journalctl -u prometheus -f
```

### Grafana dashboard shows "No Data"

1. Verify Prometheus data source is configured correctly
2. Check that Digital Actors is running and receiving requests
3. Verify time range in Grafana (try "Last 1 hour")
4. Test queries directly in Prometheus UI

### High memory usage

Prometheus stores metrics in memory. To reduce memory usage:

1. Reduce retention time in `prometheus.yml`:
```yaml
global:
  scrape_interval: 30s  # Increase from 15s
storage:
  tsdb:
    retention.time: 7d  # Reduce from default 15d
```

2. Reduce histogram bucket count in `metrics.py` if needed

## Production Considerations

### Security

1. Restrict access to metrics endpoint:
```python
# In web_server.py, add authentication to metrics_handler
async def metrics_handler(request: web.Request) -> web.Response:
    # Check for metrics token
    token = request.headers.get("Authorization")
    if token != f"Bearer {METRICS_TOKEN}":
        return web.Response(status=401)
    # ... rest of handler
```

2. Use HTTPS for Grafana and Prometheus
3. Enable authentication in Grafana (change default admin password)

### Scaling

1. Use remote storage for long-term retention:
```yaml
# prometheus.yml
remote_write:
  - url: "https://prometheus.example.com/api/v1/write"
```

2. Use Grafana Cloud for managed Grafana
3. Consider Thanos for Prometheus HA and long-term storage

### Performance Tuning

1. Adjust scrape interval based on needs:
```yaml
scrape_interval: 15s  # Default (good for most cases)
scrape_interval: 5s   # High resolution (more load)
scrape_interval: 60s  # Low resolution (less load)
```

2. Use recording rules for expensive queries:
```yaml
# Create pre-computed metrics
groups:
  - name: digital_actors_recordings
    interval: 30s
    rules:
      - record: job:digital_actors_request_rate:5m
        expr: rate(digital_actors_requests_total[5m])
```

## Integration with CI/CD

See [DEPLOYMENT.md](DEPLOYMENT.md) for information on monitoring in production environments.

## Further Reading

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/best-practices-for-creating-dashboards/)

## Support

For issues or questions:
- Check existing GitHub issues
- Create a new issue with the `monitoring` label
- Include Prometheus/Grafana versions and relevant logs
