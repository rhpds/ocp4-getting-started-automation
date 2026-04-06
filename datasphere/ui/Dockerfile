# ── Build stage ────────────────────────────────────────────────────────────
# UBI9 Node 20 — Red Hat Universal Base Image (no auth required)
FROM registry.access.redhat.com/ubi9/nodejs-20:latest AS build

# UBI non-root images run as uid 1001; /opt/app-root/src is already owned by that user
WORKDIR /opt/app-root/src

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ── Serve stage ────────────────────────────────────────────────────────────
# UBI9 nginx 1.22 — consistent base for vulnerability scanning
FROM registry.access.redhat.com/ubi9/nginx-122:latest

# Copy built assets to /opt/app-root/src — the UBI nginx-122 default serve root.
COPY --from=build /opt/app-root/src/dist /opt/app-root/src

# Startup script: generates the nginx proxy config at container start using the
# in-cluster DNS resolver. Works with any deployment method (oc new-app, Helm)
# without requiring an init container.
COPY docker-entrypoint.sh /opt/app-root/docker-entrypoint.sh

# UBI nginx runs as uid 1001 — /opt/app-root is writable by that user
EXPOSE 8080

CMD ["/opt/app-root/docker-entrypoint.sh"]
