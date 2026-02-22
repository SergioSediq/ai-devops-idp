"""
Pattern-based log classifier.
Pre-processes raw logs and error messages to identify known failure categories
and assign severity levels BEFORE sending to the LLM.
"""

import re
import logging
from typing import List, Dict, Any
from models import Severity, ErrorCategory

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Pattern definitions: (regex, category, severity, human hint)
# ──────────────────────────────────────────────────────────────────────────────

ERROR_PATTERNS: List[Dict[str, Any]] = [
    # ── Kubernetes ──
    {
        "pattern": re.compile(r"OOMKilled", re.IGNORECASE),
        "category": ErrorCategory.OOM_KILLED,
        "severity": Severity.CRITICAL,
        "hint": "Container exceeded memory limits and was killed by the kernel OOM killer.",
    },
    {
        "pattern": re.compile(r"CrashLoopBackOff", re.IGNORECASE),
        "category": ErrorCategory.CRASH_LOOP,
        "severity": Severity.CRITICAL,
        "hint": "Container is crashing repeatedly. Check exit code and last termination reason.",
    },
    {
        "pattern": re.compile(r"ImagePullBackOff|ErrImagePull|ImagePullError", re.IGNORECASE),
        "category": ErrorCategory.IMAGE_PULL,
        "severity": Severity.HIGH,
        "hint": "Unable to pull container image. Check image name/tag, registry auth, and network.",
    },
    {
        "pattern": re.compile(r"CreateContainerConfigError", re.IGNORECASE),
        "category": ErrorCategory.CONFIG_ERROR,
        "severity": Severity.HIGH,
        "hint": "Container configuration error. Usually a missing Secret, ConfigMap, or volume mount.",
    },
    {
        "pattern": re.compile(r"Readiness\s*probe\s*failed|readinessProbe", re.IGNORECASE),
        "category": ErrorCategory.READINESS_PROBE,
        "severity": Severity.MEDIUM,
        "hint": "Readiness probe failing — pod won't receive traffic. Check health endpoint and port.",
    },
    {
        "pattern": re.compile(r"Liveness\s*probe\s*failed|livenessProbe", re.IGNORECASE),
        "category": ErrorCategory.LIVENESS_PROBE,
        "severity": Severity.HIGH,
        "hint": "Liveness probe failing — kubelet will restart the container. Check health endpoint.",
    },
    {
        "pattern": re.compile(r"exceeded\s*quota|ResourceQuota|forbidden.*quota", re.IGNORECASE),
        "category": ErrorCategory.RESOURCE_QUOTA,
        "severity": Severity.MEDIUM,
        "hint": "Resource quota exceeded. Request more quota or reduce resource requests.",
    },
    {
        "pattern": re.compile(r"forbidden|Unauthorized|403|RBAC", re.IGNORECASE),
        "category": ErrorCategory.PERMISSION_DENIED,
        "severity": Severity.HIGH,
        "hint": "Permission denied. Check RBAC roles, service account, and cluster role bindings.",
    },
    {
        "pattern": re.compile(r"connection\s*refused|dial\s*tcp.*refused|timeout|ETIMEDOUT|network\s*unreachable", re.IGNORECASE),
        "category": ErrorCategory.NETWORK_ERROR,
        "severity": Severity.HIGH,
        "hint": "Network connectivity issue. Check service endpoints, DNS, security groups, and NACLs.",
    },

    # ── Terraform ──
    {
        "pattern": re.compile(r"state\s*lock|lock\s*ID|ConditionalCheckFailedException.*terraform", re.IGNORECASE),
        "category": ErrorCategory.TERRAFORM_STATE_LOCK,
        "severity": Severity.MEDIUM,
        "hint": "Terraform state is locked. Check DynamoDB lock table or use force-unlock if safe.",
    },
    {
        "pattern": re.compile(r"provider.*error|NoCredentialProviders|ExpiredToken|InvalidClientTokenId", re.IGNORECASE),
        "category": ErrorCategory.TERRAFORM_PROVIDER,
        "severity": Severity.HIGH,
        "hint": "Terraform provider authentication failure. Check AWS credentials and assume-role config.",
    },

    # ── CI/CD ──
    {
        "pattern": re.compile(r"exit\s*code\s*[1-9]\d*|Process\s*completed\s*with\s*exit\s*code\s*[1-9]", re.IGNORECASE),
        "category": ErrorCategory.CI_CD_FAILURE,
        "severity": Severity.MEDIUM,
        "hint": "Build step failed with a non-zero exit code. Check the failing command output.",
    },
    {
        "pattern": re.compile(r"permission\s*denied|EACCES", re.IGNORECASE),
        "category": ErrorCategory.PERMISSION_DENIED,
        "severity": Severity.MEDIUM,
        "hint": "File/system permission denied. Check file ownership and process privileges.",
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# Classifier
# ──────────────────────────────────────────────────────────────────────────────

def classify_errors(text: str) -> List[Dict[str, Any]]:
    """
    Scan text against known error patterns and return classified matches.
    Returns a list of dicts with: category, severity, hint, matched_text.
    """
    classifications = []
    seen_categories = set()

    for entry in ERROR_PATTERNS:
        matches = entry["pattern"].findall(text)
        if matches and entry["category"] not in seen_categories:
            seen_categories.add(entry["category"])
            classifications.append({
                "category": entry["category"].value,
                "severity": entry["severity"].value,
                "hint": entry["hint"],
                "matched_text": matches[0] if len(matches) == 1 else matches[:3],
                "match_count": len(matches),
            })

    # Sort by severity (CRITICAL first)
    severity_order = {
        Severity.CRITICAL.value: 0,
        Severity.HIGH.value: 1,
        Severity.MEDIUM.value: 2,
        Severity.LOW.value: 3,
        Severity.INFO.value: 4,
    }
    classifications.sort(key=lambda x: severity_order.get(x["severity"], 5))

    return classifications


def get_highest_severity(classifications: List[Dict[str, Any]]) -> Severity:
    """Return the highest severity from a list of classifications (list is pre-sorted)."""
    if not classifications:
        return Severity.INFO
    severity_map = {s.value: s for s in Severity}
    return severity_map.get(classifications[0]["severity"], Severity.INFO)


def format_classifications_for_prompt(classifications: List[Dict[str, Any]]) -> str:
    """Format classifications into a readable string for the LLM prompt."""
    if not classifications:
        return "No known error patterns detected."

    lines = ["Pre-analysis detected the following error patterns:"]
    for i, c in enumerate(classifications, 1):
        lines.append(
            f"  {i}. [{c['severity']}] {c['category']}: {c['hint']}"
        )
    return "\n".join(lines)
