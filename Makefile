.PHONY: lint unit build validate-sso integration integration-sso ui check

lint:
	shellcheck scripts/*.sh
	cd platform/discovery && uv run --group dev ruff check . && uv run --group dev ruff format --check .

unit:
	cd platform/discovery && uv run --group dev pytest

build: validate-sso
	docker compose config -q
	docker compose build

validate-sso:
	OIDC_COOKIE_SECRET=abcdefghijklmnopqrstuvwxyz123456 \
	OIDC_CLIENT_ID=ci-client OIDC_CLIENT_SECRET=ci-secret \
	OIDC_ISSUER_URL=https://auth.example.com/application/o/artifact-platform/ \
	SITE_ADDRESS=artifacts.example.com MANAGEMENT_API_TOKEN=ci-management-token \
	docker compose -f docker-compose.yml -f docker-compose.sso.yml config -q
	docker run --rm \
		-v "$$PWD/platform/oauth2-proxy/oauth2-proxy.cfg:/etc/oauth2-proxy/oauth2-proxy.cfg:ro" \
		-e OAUTH2_PROXY_OIDC_ISSUER_URL=https://auth.example.com/application/o/artifact-platform/ \
		-e OAUTH2_PROXY_CLIENT_ID=ci-client -e OAUTH2_PROXY_CLIENT_SECRET=ci-secret \
		-e OAUTH2_PROXY_COOKIE_SECRET=abcdefghijklmnopqrstuvwxyz123456 \
		-e OAUTH2_PROXY_REDIRECT_URL=https://artifacts.example.com/oauth2/callback \
		quay.io/oauth2-proxy/oauth2-proxy:v7.15.3 \
		--config=/etc/oauth2-proxy/oauth2-proxy.cfg \
		--allowed-group=artifact-platform-admins --config-test

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
