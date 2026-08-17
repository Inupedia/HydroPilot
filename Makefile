.PHONY: setup dev dev-web api-test core-test verify api-dev db-up db-down web-test web-build

setup:
	python scripts/setup_dev.py

dev:
	npm run dev

dev-web:
	npm run dev:web

api-test:
	PYTHONPATH=apps/api/src:packages/hydropilot-core/src:. pytest apps/api/tests -q

core-test:
	PYTHONPATH=packages/hydropilot-core/src pytest packages/hydropilot-core/tests -q

verify: core-test api-test
	python scripts/check_fixture.py data/demo/sacramento_v0_1.json

api-dev:
	cd apps/api && uvicorn hydropilot_api.main:app --reload --app-dir src

db-up:
	docker compose up -d postgis

db-down:
	docker compose down

web-test:
	cd apps/web && npm test -- --run

web-build:
	cd apps/web && npm run build
