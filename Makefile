.PHONY: help lint test fmt tf-validate

help:
	@echo "IDP Platform — Common targets"
	@echo "  make lint        - Run Ruff lint on ai-agent"
	@echo "  make fmt         - Run Ruff format on ai-agent"
	@echo "  make test        - Run pytest in ai-agent"
	@echo "  make tf-validate - Terraform init + validate in infra/"
	@echo "  make docker-up   - Start docker-compose"

lint:
	cd ai-agent && ruff check .

fmt:
	cd ai-agent && ruff format .

test:
	cd ai-agent && GOOGLE_API_KEY= pytest tests/ -v --tb=short

tf-validate:
	cd infra && terraform init -backend=false && terraform validate

docker-up:
	docker compose up --build -d
