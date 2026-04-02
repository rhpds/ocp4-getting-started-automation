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

# Copy built assets to the UBI nginx serve root (/opt/app-root/src)
# Note: /etc/nginx/conf.d/ and /usr/share/nginx/html are NOT used by UBI nginx-122.
# The nginx.conf location snippets are injected at runtime by the Helm init container
# (see datasphere/gitops/templates/deployment-ui.yaml) to pick up the cluster DNS
# resolver and API FQDN dynamically.
COPY --from=build /opt/app-root/src/dist /opt/app-root/src

# UBI nginx runs as uid 1001 — no chmod hacks needed
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
