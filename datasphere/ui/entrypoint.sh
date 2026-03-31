#!/bin/bash
# Inject the cluster DNS resolver into the nginx config at runtime.
# nginx requires a static resolver IP when using variables in proxy_pass.
# We read it from /etc/resolv.conf, which Kubernetes always populates with
# the cluster DNS service IP.
set -e

NAMESERVER=$(awk '/^nameserver/{print $2; exit}' /etc/resolv.conf)
sed -i "s/__NAMESERVER__/${NAMESERVER}/" /opt/app-root/etc/nginx.default.d/datasphere.conf

exec nginx -g "daemon off;"
