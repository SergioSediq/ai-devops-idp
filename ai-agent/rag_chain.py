"""
Production RAG chain with ChromaDB vector store and structured JSON output.
Loads runbook documents, performs semantic search, and generates structured diagnoses.
"""

import os
import json
import logging
import glob
from typing import List, Dict, Any, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
try:
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:
    from langchain.schema import HumanMessage, SystemMessage  # type: ignore

from config import settings
from models import Severity, ErrorCategory
from log_analyzer import format_classifications_for_prompt

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# System prompt — expert SRE with structured output
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert DevOps Site Reliability Engineer (SRE) working at a company that runs Kubernetes clusters on AWS EKS and uses Terraform for infrastructure.

Your job is to analyze errors reported by developers and provide a comprehensive, actionable diagnosis.

You MUST respond in the following JSON format (and ONLY this JSON, no extra text):
{
    "root_cause": "One-line summary of the root cause",
    "severity": "CRITICAL | HIGH | MEDIUM | LOW | INFO",
    "error_category": "OOMKilled | CrashLoopBackOff | ImagePullBackOff | CreateContainerConfigError | ReadinessProbeFailure | LivenessProbeFailure | ResourceQuotaExceeded | PermissionDenied | TerraformStateLock | TerraformProviderError | CICDPipelineFailure | NetworkError | Unknown",
    "explanation": "Detailed paragraph explaining WHY the failure occurred, referencing specific log lines or data points from the context",
    "fix_commands": [
        {
            "command": "exact kubectl/terraform/aws command to run",
            "description": "What this command does and why",
            "risk_level": "LOW | MEDIUM | HIGH"
        }
    ],
    "prevention_tips": [
        "Tip 1 to prevent this from happening again",
        "Tip 2"
    ],
    "related_runbooks": [
        "runbook filename if any matched from context"
    ]
}

Rules:
- Always provide at least 2 fix_commands ordered from safest to most impactful.
- Always provide at least 2 prevention_tips.
- Reference specific data from the Kubernetes cluster context when available.
- If you see container exit code 137, the cause is OOMKilled.
- If you see CrashLoopBackOff, check the previous container logs and exit code.
- Be specific about namespaces, pod names, and resource values in your commands.
"""


# ──────────────────────────────────────────────────────────────────────────────
# Runbook loader — loads markdown files into a simple in-memory store
# ──────────────────────────────────────────────────────────────────────────────

_runbook_cache: List[Dict[str, str]] = []


def load_runbooks() -> List[Dict[str, str]]:
    """Load all runbook markdown files from the runbook directory."""
    global _runbook_cache
    if _runbook_cache:
        return _runbook_cache

    runbook_path = os.path.join(os.path.dirname(__file__), settings.runbook_dir)
    if not os.path.exists(runbook_path):
        logger.warning(f"Runbook directory not found: {runbook_path}")
        return []

    for filepath in glob.glob(os.path.join(runbook_path, "*.md")):
        try:
            with open(filepath, "r") as f:
                content = f.read()
            _runbook_cache.append({
                "filename": os.path.basename(filepath),
                "title": content.split("\n")[0].replace("#", "").strip(),
                "content": content,
            })
        except Exception as e:
            logger.error(f"Failed to load runbook {filepath}: {e}")

    logger.info(f"Loaded {len(_runbook_cache)} runbooks")
    return _runbook_cache


def search_runbooks(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Simple keyword-based runbook search.
    In production, replace with ChromaDB vector similarity search.
    """
    runbooks = load_runbooks()
    if not runbooks:
        return []

    scored = []
    query_words = set(query.lower().split())

    for rb in runbooks:
        content_lower = rb["content"].lower()
        # Score by keyword overlap
        matches = sum(1 for word in query_words if word in content_lower)
        if matches > 0:
            scored.append({
                "title": rb["title"],
                "filename": rb["filename"],
                "relevance_score": min(matches / max(len(query_words), 1), 1.0),
                "summary": rb["content"][:200] + "...",
            })

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored[:top_k]


# ──────────────────────────────────────────────────────────────────────────────
# Main RAG analysis function
# ──────────────────────────────────────────────────────────────────────────────

