# 🚀 AI-Native Internal Developer Platform (IDP)

> Production-grade Internal Developer Platform with AI-powered DevOps diagnostics, built on **AWS EKS**, **Backstage**, **ArgoCD**, and **Google Gemini**.

---

## 📐 Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       Backstage Portal (:7007)                   │
│           ChatComponent.tsx  →  POST /diagnose API               │
│           Scaffolder Templates  |  Service Catalog               │
└──────────────────────┬───────────────────────────────────────────┘
                       │ HTTP
┌──────────────────────▼───────────────────────────────────────────┐
│                   AI DevOps Agent (:8000)  [FastAPI]              │
│                                                                   │
│  ┌──────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │ Log Analyzer  │  │  K8s Collector  │  │   RAG Chain         │  │
│  │ (regex-based  │  │  (live cluster  │  │   (Gemini LLM +     │  │
│  │  classifier)  │  │   API queries)  │  │    Runbook search)  │  │
│  └──────┬───────┘  └────────┬────────┘  └──────────┬──────────┘  │
│         └──────────────┬────┘                      │             │
│                        ▼                           ▼             │
│              Combined Context  ────────►  Structured JSON        │
│              (errors + k8s data)          DiagnoseResponse       │
└──────────────────────┬───────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────┐
│                    Infrastructure (Terraform)                     │
│  AWS EKS  |  RDS PostgreSQL  |  S3  |  IRSA  |  Security Groups │
│  ArgoCD (GitOps)  |  OPA Gatekeeper (Policy)  |  NetworkPolicy   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
idp-platform/
│
├── ai-agent/                          # 🤖 AI Diagnostics Engine (Python/FastAPI)
│   ├── main.py                        #    FastAPI app — /diagnose, /cluster-health, /suggest-runbook, /health
│   ├── rag_chain.py                   #    RAG pipeline — Gemini LLM + runbook retrieval + JSON output
│   ├── config.py                      #    Centralized settings (pydantic-settings)
│   ├── models.py                      #    Pydantic request/response models + enums
│   ├── k8s_collector.py               #    Live Kubernetes data collector (pods, deployments, nodes)
│   ├── log_analyzer.py                #    Regex-based error classifier (OOM, CrashLoop, etc.)
│   ├── runbooks/                      #    📚 Markdown runbooks for common failures
│   │   ├── crashloopbackoff.md        #       CrashLoopBackOff diagnosis & fix steps
│   │   ├── oomkilled.md               #       OOMKilled (exit code 137) guide
│   │   ├── imagepullbackoff.md        #       ImagePullBackOff / registry auth issues
│   │   └── terraform-state-lock.md    #       Terraform DynamoDB lock troubleshooting
│   ├── Dockerfile                     #    Multi-stage build, non-root user, HEALTHCHECK
│   ├── .dockerignore                  #    Excludes dev files from Docker context
│   ├── requirements.txt              #    Pinned Python dependencies
│   ├── pyproject.toml                #    Ruff, pytest, mypy config
│   └── tests/                        #    Unit tests (log_analyzer, rag_chain, API)
│
├── portal/                            # 🌐 Backstage Developer Portal
│   ├── Dockerfile                     #    Node 18 multi-stage build for Backstage
│   ├── plugins/
│   │   └── ai-ops-assistant/
│   │       └── src/components/
│   │           └── ChatComponent.tsx   #    AI chat UI — severity banners, copyable commands
│   └── scaffolder-templates/
│       └── react-ssr-template.yaml    #    Backstage scaffolder template for React SSR apps
│
├── infra/                             # 🏗️ Terraform Infrastructure-as-Code
│   ├── main.tf                        #    VPC, EKS, RDS, S3, IRSA (using TF modules)
│   ├── variables.tf                   #    Parameterized inputs with validation rules
│   ├── backend.tf                     #    S3 remote state + DynamoDB locking
│   ├── outputs.tf                     #    Cluster endpoint, RDS URI, subnet IDs, IRSA ARN
│   └── security.tf                    #    Security groups — RDS, EKS workers, Portal ALB
│
├── gitops/                            # ☸️ Kubernetes Manifests & GitOps
│   ├── base/
│   │   ├── ai-agent.yaml              #    Deployment (2 replicas) + Service + ServiceAccount
│   │   ├── namespace.yaml             #    Namespace + Secrets
│   │   └── network-policy.yaml        #    Ingress/egress restrictions
│   ├── argocd/
│   │   └── application.yaml           #    ArgoCD Application — auto-sync, self-heal, retry
│   └── policies/
│       └── opa-loadbalancer-tag.yaml  #    OPA Gatekeeper — enforce cost tags on LoadBalancers
│
├── .github/workflows/
│   └── ci.yml                         # 🔄 CI/CD — lint, test, build, validate, security scan
│
├── docker-compose.yml                 # 🐳 Local dev stack (AI Agent + PostgreSQL + ChromaDB)
├── .env.example                       #    Environment variable template
└── README.md                          #    This file
```

---

## 🐳 Docker — Local Development

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

### 1. Setup Environment

```bash
# Clone the repo
git clone https://github.com/YOUR_ORG/idp-platform.git
cd idp-platform

