#!/bin/sh
# Railway injects PORT at runtime; pass it to Grafana via env var
export GF_SERVER_HTTP_PORT="${PORT:-3000}"

# Allow anonymous read-only access (no login required)
# These can be overridden by Railway Variables
export GF_AUTH_ANONYMOUS_ENABLED="${GF_AUTH_ANONYMOUS_ENABLED:-true}"
export GF_AUTH_ANONYMOUS_ORG_ROLE="${GF_AUTH_ANONYMOUS_ORG_ROLE:-Viewer}"
export GF_AUTH_DISABLE_LOGIN_FORM="${GF_AUTH_DISABLE_LOGIN_FORM:-true}"

exec /run.sh
