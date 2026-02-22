"""
Production FastAPI service for the AI DevOps Assistant.
Endpoints:
  POST /diagnose        — Full diagnosis with K8s data + log classification + RAG
  GET  /cluster-health  — Quick cluster-wide health summary
  POST /suggest-runbook — Find matching runbooks for an error
  GET  /health          — Liveness/readiness probe
"""

import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import settings
from models import (
    DiagnoseRequest, DiagnoseResponse, FixCommand, RelatedRunbook,
    RunbookRequest, ClusterHealthResponse,
    PodHealthSummary, NodeHealthSummary,
    Severity, ErrorCategory,
)
from k8s_collector import (
    is_k8s_available, collect_pod_details,
    collect_deployment_details, collect_namespace_overview,
    collect_cluster_health,
)
from log_analyzer import classify_errors, get_highest_severity
from rag_chain import analyze_devops_issue, search_runbooks

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# App lifecycle
# ──────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown tasks."""
    logger.info("🚀 AI DevOps Assistant starting up...")
    logger.info(f"   Gemini Model : {settings.gemini_model}")
    logger.info(f"   K8s Available: {is_k8s_available()}")
    logger.info(f"   API Key Set  : {'Yes' if settings.google_api_key else 'No (mock mode)'}")
    yield
    logger.info("AI DevOps Assistant shutting down.")


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AI DevOps Assistant",
    description="Production-grade AI-powered DevOps diagnostics engine",
    version="2.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
# POST /diagnose — Primary endpoint
# ──────────────────────────────────────────────────────────────────────────────

@limiter.limit(f"{settings.rate_limit_requests}/minute")
@app.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(request: Request, body: DiagnoseRequest):
    """
    Full diagnostic pipeline:
    1. Classify errors from the raw message
    2. Optionally collect live K8s data (pod, deployment, namespace)
    3. Run RAG analysis with Gemini
    4. Return structured DiagnoseResponse
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Diagnosis request for namespace={body.namespace}")

    try:
        # Step 1: Classify known error patterns
        classifications = classify_errors(body.error_message)
        logger.info(f"[{request_id}] Classified {len(classifications)} error patterns")

        # Step 2: Collect K8s data if available
        k8s_data = {}
        if is_k8s_available():
            if body.pod_name:
                k8s_data = collect_pod_details(body.pod_name, body.namespace)
                logger.info(f"[{request_id}] Collected pod details for {body.pod_name}")

            if body.deployment_name:
                dep_data = collect_deployment_details(body.deployment_name, body.namespace)
                k8s_data.update(dep_data)
                logger.info(f"[{request_id}] Collected deployment details for {body.deployment_name}")

            if body.include_cluster_health:
                ns_data = collect_namespace_overview(body.namespace)
                k8s_data["namespace_overview"] = ns_data

        # Step 3: RAG analysis
        analysis = analyze_devops_issue(
            error_context=body.error_message,
            classifications=classifications,
            k8s_data=k8s_data if k8s_data else None,
        )

        # Step 4: Build structured response
        fix_commands = [
            FixCommand(
                command=cmd.get("command", ""),
                description=cmd.get("description", ""),
                risk_level=cmd.get("risk_level", "LOW"),
            )
            for cmd in analysis.get("fix_commands", [])
        ]

        related_runbooks = [
            RelatedRunbook(title=rb, filename=rb, relevance_score=0.8)
            if isinstance(rb, str)
            else RelatedRunbook(**rb)
            for rb in analysis.get("related_runbooks", [])
        ]

        # Map severity and category from analysis
        try:
            severity = Severity(analysis.get("severity", "MEDIUM"))
        except ValueError:
            severity = get_highest_severity(classifications) if classifications else Severity.MEDIUM

        try:
            error_category = ErrorCategory(analysis.get("error_category", "Unknown"))
        except ValueError:
            error_category = ErrorCategory.UNKNOWN

        return DiagnoseResponse(
            request_id=request_id,
            severity=severity,
            error_category=error_category,
            root_cause=analysis.get("root_cause", "Unknown"),
            explanation=analysis.get("explanation", "No analysis available"),
            fix_commands=fix_commands,
            prevention_tips=analysis.get("prevention_tips", []),
            related_runbooks=related_runbooks,
            k8s_context=k8s_data if k8s_data else None,
            classified_errors=classifications if classifications else None,
        )

    except Exception as e:
        logger.error(f"[{request_id}] Diagnosis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Diagnosis failed: {str(e)}")


# ──────────────────────────────────────────────────────────────────────────────
# GET /cluster-health
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/cluster-health", response_model=ClusterHealthResponse)
async def cluster_health():
    """Quick cluster-wide health check — nodes, unhealthy pods, warnings."""
    request_id = str(uuid.uuid4())[:8]

    if not is_k8s_available():
        return ClusterHealthResponse(
            request_id=request_id,
            cluster_status="UNKNOWN",
            warnings=["Kubernetes is not configured. Cannot collect cluster health."],
        )

    try:
        health = collect_cluster_health()

        # Build node summaries
        node_issues = []
        for node in health.get("nodes", []):
            if node["memory_pressure"] or node["disk_pressure"] or node.get("pid_pressure"):
                issues = []
                if node["memory_pressure"]:
                    issues.append("MemoryPressure")
                if node["disk_pressure"]:
                    issues.append("DiskPressure")
                if node.get("pid_pressure"):
                    issues.append("PIDPressure")
                node_issues.append(NodeHealthSummary(
                    name=node["name"],
                    status="Degraded",
                    conditions=issues,
                    cpu_pressure=False,
                    memory_pressure=node["memory_pressure"],
                    disk_pressure=node["disk_pressure"],
                ))

        # Determine overall status
        total_nodes = health.get("total_nodes", 0)
        ready_nodes = health.get("ready_nodes", 0)

        if ready_nodes == 0 and total_nodes > 0:
            cluster_status = "CRITICAL"
        elif node_issues or ready_nodes < total_nodes:
            cluster_status = "DEGRADED"
        else:
            cluster_status = "HEALTHY"

        return ClusterHealthResponse(
            request_id=request_id,
            cluster_status=cluster_status,
            total_nodes=total_nodes,
            ready_nodes=ready_nodes,
            node_issues=node_issues,
        )

    except Exception as e:
        logger.error(f"[{request_id}] Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# POST /suggest-runbook
# ──────────────────────────────────────────────────────────────────────────────

@limiter.limit(f"{settings.rate_limit_requests}/minute")
@app.post("/suggest-runbook")
async def suggest_runbook(request: Request, body: RunbookRequest):
    """Search internal runbooks for a matching error."""
    results = search_runbooks(body.error_message, top_k=body.top_k)
    return {
        "query": body.error_message,
        "results": results,
        "total_matched": len(results),
    }


# ──────────────────────────────────────────────────────────────────────────────
# GET /health — Probes
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Liveness / readiness probe."""
    return {
        "status": "ok",
        "service": "ai-devops-assistant",
        "version": "2.0.0",
        "k8s_connected": is_k8s_available(),
        "llm_configured": bool(settings.google_api_key),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Legacy endpoint — backwards compatibility
# ──────────────────────────────────────────────────────────────────────────────

@limiter.limit(f"{settings.rate_limit_requests}/minute")
@app.post("/analyze-error")
async def analyze_error_legacy(req: Request, body: DiagnoseRequest):
    """Legacy endpoint — redirects to /diagnose."""
    return await diagnose(req, body)


# ──────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
