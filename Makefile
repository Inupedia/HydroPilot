.PHONY: setup dev dev-web api-test core-test verify api-dev db-up db-down studio-test studio-build web-test web-build

setup:
	npm run setup

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

studio-test:
	cd apps/studio && npm test

studio-build:
	cd apps/studio && npm run build:web

web-test: studio-test

web-build: studio-build
