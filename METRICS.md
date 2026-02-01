# Metrics Overview

Digital Actors includes built-in Prometheus metrics for monitoring application performance and behavior.

## Quick Start

### View Raw Metrics

```bash
# Start the application
python web_server.py

# Access metrics endpoint
curl http://localhost:8888/metrics
```

### Start Monitoring Stack

```bash
# Start with Docker Compose (includes Prometheus + Grafana)
docker-compose up -d prometheus grafana

# Access Grafana dashboard
open http://localhost:3000  # Default credentials: admin/admin
```

## What's Being Tracked

### Request Metrics
- **Request count** - Total requests by scene, character, and status
- **Response time** - Complete request duration (LLM + TTS)
- **Active sessions** - Current WebSocket connections

### Component Metrics
- **LLM latency** - Time spent calling Anthropic/OpenAI APIs
- **TTS latency** - Time spent generating speech audio
- **Database queries** - Query execution time by operation type

### Error Tracking
- **Error count** - Errors by type (validation, LLM, TTS, etc.)
- **Error rate** - Percentage of failed requests

## Implementation

### Core Files

- **`metrics.py`** - Metrics definitions and instrumentation helpers
- **`grafana-dashboard.json`** - Pre-built Grafana dashboard
- **`prometheus.yml`** - Prometheus scrape configuration
- **`docs/MONITORING.md`** - Complete monitoring guide

### Instrumented Functions

The following functions automatically track metrics:

1. **`ChatSession.handle_message()`** - Request count and response time
2. **`invoke_llm_async()`** - LLM API latency
3. **`TTSManager.synthesize_speech()`** - TTS processing time
4. **Session lifecycle** - Active session count

## Example Queries

### Prometheus Queries

```promql
# Request rate per second
rate(digital_actors_requests_total[5m])

# 95th percentile response time
histogram_quantile(0.95, rate(digital_actors_response_time_seconds_bucket[5m]))

# Error rate
rate(digital_actors_errors_total[5m]) / rate(digital_actors_requests_total[5m])

# Average LLM latency
rate(digital_actors_llm_latency_seconds_sum[5m]) / rate(digital_actors_llm_latency_seconds_count[5m])
```

## Grafana Dashboard

The included dashboard (`grafana-dashboard.json`) provides:

- **Request Rate by Scene/Character** - Line graph of requests/second
- **Active Sessions** - Gauge showing current connections
- **Error Rate** - Percentage gauge with thresholds
- **Response Time Distribution** - p50/p95/p99 histograms
- **LLM API Latency** - Latency by provider and model
- **TTS Processing Time** - Audio generation performance
- **Error Rate by Type** - Stacked bar chart
- **Database Query Time** - Query performance by operation

## Adding Custom Metrics

### Example: Track Custom Operation

```python
from metrics import Histogram

# Define new metric
custom_operation_seconds = Histogram(
    "digital_actors_custom_operation_seconds",
    "Time taken for custom operation",
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, float("inf")),
)

# Use in code
import time

start = time.time()
# ... do operation ...
duration = time.time() - start
custom_operation_seconds.observe(duration)
```

### Example: Track Custom Counter

```python
from metrics import Counter

# Define new counter
custom_events_total = Counter(
    "digital_actors_custom_events_total",
    "Total number of custom events",
    ["event_type"],
)

# Use in code
custom_events_total.labels(event_type="player_action").inc()
```

## Production Considerations

### Security

For production, consider protecting the `/metrics` endpoint:

```python
# Add authentication in web_server.py
METRICS_TOKEN = os.getenv("METRICS_TOKEN", "")

async def metrics_handler(request: web.Request) -> web.Response:
    if METRICS_TOKEN:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer ") or auth_header[7:] != METRICS_TOKEN:
            return web.Response(status=401, text="Unauthorized")

    metrics_output = generate_latest()
    return web.Response(body=metrics_output, content_type=CONTENT_TYPE_LATEST)
```

### Performance Impact

Metrics collection has minimal performance impact:
- Memory: ~1-2MB for metric storage
- CPU: < 0.1% overhead per request
- Network: Prometheus scrapes every 15s (~10KB per scrape)

### Data Retention

Configure retention in `prometheus.yml`:

```yaml
storage:
  tsdb:
    retention.time: 15d  # Keep 15 days of data
    retention.size: 10GB # Or limit by size
```

## Troubleshooting

### Metrics endpoint returns 404

- Ensure `metrics_handler` route is registered in `web_server.py`
- Check that `/metrics` endpoint is added before catch-all routes

### Prometheus shows "DOWN" target

- Verify Digital Actors is running: `curl http://localhost:8888/health`
- Check Prometheus logs: `docker logs digital-actors-prometheus`
- Verify network connectivity between containers

### Grafana shows "No Data"

- Verify Prometheus is scraping: http://localhost:9090/targets
- Check time range in Grafana (try "Last 1 hour")
- Verify data source is configured: Configuration → Data Sources

## Further Reading

- [Full Monitoring Guide](docs/MONITORING.md) - Complete setup and configuration
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
