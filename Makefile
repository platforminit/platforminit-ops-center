.PHONY: dev-api dev-ui test lint check-plugins

dev-api:
	./scripts/dev-api.sh

dev-ui:
	./scripts/dev-ui.sh

test:
	cd backend && uv run pytest -q

lint:
	cd backend && uv run ruff check .
	cd frontend && pnpm lint

check-plugins:
	/usr/lib/nagios/plugins/check_http -H example.com
	/usr/lib/nagios/plugins/check_disk -w 20% -c 10% -p /

.PHONY: bootstrap verify

bootstrap:
	./scripts/bootstrap-dev.sh

verify:
	./scripts/verify-dev.sh
