"""
Deep Kubernetes data collector.
Gathers pod status, events, deployments, node conditions, HPA, and resource quotas.
"""

import logging
from typing import Dict, Any, List, Optional
from kubernetes import client, config
from config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Initialization
# ──────────────────────────────────────────────────────────────────────────────

_k8s_available = False

try:
    if settings.k8s_in_cluster:
        config.load_incluster_config()
    else:
        config.load_kube_config()
    _k8s_available = True
except Exception as e:
    logger.warning(f"Kubernetes not available: {e}. K8s features disabled.")


def is_k8s_available() -> bool:
    return _k8s_available


# ──────────────────────────────────────────────────────────────────────────────
# Pod-level collection
# ──────────────────────────────────────────────────────────────────────────────

def collect_pod_details(pod_name: str, namespace: str = "default") -> Dict[str, Any]:
    """Collect deep details about a specific pod."""
    if not _k8s_available:
        return {"error": "Kubernetes not available"}

    v1 = client.CoreV1Api()
    result: Dict[str, Any] = {}

    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        status = pod.status

        # Basic info
        result["name"] = pod_name
        result["namespace"] = namespace
        result["phase"] = status.phase
        result["host_ip"] = status.host_ip
        result["pod_ip"] = status.pod_ip
        result["start_time"] = str(status.start_time) if status.start_time else None

        # Container statuses
        containers = []
        for cs in (status.container_statuses or []):
            container_info = {
                "name": cs.name,
                "ready": cs.ready,
                "restart_count": cs.restart_count,
                "image": cs.image,
            }
            if cs.state:
                if cs.state.waiting:
                    container_info["state"] = "Waiting"
                    container_info["reason"] = cs.state.waiting.reason
                    container_info["message"] = cs.state.waiting.message
                elif cs.state.terminated:
                    container_info["state"] = "Terminated"
                    container_info["reason"] = cs.state.terminated.reason
                    container_info["exit_code"] = cs.state.terminated.exit_code
                    container_info["message"] = cs.state.terminated.message
                elif cs.state.running:
                    container_info["state"] = "Running"
                    container_info["started_at"] = str(cs.state.running.started_at)

            if cs.last_state and cs.last_state.terminated:
                container_info["last_termination"] = {
                    "reason": cs.last_state.terminated.reason,
                    "exit_code": cs.last_state.terminated.exit_code,
                    "message": cs.last_state.terminated.message,
                    "finished_at": str(cs.last_state.terminated.finished_at),
                }
            containers.append(container_info)

        result["containers"] = containers

        # Resource requests/limits from spec
        resource_info = []
        for c in (pod.spec.containers or []):
            res = {"name": c.name}
            if c.resources:
                res["requests"] = dict(c.resources.requests) if c.resources.requests else {}
                res["limits"] = dict(c.resources.limits) if c.resources.limits else {}
            resource_info.append(res)
        result["resource_spec"] = resource_info

    except client.ApiException as e:
        result["error"] = f"Failed to fetch pod: {e.reason}"

    # Pod logs (last N lines)
    try:
        logs = v1.read_namespaced_pod_log(
            name=pod_name, namespace=namespace,
            tail_lines=settings.k8s_log_tail_lines
        )
        result["recent_logs"] = logs
    except client.ApiException:
        result["recent_logs"] = "[Could not fetch logs]"

    # Pod events
    try:
        events = v1.list_namespaced_event(
            namespace=namespace,
            field_selector=f"involvedObject.name={pod_name}",
            limit=settings.k8s_event_limit,
        )
        result["events"] = [
            {
                "type": e.type,
                "reason": e.reason,
                "message": e.message,
                "count": e.count,
                "first_seen": str(e.first_timestamp),
                "last_seen": str(e.last_timestamp),
                "source": e.source.component if e.source else None,
            }
            for e in events.items
        ]
    except client.ApiException:
        result["events"] = []

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Deployment-level collection
# ──────────────────────────────────────────────────────────────────────────────

def collect_deployment_details(deployment_name: str, namespace: str = "default") -> Dict[str, Any]:
    """Collect rollout status and replica info for a deployment."""
    if not _k8s_available:
        return {"error": "Kubernetes not available"}

    apps_v1 = client.AppsV1Api()
    result: Dict[str, Any] = {}

    try:
        dep = apps_v1.read_namespaced_deployment(name=deployment_name, namespace=namespace)
        result["name"] = deployment_name
        result["namespace"] = namespace
        result["replicas_desired"] = dep.spec.replicas
        result["replicas_available"] = dep.status.available_replicas or 0
        result["replicas_ready"] = dep.status.ready_replicas or 0
        result["replicas_unavailable"] = dep.status.unavailable_replicas or 0
        result["strategy"] = dep.spec.strategy.type if dep.spec.strategy else "Unknown"

        conditions = []
        for c in (dep.status.conditions or []):
            conditions.append({
                "type": c.type,
                "status": c.status,
                "reason": c.reason,
                "message": c.message,
            })
        result["conditions"] = conditions

    except client.ApiException as e:
        result["error"] = f"Failed to fetch deployment: {e.reason}"

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Namespace-wide collection
# ──────────────────────────────────────────────────────────────────────────────

