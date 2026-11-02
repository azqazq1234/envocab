#!/bin/sh
set -eu

# A failed migration prevents the new backend from starting.
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
