FROM node:24-bookworm-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
# Next.js embeds rewrites during the build, so this must be a build argument.
ARG API_URL=http://envocab-api:8000
ENV API_URL=${API_URL}
RUN npm run build

FROM node:24-bookworm-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=build --chown=node:node /app/ ./
USER node
EXPOSE 3000
CMD ["node", "node_modules/next/dist/bin/next", "start", "--hostname", "0.0.0.0", "--port", "3000"]
