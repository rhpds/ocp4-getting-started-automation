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

# Copy built assets into the UBI default web root
COPY --from=build /opt/app-root/src/dist /opt/app-root/src

# nginx.conf contains location blocks for the UBI default server block.
# __NAMESERVER__ is substituted at runtime by entrypoint.sh.
COPY nginx.conf /opt/app-root/etc/nginx.default.d/datasphere.conf

# entrypoint.sh injects the cluster DNS resolver and starts nginx
# The script must be committed with execute permissions (chmod +x before git add)
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# UBI nginx runs as uid 1001 — no chmod hacks needed
EXPOSE 8080

CMD ["/usr/local/bin/entrypoint.sh"]
