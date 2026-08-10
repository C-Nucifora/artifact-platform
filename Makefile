.PHONY: lint unit build integration integration-sso ui check

lint:
	shellcheck scripts/*.sh
	cd platform/discovery && uv run --group dev ruff check . && uv run --group dev ruff format --check .

unit:
	cd platform/discovery && uv run --group dev pytest

build:
	docker compose config -q
	docker compose build

integration:
	docker compose -f docker-compose.test.yml up -d --wait
	uv run --project platform/discovery --group dev pytest tests/integration/test_http.py; \
	status=$$?; \
	docker compose -f docker-compose.test.yml down -v; \
	exit $$status

integration-sso:
	docker compose -f docker-compose.sso.test.yml up -d --wait
	uv run --project platform/discovery --group dev pytest tests/integration/test_sso_http.py; \
	status=$$?; \
	docker compose -f docker-compose.sso.test.yml down -v; \
	exit $$status

ui:
	npm test

check: lint unit build integration integration-sso ui
