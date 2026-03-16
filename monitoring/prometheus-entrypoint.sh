#!/bin/sh
# Substitute RAILWAY_API_HOST env var into prometheus config at startup
API_HOST="${RAILWAY_API_HOST:-aiagent-production.up.railway.app}"
sed "s|\${RAILWAY_API_HOST}|${API_HOST}|g" \
    /etc/prometheus/prometheus.template.yml > /etc/prometheus/prometheus.yml

exec /bin/prometheus \
    --config.file=/etc/prometheus/prometheus.yml \
    --storage.tsdb.retention.time=7d \
    --web.listen-address=":${PORT:-9090}" \
    "$@"
