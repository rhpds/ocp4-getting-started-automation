#!/bin/bash
# Inject cluster DNS resolver and namespace into nginx config at runtime.
#
# nginx's resolver directive does not use /etc/resolv.conf search domains,
# so short service names like "datasphere-api" don't resolve. We build the
# full FQDN (datasphere-api.<namespace>.svc.cluster.local) from the
# namespace mounted by Kubernetes at a well-known path.
set -e

NAMESERVER=$(awk '/^nameserver/{print $2; exit}' /etc/resolv.conf)
NAMESPACE=$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace)

sed -i \
  -e "s/__NAMESERVER__/${NAMESERVER}/" \
  -e "s/__NAMESPACE__/${NAMESPACE}/" \
  /opt/app-root/etc/nginx.default.d/datasphere.conf

exec nginx -g "daemon off;"
