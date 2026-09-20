# syntax=docker/dockerfile:1
#
# Multi-stage build for the Next.js frontend.
#
# Stages:
#   base    - shared minimal image, no source code
#   deps    - installs npm dependencies (its own layer, cached across builds
#             as long as package*.json don't change)
#   dev     - target for local docker-compose development: full dependency
#             tree + `next dev`. Source is expected to be bind-mounted by
#             docker-compose so edits hot-reload without a rebuild; the COPY
#             here only makes the image runnable standalone (e.g. `docker run`
#             without a mount, or CI smoke-checks).
#   builder - installs deps, copies source, runs `next build`. Thanks to
#             `output: "standalone"` in next.config.ts this produces a
#             self-contained server bundle with only the runtime deps it needs.
#   runner  - final, production stage (default target): copies only the
#             standalone build output, runs as a non-root user. No dev
#             tooling, no full node_modules, no source maps beyond what
#             Next.js includes.
#
# Rationale for a separate `dev` stage instead of reusing `runner` for local
# dev: the production image intentionally excludes dev dependencies, the
# source tree, and a shell useful for debugging so it deploys nothing more
# than required. Local development instead needs fast rebuilds, source
# watching, and dev dependencies (eslint, types) available — a different
# enough runtime shape to warrant its own stage rather than flags/env
# branching inside one image. docker-compose selects the stage via
# `build.target: dev`; omitting `target` builds the production `runner` stage.

ARG NODE_VERSION=20-alpine

# ---- base -------------------------------------------------------------
FROM node:${NODE_VERSION} AS base
WORKDIR /app
# Required at runtime by `next start`/standalone server and at build time by
# `next build`; also read client-side after being inlined into the bundle.
ENV NEXT_TELEMETRY_DISABLED=1

# ---- deps ---------------------------------------------------------------
FROM base AS deps
COPY package.json package-lock.json ./
RUN npm ci

# ---- dev ------------------------------------------------------------------
FROM base AS dev
ENV NODE_ENV=development
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Non-root: the `node` image ships an unprivileged `node` user out of the box.
# `.next` must exist (owned by `node`) before the volume mount below attaches
# to it — docker-compose mounts a named volume at /app/.next for build-cache
# persistence, and an empty named volume inherits ownership from whatever
# already exists at that path in the image. Without this, Docker creates the
# mount point as root and `next dev` fails with EACCES trying to write to it.
RUN mkdir -p .next && chown -R node:node /app
USER node
EXPOSE 3000
CMD ["npm", "run", "dev"]

# ---- builder --------------------------------------------------------------
FROM base AS builder
ENV NODE_ENV=production
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* values are inlined into the client bundle at build time, so
# the build needs a value even if it's only a dev-network default; override
# with --build-arg for other environments.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
# Server-only (no `NEXT_PUBLIC_`, never reaches the client bundle) — but
# `next build` actually executes `generateStaticParams`/Server Component
# fetches at build time (true SSG for `/[lang]/o-mnie`, `/[lang]/posty`,
# `/[lang]/posty/[slug]`), so the API must be reachable from *this* build
# stage, not just at runtime. Default mirrors NEXT_PUBLIC_API_URL for a
# bare `docker build` without compose network; pass
# `--build-arg API_URL=http://backend:8000 --network <compose-network>`
# to build against the real API (e.g. local compose's `backend` service).
ARG API_URL=http://localhost:8000
ENV API_URL=${API_URL}
RUN npm run build

# ---- runner (production, default) -----------------------------------------
FROM base AS runner
ENV NODE_ENV=production
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
# Runtime fallback for on-demand ISR of params not covered by build-time
# `generateStaticParams` (e.g. a slug published after the last build) —
# should normally be overridden per environment same as at build time.
ARG API_URL=http://localhost:8000
ENV API_URL=${API_URL}

# `node` user/group already exist in the official node images.
COPY --from=builder /app/public ./public
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static

USER node
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
