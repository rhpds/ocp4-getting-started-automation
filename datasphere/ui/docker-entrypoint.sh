#!/bin/bash
# Startup script for datasphere-ui.
#
# Generates the nginx location config at container start so the /api/ proxy
# works with any deployment method (oc new-app, Helm, etc.) without an init
# container. Uses the in-cluster DNS resolver discovered from /etc/resolv.conf
# and the set $variable pattern so nginx starts cleanly even before the API
# Service exists.
set -e

NS_IP=$(awk '/^nameserver/{print $2; exit}' /etc/resolv.conf)
NS_FILE=/var/run/secrets/kubernetes.io/serviceaccount/namespace
if [ -f "$NS_FILE" ]; then
  NS=$(cat "$NS_FILE")
  API_HOST="datasphere-api.${NS}.svc.cluster.local"
else
  API_HOST="datasphere-api"
fi

mkdir -p /opt/app-root/etc/nginx.default.d

cat > /opt/app-root/etc/nginx.default.d/datasphere.conf <<EOF
location / {
  root /opt/app-root/src;
  try_files \$uri \$uri/ /index.html;
}
location /api/ {
  resolver ${NS_IP} valid=10s;
  set \$api_upstream http://${API_HOST}:8080;
  proxy_pass          \$api_upstream;
  proxy_set_header    Host              \$host;
  proxy_set_header    X-Real-IP         \$remote_addr;
  proxy_set_header    X-Forwarded-For   \$proxy_add_x_forwarded_for;
  proxy_read_timeout  30s;
}
EOF

exec nginx -g "daemon off;"