# Create your .env file
cp .env.example .env

# Edit .env and add your Gemini API key
nano .env
```

### 2. Start All Services

```bash
# Build and start everything (AI Agent + PostgreSQL + ChromaDB)
docker compose up --build

# Or run in detached mode
docker compose up --build -d
```

### 3. Verify Services

```bash
# Check all containers are healthy
docker compose ps

# Test AI Agent health
curl http://localhost:8000/health

# Test a diagnosis
curl -X POST http://localhost:8000/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "error_message": "Pod my-app-xyz is in CrashLoopBackOff with exit code 137",
    "namespace": "production",
    "pod_name": "my-app-xyz"
  }'

# Search runbooks
curl -X POST http://localhost:8000/suggest-runbook \
  -H "Content-Type: application/json" \
  -d '{"error_message": "OOMKilled", "top_k": 3}'
```

### 4. Stop Services

```bash
docker compose down          # Stop containers
docker compose down -v       # Stop + remove volumes (clean slate)
```

### Individual Docker Builds

```bash
# Build AI Agent only
docker build -t idp-ai-agent:latest ./ai-agent

# Run AI Agent standalone
docker run -p 8000:8000 \
  -e GOOGLE_API_KEY=your-key \
  -e LOG_LEVEL=DEBUG \
  idp-ai-agent:latest

# Build Portal (requires Backstage scaffolding first)
docker build -t idp-portal:latest ./portal
```

### Docker Compose Services

| Service | Port | Image | Purpose |
|---|---|---|---|
| `ai-agent` | `8000` | Custom (Python 3.11) | AI diagnostics engine |
| `postgres` | `5432` | `postgres:14-alpine` | Backstage backend database |
| `chromadb` | `8100` | `chromadb/chroma` | Vector store for RAG runbook search |

---

## 🤖 AI Agent — API Reference

### `POST /diagnose` — Full AI Diagnosis

The primary endpoint. Classifies errors, collects live K8s data, and returns structured fixes.

**Request:**

```json
{
  "error_message": "CrashLoopBackOff: back-off 5m0s restarting failed container",
  "pod_name": "api-server-7d9f8b6c5-xk4jn",
  "namespace": "production",
  "deployment_name": "api-server",
  "include_cluster_health": true
}
```

**Response:**

```json
{
  "request_id": "a1b2c3d4",
  "timestamp": "2026-02-19T10:30:00.000Z",
  "severity": "HIGH",
  "error_category": "CrashLoopBackOff",
  "root_cause": "Container exits with code 137 (OOMKilled) due to memory limit of 256Mi",
  "explanation": "The container is being killed by the Linux OOM killer because...",
  "fix_commands": [
    {
      "command": "kubectl set resources deployment/api-server -n production --limits=memory=512Mi",
      "description": "Increase memory limit to 512Mi",
      "risk_level": "LOW"
    }
  ],
  "prevention_tips": [
    "Set memory requests to the p95 usage observed in monitoring",
    "Enable Vertical Pod Autoscaler (VPA) in recommendation mode"
  ],
  "related_runbooks": ["oomkilled.md", "crashloopbackoff.md"]
}
```

### `GET /cluster-health` — Cluster Health Summary

```bash
curl http://localhost:8000/cluster-health
```

Returns node status, memory/disk pressure, and overall cluster health.

### `POST /suggest-runbook` — Runbook Search

```json
{
  "error_message": "terraform state lock",
  "top_k": 3
}
```

Returns relevant internal runbooks ranked by keyword relevance.

### `GET /health` — Liveness Probe

```json
{
  "status": "ok",
  "service": "ai-devops-assistant",
  "version": "2.0.0",
  "k8s_connected": true,
  "llm_configured": true
}
```

---

## 🏗️ Infrastructure — Terraform

### Prerequisites

- [Terraform ≥ 1.6](https://developer.hashicorp.com/terraform/install)
- AWS CLI configured with appropriate permissions
- S3 bucket + DynamoDB table for remote state (see below)

### Remote State Setup (one-time)

```bash
# Create the S3 bucket for Terraform state
aws s3api create-bucket \
  --bucket idp-platform-terraform-state \
  --region ap-south-1 \
  --create-bucket-configuration LocationConstraint=ap-south-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket idp-platform-terraform-state \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name idp-platform-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-south-1
