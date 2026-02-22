"""Pydantic models for structured API requests and responses."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ──────────────────────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class ErrorCategory(str, Enum):
    OOM_KILLED = "OOMKilled"
    CRASH_LOOP = "CrashLoopBackOff"
    IMAGE_PULL = "ImagePullBackOff"
    CONFIG_ERROR = "CreateContainerConfigError"
    READINESS_PROBE = "ReadinessProbeFailure"
    LIVENESS_PROBE = "LivenessProbeFailure"
    RESOURCE_QUOTA = "ResourceQuotaExceeded"
    PERMISSION_DENIED = "PermissionDenied"
    TERRAFORM_STATE_LOCK = "TerraformStateLock"
    TERRAFORM_PROVIDER = "TerraformProviderError"
    CI_CD_FAILURE = "CICDPipelineFailure"
    NETWORK_ERROR = "NetworkError"
    UNKNOWN = "Unknown"


# ──────────────────────────────────────────────────────────────────────────────
# Request Models
# ──────────────────────────────────────────────────────────────────────────────

class DiagnoseRequest(BaseModel):
    """Full diagnosis request — the primary endpoint."""
    error_message: str = Field(..., description="Raw error log, build output, or natural language question")
    pod_name: Optional[str] = Field(None, description="K8s pod name to inspect")
    deployment_name: Optional[str] = Field(None, description="K8s deployment to inspect")
    namespace: str = Field("default", description="Kubernetes namespace")
    include_cluster_health: bool = Field(False, description="Also include cluster-wide health data")


class RunbookRequest(BaseModel):
    """Request to find matching runbooks for a given error."""
    error_message: str
    top_k: int = Field(3, description="Number of runbooks to return")


# ──────────────────────────────────────────────────────────────────────────────
# Response Models
# ──────────────────────────────────────────────────────────────────────────────

class FixCommand(BaseModel):
    """A single actionable command to remediate the issue."""
    command: str = Field(..., description="The exact shell/kubectl/terraform command")
    description: str = Field(..., description="What this command does")
    risk_level: str = Field("LOW", description="Risk of running this command: LOW, MEDIUM, HIGH")


class RelatedRunbook(BaseModel):
    """Reference to a matching internal runbook."""
    title: str
    filename: str
    relevance_score: float = Field(0.0, ge=0.0, le=1.0)
    summary: str = ""


class DiagnoseResponse(BaseModel):
    """Structured diagnosis output — the main response from /diagnose."""
    request_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    severity: Severity
    error_category: ErrorCategory
    root_cause: str = Field(..., description="One-line root cause summary")
    explanation: str = Field(..., description="Detailed explanation of why the failure occurred")
    fix_commands: List[FixCommand] = Field(default_factory=list, description="Actionable fix commands")
    prevention_tips: List[str] = Field(default_factory=list, description="How to prevent this in the future")
    related_runbooks: List[RelatedRunbook] = Field(default_factory=list)
    k8s_context: Optional[Dict[str, Any]] = Field(None, description="Raw K8s data collected during diagnosis")
    classified_errors: Optional[List[Dict[str, Any]]] = Field(None, description="Pre-LLM error classifications")


class PodHealthSummary(BaseModel):
    name: str
    namespace: str
    status: str
    restarts: int
    ready: bool
    age: str = ""
    issues: List[str] = Field(default_factory=list)


class NodeHealthSummary(BaseModel):
    name: str
    status: str
    conditions: List[str] = Field(default_factory=list)
    cpu_pressure: bool = False
    memory_pressure: bool = False
    disk_pressure: bool = False


class ClusterHealthResponse(BaseModel):
    """Quick cluster-wide health summary."""
    request_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    cluster_status: str  # HEALTHY / DEGRADED / CRITICAL
    total_nodes: int = 0
    ready_nodes: int = 0
    total_pods: int = 0
    unhealthy_pods: List[PodHealthSummary] = Field(default_factory=list)
    node_issues: List[NodeHealthSummary] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
