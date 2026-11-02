# Coolify deployment

This Compose application contains only Next.js and FastAPI. It uses the existing
PostgreSQL database restored through Coolify; it does not create a database or
publish container ports on the host.

## Configuration

- Git branch: `main`
- Build strategy: Docker Compose
- Base directory: `/`
- Compose location: `/compose.yaml`
- Both services and the database must be attached to the existing `coolify` Docker
  network. The backend has the network alias `envocab-api`.
- Set `DATABASE_URL` in Coolify's application environment variables using the
  database's internal URL. Change its scheme from `postgres://` or `postgresql://`
  to `postgresql+psycopg://`, preserving the encoded credentials, hostname, port,
  and database name. Never commit the URL or password.
- Expose only the `ui` service through the site's reverse proxy, using its internal
  port `3000`. PostgreSQL and FastAPI have no public host port mappings.
- This server uses an existing host Caddy rather than Coolify's managed proxy.
  Public website routing therefore needs a separate host Caddy configuration;
  selecting a domain in Coolify alone does not configure the existing host Caddy.

## First deployment and updates

The backend image downloads the pinned ECDICT snapshot during its build. The
PostgreSQL backup already restored from the Mac contains the vocabulary data.
The backend runs `alembic upgrade head` on startup before starting Uvicorn. Take a
database backup before deploying schema changes. An application rollback does not
automatically roll back database migrations.

The frontend's `/api` rewrite is set at build time to
`http://envocab-api:8000`; a new container image is required to change it.

## Validation

On the Ubuntu server, after entering the real connection URL in Coolify, build and
deploy the selected commit. Review build logs and confirm both services become
healthy. Both health checks exercise `/api/groups`; the frontend check also tests
the frontend-to-backend rewrite and the backend-to-database connection.

For standalone Compose usage, supply `DATABASE_URL` through an untracked `.env`,
ensure the external `coolify` network and PostgreSQL exist, then run
`docker compose up -d --build`. Do not run this alongside Coolify's deployment of
the same application: the network alias must identify a single backend.
