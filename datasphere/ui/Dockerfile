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

# Copy built assets and custom nginx config
COPY --from=build /opt/app-root/src/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/datasphere.conf

# UBI nginx runs as uid 1001 — no chmod hacks needed
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
