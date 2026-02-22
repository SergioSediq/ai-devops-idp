# Contributing to IDP Platform

Thank you for contributing to the IDP Platform! This document covers how to set up your environment and submit changes.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for portal)
- Docker & Docker Compose
- Terraform ≥ 1.6 (for infra changes)
- [Google Gemini API key](https://aistudio.google.com/app/apikey)

### AI Agent (Python)

```bash
cd ai-agent
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx ruff  # dev deps
cp ../.env.example .env  # add GOOGLE_API_KEY
python main.py
```

### Run Tests

```bash
cd ai-agent
export GOOGLE_API_KEY=""  # mock mode
pytest tests/ -v
```

### Linting & Formatting

```bash
cd ai-agent
ruff check .
ruff format .
```

### Pre-commit Hooks

Install [pre-commit](https://pre-commit.com/) and run:

```bash
pre-commit install
```

This will run Ruff and Terraform fmt on staged files.

## Pull Request Process

1. Fork the repo and create a feature branch
2. Make your changes with tests where applicable
3. Run tests and lint locally
4. Push and open a PR
5. Ensure CI passes (lint, tests, Terraform validate, K8s manifest validation)

## Code Style

- **Python**: Ruff for lint and format; follow type hints where practical
- **Terraform**: `terraform fmt`; use variables for configurable values
- **YAML**: 2-space indentation, kebab-case for Kubernetes resources

## Reporting Issues

Use GitHub Issues with labels (`bug`, `enhancement`, `documentation`). Include:

- Reproducible steps
- Expected vs actual behavior
- Environment (OS, Python/Node version, etc.)
