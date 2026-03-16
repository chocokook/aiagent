#!/bin/sh
# Substitute env vars into prometheus config at startup
API_HOST="${RAILWAY_API_HOST:-aiagent-production.up.railway.app}"
API_SCHEME="${RAILWAY_API_SCHEME:-https}"
sed \
    -e "s|\${RAILWAY_API_HOST}|${API_HOST}|g" \
    -e "s|\${RAILWAY_API_SCHEME}|${API_SCHEME}|g" \
    /etc/prometheus/prometheus.template.yml > /etc/prometheus/prometheus.yml

exec /bin/prometheus \
    --config.file=/etc/prometheus/prometheus.yml \
    --storage.tsdb.retention.time=7d \
    --web.listen-address=":${PORT:-9090}" \
    "$@"
