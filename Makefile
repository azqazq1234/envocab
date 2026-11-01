.PHONY: setup dev ui server migrate check dictionary

setup:
	cd ui && npm ci
	cd server && uv sync --locked
	@test -f server/.env || cp server/.env.example server/.env
	@test -f ui/.env.local || cp ui/.env.example ui/.env.local
	@test -f server/data/ecdict.sqlite3 || $(MAKE) dictionary
	$(MAKE) migrate

dictionary:
	cd server && uv run python -m app.import_dictionary

migrate:
	cd server && uv run alembic upgrade head

ui:
	cd ui && npm run dev

server:
	cd server && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Start the ui and server together; Ctrl-C stops both.
dev:
	$(MAKE) -j2 server ui

check:
	cd server && uv run ruff check app migrations tests && uv run pytest -q
	cd ui && npm run lint && npm run typecheck && npm test && npm run build
