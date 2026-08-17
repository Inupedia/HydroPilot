PYTHON ?= python3

.PHONY: db-up db-down api-test api-dev

db-up:
	docker compose up -d db

db-down:
	docker compose down

api-test:
	cd apps/api && $(PYTHON) -m pytest tests -v

api-dev:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m uvicorn hydropilot_api.main:app --reload --host 0.0.0.0 --port 8000