def collect_namespace_overview(namespace: str = "default") -> Dict[str, Any]:
    """Collect a summary of all pods and events in a namespace."""
    if not _k8s_available:
        return {"error": "Kubernetes not available"}

    v1 = client.CoreV1Api()
    result: Dict[str, Any] = {"namespace": namespace}

    try:
        pods = v1.list_namespaced_pod(namespace=namespace)
        pod_summaries = []
        unhealthy = []
        for pod in pods.items:
            summary = {
                "name": pod.metadata.name,
                "phase": pod.status.phase,
                "restarts": sum(
                    (cs.restart_count or 0)
                    for cs in (pod.status.container_statuses or [])
                ),
                "ready": all(
                    cs.ready for cs in (pod.status.container_statuses or [])
                ) if pod.status.container_statuses else False,
            }
            pod_summaries.append(summary)
            if summary["phase"] != "Running" or not summary["ready"] or summary["restarts"] > 3:
                unhealthy.append(summary)

        result["total_pods"] = len(pod_summaries)
        result["unhealthy_pods"] = unhealthy

    except client.ApiException as e:
        result["error"] = f"Failed to list pods: {e.reason}"

    # Warning events
    try:
        events = v1.list_namespaced_event(
            namespace=namespace,
            field_selector="type=Warning",
            limit=settings.k8s_event_limit,
        )
        result["warning_events"] = [
            {"reason": e.reason, "message": e.message, "object": e.involved_object.name, "count": e.count}
            for e in events.items
        ]
    except client.ApiException:
        result["warning_events"] = []

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Cluster-wide health
# ──────────────────────────────────────────────────────────────────────────────

def collect_cluster_health() -> Dict[str, Any]:
    """Collect cluster-wide node health, HPA, and resource quotas."""
    if not _k8s_available:
        return {"error": "Kubernetes not available"}

    v1 = client.CoreV1Api()
    autoscaling_v1 = client.AutoscalingV1Api()
    result: Dict[str, Any] = {}

    # Nodes
    try:
        nodes = v1.list_node()
        node_list = []
        for node in nodes.items:
            conditions = {c.type: c.status for c in (node.status.conditions or [])}
            node_info = {
                "name": node.metadata.name,
                "ready": conditions.get("Ready", "Unknown"),
                "memory_pressure": conditions.get("MemoryPressure", "False") == "True",
                "disk_pressure": conditions.get("DiskPressure", "False") == "True",
                "pid_pressure": conditions.get("PIDPressure", "False") == "True",
                "allocatable_cpu": node.status.allocatable.get("cpu", "?") if node.status.allocatable else "?",
                "allocatable_memory": node.status.allocatable.get("memory", "?") if node.status.allocatable else "?",
            }
            node_list.append(node_info)
        result["nodes"] = node_list
        result["total_nodes"] = len(node_list)
        result["ready_nodes"] = sum(1 for n in node_list if n["ready"] == "True")
    except client.ApiException as e:
        result["nodes_error"] = str(e.reason)

    # HPAs across all namespaces
    try:
        hpas = autoscaling_v1.list_horizontal_pod_autoscaler_for_all_namespaces()
        hpa_list = []
        for hpa in hpas.items:
            hpa_list.append({
                "name": hpa.metadata.name,
                "namespace": hpa.metadata.namespace,
                "min_replicas": hpa.spec.min_replicas,
                "max_replicas": hpa.spec.max_replicas,
                "current_replicas": hpa.status.current_replicas,
                "desired_replicas": hpa.status.desired_replicas,
                "current_cpu_utilization": hpa.status.current_cpu_utilization_percentage,
                "target_cpu_utilization": hpa.spec.target_cpu_utilization_percentage,
            })
        result["hpas"] = hpa_list
    except client.ApiException:
        result["hpas"] = []

    # Resource Quotas across all namespaces
    try:
        quotas = v1.list_resource_quota_for_all_namespaces()
        quota_list = []
        for q in quotas.items:
            quota_list.append({
                "name": q.metadata.name,
                "namespace": q.metadata.namespace,
                "hard": dict(q.status.hard) if q.status.hard else {},
                "used": dict(q.status.used) if q.status.used else {},
            })
        result["resource_quotas"] = quota_list
    except client.ApiException:
        result["resource_quotas"] = []

    return result
