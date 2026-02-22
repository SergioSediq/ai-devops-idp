# CrashLoopBackOff

## Symptoms

- Pod restarts repeatedly with increasing backoff delays
- `kubectl get pods` shows STATUS = CrashLoopBackOff with high RESTARTS count

## Common Causes

1. **Application crash on startup** — missing env vars, bad config, unhandled exception
2. **Liveness probe misconfigured** — probe path wrong, port mismatch, initialDelaySeconds too low
3. **OOMKilled** — container exceeds memory limits
4. **Missing dependencies** — database unavailable, external service unreachable
5. **File permission issues** — container runs as non-root but needs root-owned files

## Diagnostic Commands

```bash
# Check pod events
kubectl describe pod <pod-name> -n <namespace>

# Check container logs (previous crashed instance)
kubectl logs <pod-name> -n <namespace> --previous

# Check exit code
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}'
```

## Fix Steps

1. Check logs from the previous container instance with `--previous` flag
2. Look at the exit code: 137 = OOMKilled, 1 = app error, 127 = command not found
3. Verify all required ConfigMaps and Secrets exist
4. Increase `initialDelaySeconds` on liveness probe if the app is slow to start
5. Increase memory limits if OOMKilled
