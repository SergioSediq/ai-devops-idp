# OOMKilled

## Symptoms

- Container terminated with exit code 137
- `kubectl describe pod` shows reason: OOMKilled
- dmesg on node shows kernel OOM killer invoked

## Common Causes

1. **Memory limit too low** — container needs more memory than spec allows
2. **Memory leak** — application gradually consumes more memory until killed
3. **Large data processing** — loading entire datasets into memory
4. **JVM heap not aligned** — Java apps with -Xmx exceeding container limit

## Diagnostic Commands

```bash
# Check the termination reason
kubectl describe pod <pod-name> -n <namespace> | grep -A5 "Last State"

# Check resource limits
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].resources}'

# Check node memory pressure
kubectl describe node <node-name> | grep -A5 "Conditions"

# Check actual memory usage (requires metrics-server)
kubectl top pod <pod-name> -n <namespace>
```

## Fix Steps

1. Increase `resources.limits.memory` in the deployment manifest
2. Profile the application for memory leaks
3. For JVM apps, set `-Xmx` to 75% of container memory limit
4. Consider using Vertical Pod Autoscaler (VPA)
5. If memory leak, add restart policy with a resource limit as a safety net
