FROM node:22.22.0-bookworm-slim@sha256:dd9d21971ec4395903fa6143c2b9267d048ae01ca6d3ea96f16cb30df6187d94 AS node

FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c AS dependencies
WORKDIR /opt/hyperglass
COPY --from=node /usr/local/ /usr/local/
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config libcairo2-dev libffi-dev curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN npm install --global pnpm@10.11.0
ENV HYPERGLASS_APP_PATH=/etc/hyperglass \
    HYPERGLASS_HOST=0.0.0.0 \
    HYPERGLASS_PORT=8001 \
    HYPERGLASS_DEBUG=false \
    HYPERGLASS_DEV_MODE=false \
    HYPERGLASS_REDIS_HOST=localhost \
    HYPERGLASS_DISABLE_UI=false \
    HYPERGLASS_CONTAINER=true \
    NEXT_TELEMETRY_DISABLED=1 \
    CI=true
RUN mkdir -p /etc/hyperglass/static/images /etc/hyperglass/plugins
COPY hyperglass/ui/package.json hyperglass/ui/pnpm-lock.yaml hyperglass/ui/pnpm-workspace.yaml ./hyperglass/ui/
RUN pnpm --dir hyperglass/ui install --frozen-lockfile
COPY . .
RUN pip install --no-cache-dir hatchling==1.24.2 editables==0.5 setuptools==69.2.0 wheel==0.43.0 \
    && pip install --no-cache-dir --no-deps --no-build-isolation -r requirements.lock \
    && pip check

FROM dependencies AS test
RUN pip install --no-cache-dir --no-deps --no-build-isolation -r requirements-dev.lock

FROM dependencies AS app
ARG APPLICATION_REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/X4BNet/hyperglass" \
    org.opencontainers.image.revision=$APPLICATION_REVISION \
    io.x4b.hyperglass.upstream="fd34bda03fe3382cb14a00dc9ec76cf282bc3e0a"
EXPOSE 8001
CMD ["python3", "-m", "hyperglass.console", "start", "--workers", "2"]