```

### Deploy Infrastructure

```bash
cd infra

terraform init
terraform plan -var="rds_master_password=YourSecurePassword123!"
terraform apply -var="rds_master_password=YourSecurePassword123!"
```

### Key Resources Created

| Resource | Description |
|---|---|
| **VPC** | Dedicated network with public/private subnets across 2 AZs |
| **EKS Cluster** | Managed Kubernetes (v1.27) with 1–3 `t3.medium` nodes |
| **RDS PostgreSQL** | PostgreSQL 14 database for Backstage catalog |
| **S3 Bucket** | Artifact storage with unique suffix |
| **IRSA Role** | IAM Role for AI Agent ServiceAccount → CloudWatch read |
| **Security Groups** | RDS (PG from EKS only), EKS workers, Portal ALB |

### Key Terraform Variables

| Variable | Default | Description |
|---|---|---|
| `project_name` | `idp-platform` | Resource naming prefix |
| `environment` | `production` | `production`, `staging`, or `development` |
| `aws_region` | `ap-south-1` | AWS region |
| `eks_cluster_version` | `1.28` | EKS Kubernetes version |
| `eks_node_instance_types` | `["t3.medium"]` | Worker node types |
| `rds_instance_class` | `db.t3.small` | RDS instance size |
| `rds_master_password` | — | **Required**, sensitive |

---

## ☸️ GitOps — ArgoCD

### Install ArgoCD

```bash
# Create ArgoCD namespace and install
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Get the initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Port-forward the UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

### Deploy the Application

```bash
# Apply the ArgoCD Application manifest
kubectl apply -f gitops/argocd/application.yaml
```

ArgoCD will automatically sync the K8s manifests from `gitops/base/`, including:

- **AI Agent Deployment** — 2 replicas with health probes and resource limits
- **ServiceAccount** — with IRSA annotation for AWS access
- **NetworkPolicy** — restricts ingress to portal only, egress to DNS + HTTPS + K8s API
- **Namespace** — `idp-platform` with managed labels

### OPA Gatekeeper Policy

```bash
# Install Gatekeeper
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/release-3.14/deploy/gatekeeper.yaml

# Apply the cost-control policy
kubectl apply -f gitops/policies/opa-loadbalancer-tag.yaml
```

This blocks any `LoadBalancer` Service that doesn't include AWS cost-control tags.

---

## 🔄 CI/CD — GitHub Actions

The `.github/workflows/ci.yml` pipeline runs on every push/PR:

| Job | Trigger | What it does |
|---|---|---|
| 🔍 **Lint & Test** | Push + PR | Ruff, Bandit, pip-audit, mypy, pytest (coverage ≥20%) |
| 🐳 **Build & Push** | Push to `main` | Docker build → push to Amazon ECR |
| 🏗️ **Terraform Validate** | Push + PR | `terraform fmt -check` + `terraform validate` |
| ☸️ **K8s Validate** | Push + PR | kubeconform validation on GitOps manifests |
| 🔒 **Security Scan** | Push to `main` | Trivy CVE scan — **fails on CRITICAL/HIGH** |

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `AWS_ROLE_ARN` | IAM Role ARN for GitHub Actions OIDC |

