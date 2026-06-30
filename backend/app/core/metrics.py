"""Prometheus metrics registry.

All application metrics live here so importers get the same objects.
"""

from prometheus_client import (
    REGISTRY as DEFAULT_REGISTRY,
)
from prometheus_client import (
    Counter,
    Histogram,
)

# Use the default registry so the /metrics endpoint collects standard
# process/Python metrics alongside application metrics.

http_requests_total = Counter(
    "knowbase_http_requests_total",
    "Total HTTP requests",
    ["method", "path_template", "status_code"],
)

http_request_duration_seconds = Histogram(
    "knowbase_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path_template"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

agent_runs_total = Counter(
    "knowbase_agent_runs_total",
    "Agent runs by outcome",
    ["status"],  # started | completed | failed
)

document_ingests_total = Counter(
    "knowbase_document_ingests_total",
    "Document ingest jobs by outcome",
    ["status"],  # started | completed | failed
)

__all__ = [
    "DEFAULT_REGISTRY",
    "agent_runs_total",
    "document_ingests_total",
    "http_request_duration_seconds",
    "http_requests_total",
]
