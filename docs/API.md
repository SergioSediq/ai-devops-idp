# AI DevOps Assistant — API Reference

Base URL: `http://localhost:8000` (local) or your deployed AI Agent URL.

Interactive docs: **[Swagger UI](http://localhost:8000/docs)** | **ReDoc** at `/redoc`

---

## Endpoints

### `GET /health`
Liveness and readiness probe.

**Response:**
```json
{
  "status": "ok",
  "service": "ai-devops-assistant",
  "version": "2.0.0",
  "k8s_connected": true,
  "llm_configured": true
}
```

**Rate limit:** None (probes should not be limited).

---

### `POST /diagnose`
Full AI-powered diagnostic pipeline.

**Request:**
```json
{
  "error_message": "Pod in CrashLoopBackOff with exit code 137",
  "pod_name": "api-server-7d9f8b6c5-xk4jn",
  "deployment_name": "api-server",
  "namespace": "production",
  "include_cluster_health": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `error_message` | string | Yes | Raw error log or description |
| `pod_name` | string | No | Kubernetes pod to inspect |
| `deployment_name` | string | No | Deployment to inspect |
| `namespace` | string | No | Namespace (default: `default`) |
| `include_cluster_health` | bool | No | Include cluster-wide health data |

**Response:** `DiagnoseResponse` with `root_cause`, `severity`, `error_category`, `fix_commands`, `prevention_tips`, `related_runbooks`, etc.

**Rate limit:** 60 requests/minute (configurable via `RATE_LIMIT_REQUESTS`).

---

### `GET /cluster-health`
Cluster-wide health summary (nodes, pressure conditions, etc.).

**Response:** `ClusterHealthResponse` with `cluster_status`, `total_nodes`, `ready_nodes`, `node_issues`.

**Rate limit:** None (internal dashboards).

---

### `POST /suggest-runbook`
Search internal runbooks by keyword.

**Request:**
```json
{
  "error_message": "terraform state lock",
  "top_k": 3
}
```

**Response:**
```json
{
  "query": "terraform state lock",
  "results": [...],
  "total_matched": 2
}
```

**Rate limit:** 60 requests/minute.

---

### `POST /analyze-error`
Legacy alias for `POST /diagnose`. Same behavior and rate limit.

---

## Rate limiting
- `POST /diagnose`, `POST /suggest-runbook`, `POST /analyze-error`: `RATE_LIMIT_REQUESTS` per minute (default 60).
- Exceeding the limit returns HTTP 429 with `Retry-After` header.