---

## 🌐 Portal — Backstage

### Setup Backstage (first time)

```bash
cd portal

# Scaffold the base Backstage app
npx @backstage/create-app@latest

# Install the AI Ops plugin dependencies
cd plugins/ai-ops-assistant
npm install

# Return to portal root and start
cd ../..
npm run dev
```

The `ChatComponent.tsx` plugin provides:

- 🎨 **Severity-colored banners** — CRITICAL (red), HIGH (orange), MEDIUM (yellow), LOW (green)
- 📋 **One-click copy** on all fix commands
- ⚠️ **Risk indicators** — LOW/MEDIUM/HIGH per command
- 🛡️ **Prevention tips** section
- 📚 **Runbook links** — clickable badges for related runbooks
- ⏳ **Loading animation** with error handling

---

## ⚙️ Environment Variables

### AI Agent

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | **Yes** | — | Google Gemini API key |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Gemini model name |
| `RATE_LIMIT_REQUESTS` | No | `60` | Max requests per minute for /diagnose, /suggest-runbook |
| `LOG_LEVEL` | No | `INFO` | Python log level (DEBUG/INFO/WARNING/ERROR) |
| `APP_HOST` | No | `0.0.0.0` | FastAPI bind host |
| `APP_PORT` | No | `8000` | FastAPI bind port |
| `CORS_ORIGINS` | No | `*` | Comma-separated allowed origins |
| `LLM_TEMPERATURE` | No | `0.1` | LLM response temperature (0.0–1.0) |
| `LLM_MAX_OUTPUT_TOKENS` | No | `2048` | Max tokens in LLM response |
| `RUNBOOK_DIR` | No | `runbooks` | Path to runbook markdown files |

### PostgreSQL (docker-compose)

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | `backstage_dev_pass` | Database password |

### AWS / Terraform

| Variable | Description |
|---|---|
| `AWS_REGION` | AWS region (default: `ap-south-1`) |
| `AWS_ACCESS_KEY_ID` | AWS access key (or use IAM roles) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key (or use IAM roles) |

---

## 🔒 Security

| Layer | Implementation |
|---|---|
| **Container** | Non-root user (`appuser`), multi-stage Docker build |
| **Network** | K8s NetworkPolicy — AI agent only reachable from portal |
| **IAM** | IRSA — pods get scoped AWS permissions via ServiceAccount |
| **Database** | Security group — PostgreSQL only from EKS nodes |
| **Secrets** | K8s Secrets (upgrade to External Secrets Operator for production) |
| **Policy** | OPA Gatekeeper — blocks untagged LoadBalancers |
| **CI/CD** | Trivy scans for CRITICAL/HIGH CVEs on every build |
| **ALB** | Dedicated security group — HTTPS + HTTP redirect only |
| **State** | Terraform remote state encrypted in S3 with DynamoDB locking |

---

## 📚 Documentation

- **[API Reference](docs/API.md)** — Full API docs; also see Swagger UI at `/docs`
- **[Secrets Management](docs/SECRETS.md)** — External Secrets, IRSA, and secret handling

## 📚 Runbooks

Pre-built diagnostic runbooks in `ai-agent/runbooks/`:

| Runbook | Covers |
|---|---|
| `crashloopbackoff.md` | App crashes, bad probes, missing deps, exit codes |
| `oomkilled.md` | Exit code 137, memory limits, JVM heap, VPA |
| `imagepullbackoff.md` | Registry auth, rate limits, ECR permissions |
| `terraform-state-lock.md` | Stale locks, force-unlock, CI/CD timeouts |

The AI agent automatically searches these during diagnosis and references them in responses.

---

## 🛠️ Development

```bash
# Run AI Agent locally (without Docker)
cd ai-agent
pip install -r requirements.txt
export GOOGLE_API_KEY="your-key"
python main.py                        # http://localhost:8000

# Run tests (use empty GOOGLE_API_KEY for mock mode)
export GOOGLE_API_KEY=""
pytest tests/ -v

# Lint & format
ruff check .
ruff format .

# Terraform validate
cd infra
terraform init -backend=false
terraform validate
terraform fmt -check -recursive
```

---

## 📝 License

MIT
