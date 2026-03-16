#!/bin/sh
# Railway injects PORT at runtime; pass it to Grafana via env var
export GF_SERVER_HTTP_PORT="${PORT:-3000}"
exec /run.sh
