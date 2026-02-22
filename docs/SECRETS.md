# Secrets Management

This document describes how to manage secrets for the IDP Platform.

## Current approach (plain K8s Secrets)

The `gitops/base/namespace.yaml` defines a Secret `ai-agent-secrets` with placeholder values. For development or quick setups:

1. Base64-encode your Google API key: `echo -n "your-key" | base64`
2. Replace `REPLACE_WITH_BASE64_ENCODED_KEY` in `namespace.yaml` with the output
3. **Never commit real secrets to git.** Use a private fork, sealed secrets, or External Secrets.

## Recommended: External Secrets Operator

For production, use [External Secrets Operator](https://external-secrets.io/) to sync secrets from AWS Secrets Manager, HashiCorp Vault, or GCP Secret Manager into Kubernetes.

### Example: AWS Secrets Manager

1. Store the secret in AWS Secrets Manager
2. Install External Secrets Operator
3. Create an `ExternalSecret` that references the AWS secret and creates `ai-agent-secrets` in the `idp-platform` namespace

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: ai-agent-secrets
  namespace: idp-platform
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: ai-agent-secrets
  data:
    - secretKey: google-api-key
      remoteRef:
        key: idp-platform/ai-agent
        property: GOOGLE_API_KEY
```

4. Remove the static Secret from `namespace.yaml` or let External Secrets manage it

## IRSA and EKS

The AI Agent uses IRSA (IAM Roles for Service Accounts) for AWS access. The Terraform output `ai_agent_role_arn` must be annotated on the ServiceAccount. See `gitops/base/ai-agent.yaml` and ensure the `eks.amazonaws.com/role-arn` annotation matches the Terraform-generated role ARN.
