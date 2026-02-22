# ImagePullBackOff

## Symptoms

- Pod stuck in ImagePullBackOff or ErrImagePull status
- `kubectl describe pod` shows "Failed to pull image" event

## Common Causes

1. **Wrong image name or tag** — typo in image URI, tag doesn't exist
2. **Private registry auth missing** — no imagePullSecret configured
3. **Registry rate limit** — Docker Hub rate limiting anonymous pulls
4. **Network issue** — node cannot reach the container registry
5. **Image deleted** — tag was overwritten or repo was removed

## Diagnostic Commands

```bash
# Check events for the pod
kubectl describe pod <pod-name> -n <namespace> | grep -A10 "Events"

# Verify the image exists (Docker Hub example)
docker manifest inspect <image>:<tag>

# Check imagePullSecrets
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.spec.imagePullSecrets}'

# Check if secret exists
kubectl get secret <secret-name> -n <namespace>
```

## Fix Steps

1. Verify the image name and tag are correct
2. Create imagePullSecret: `kubectl create secret docker-registry regcred --docker-server=<registry> --docker-username=<user> --docker-password=<pass> -n <namespace>`
3. Add the secret to the pod spec or service account
4. If using ECR, ensure the IRSA role has ecr:GetAuthorizationToken permission
5. If Docker Hub rate limit, consider using a pull-through cache or ECR mirror
