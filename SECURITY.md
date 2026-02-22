# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | :white_check_mark: |
| 1.x     | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a vulnerability:

1. **Do not** open a public GitHub issue
2. Email a concise description to the maintainers (or use GitHub Security Advisories if you have access)
3. Include steps to reproduce and impact assessment
4. Allow reasonable time for a fix before public disclosure

We will acknowledge receipt and provide updates on the fix timeline.

## Security Measures in This Project

- **Container**: Non-root user, minimal base images
- **Secrets**: Use Kubernetes Secrets or External Secrets Operator — never commit credentials
- **Network**: NetworkPolicy restricts AI agent to portal ingress
- **IAM**: IRSA for least-privilege AWS access
- **CI**: Trivy scans for CRITICAL/HIGH CVEs; failures block builds
- **Terraform**: Remote state in S3 with encryption and DynamoDB locking