def analyze_devops_issue(
    error_context: str,
    classifications: Optional[List[Dict[str, Any]]] = None,
    k8s_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Production RAG pipeline:
    1. Pre-classify errors (already done by log_analyzer)
    2. Search runbooks for relevant context
    3. Construct rich prompt with all context
    4. Call Gemini LLM for structured analysis
    5. Parse and return structured JSON
    """

    # 1. Search runbooks
    matching_runbooks = search_runbooks(error_context)
    runbook_context = ""
    if matching_runbooks:
        runbook_context = "\n\nRelevant Internal Runbooks:\n"
        for rb in matching_runbooks:
            runbook_context += f"\n--- {rb['title']} ({rb['filename']}) ---\n{rb['summary']}\n"

    # 2. Format pre-classifications
    classification_context = ""
    if classifications:
        classification_context = "\n\n" + format_classifications_for_prompt(classifications)

    # 3. Format K8s data
    k8s_context = ""
    if k8s_data:
        # Include key parts, not the full blob to stay within token limits
        k8s_summary_parts = []
        if "containers" in k8s_data:
            k8s_summary_parts.append(f"Container Statuses: {json.dumps(k8s_data['containers'], indent=2)}")
        if "events" in k8s_data:
            k8s_summary_parts.append(f"Recent Events: {json.dumps(k8s_data['events'][:10], indent=2)}")
        if "conditions" in k8s_data:
            k8s_summary_parts.append(f"Deployment Conditions: {json.dumps(k8s_data['conditions'], indent=2)}")
        if "resource_spec" in k8s_data:
            k8s_summary_parts.append(f"Resource Spec: {json.dumps(k8s_data['resource_spec'], indent=2)}")
        if "recent_logs" in k8s_data:
            # Truncate logs to last 50 lines for token economy
            logs = k8s_data["recent_logs"]
            if isinstance(logs, str):
                log_lines = logs.strip().split("\n")[-50:]
                k8s_summary_parts.append(f"Recent Pod Logs (last 50 lines):\n" + "\n".join(log_lines))

        if k8s_summary_parts:
            k8s_context = "\n\nLive Kubernetes Cluster Data:\n" + "\n\n".join(k8s_summary_parts)

    # 4. Construct the full prompt
    full_prompt = f"""
--- Developer Error Report ---
{error_context}
{classification_context}
{k8s_context}
{runbook_context}

Analyze this error comprehensively and respond in the required JSON format.
"""

    # 5. Call Gemini LLM
    try:
        if settings.google_api_key:
            chat = ChatGoogleGenerativeAI(
                temperature=settings.llm_temperature,
                model=settings.gemini_model,
                max_output_tokens=settings.llm_max_output_tokens,
                google_api_key=settings.google_api_key,
            )
            result = chat.invoke([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=full_prompt),
            ])

            # Parse the JSON response
            return _parse_llm_response(result.content, matching_runbooks)
        else:
            # Mock response when no API key is set
            return _generate_mock_response(error_context, classifications, matching_runbooks)

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return _generate_fallback_response(str(e), classifications, matching_runbooks)


def _parse_llm_response(
    raw_response: str,
    runbooks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Parse LLM JSON response with fallback handling."""
    try:
        # Clean potential markdown wrapping
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        parsed = json.loads(cleaned)

        # Ensure required fields exist
        parsed.setdefault("root_cause", "Unable to determine root cause")
        parsed.setdefault("severity", "MEDIUM")
        parsed.setdefault("error_category", "Unknown")
        parsed.setdefault("explanation", raw_response)
        parsed.setdefault("fix_commands", [])
        parsed.setdefault("prevention_tips", [])
        parsed.setdefault("related_runbooks", [rb["filename"] for rb in runbooks])

        return parsed

    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response as JSON, returning raw text")
        return {
            "root_cause": "See explanation",
            "severity": "MEDIUM",
            "error_category": "Unknown",
            "explanation": raw_response,
            "fix_commands": [],
            "prevention_tips": [],
            "related_runbooks": [rb["filename"] for rb in runbooks],
        }


def _generate_mock_response(
    error_context: str,
    classifications: Optional[List[Dict[str, Any]]],
    runbooks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate a mock response when no API key is configured."""
    severity = "MEDIUM"
    category = "Unknown"
    if classifications:
        severity = classifications[0].get("severity", "MEDIUM")
        category = classifications[0].get("category", "Unknown")

    return {
        "root_cause": f"[MOCK] Detected {category} error pattern",
        "severity": severity,
        "error_category": category,
        "explanation": f"[MOCK MODE — No GOOGLE_API_KEY set]\nDetected error patterns: {json.dumps(classifications or [], indent=2)}\n\nOriginal error:\n{error_context[:500]}",
        "fix_commands": [
            {
                "command": "kubectl describe pod <pod-name> -n <namespace>",
                "description": "Get detailed pod information including events and conditions",
                "risk_level": "LOW",
            },
            {
                "command": "kubectl logs <pod-name> -n <namespace> --previous",
                "description": "Check logs from the previous crashed container instance",
                "risk_level": "LOW",
            },
        ],
        "prevention_tips": [
            "Set proper resource requests and limits for all containers",
            "Configure health probes with appropriate initialDelaySeconds",
        ],
        "related_runbooks": [rb["filename"] for rb in runbooks],
    }


def _generate_fallback_response(
    error_msg: str,
    classifications: Optional[List[Dict[str, Any]]],
    runbooks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate a fallback response when LLM call fails."""
    return {
        "root_cause": "LLM analysis failed — see pre-classified errors below",
        "severity": classifications[0]["severity"] if classifications else "MEDIUM",
        "error_category": classifications[0]["category"] if classifications else "Unknown",
        "explanation": f"The AI model could not be reached ({error_msg}). However, pattern-based analysis detected: {json.dumps(classifications or [])}",
        "fix_commands": [
            {
                "command": "kubectl get events -n <namespace> --sort-by='.lastTimestamp'",
                "description": "Check recent events in the namespace for clues",
                "risk_level": "LOW",
            }
        ],
        "prevention_tips": ["Ensure GOOGLE_API_KEY is set and valid"],
        "related_runbooks": [rb["filename"] for rb in runbooks],
    }
