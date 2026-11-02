FROM python:3.15-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/server
COPY server/pyproject.toml server/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
ENV PATH="/app/server/.venv/bin:${PATH}"
COPY server/ ./
COPY rawlist/ /app/rawlist/
# This read-only dictionary is separate from the migrated PostgreSQL data.
RUN python -m app.import_dictionary
COPY deploy/start-server.sh /app/start-server.sh
RUN useradd --create-home --uid 10001 app && chmod 755 /app/start-server.sh && chown -R app:app /app
USER app
EXPOSE 8000
ENTRYPOINT ["/app/start-server.sh"]
