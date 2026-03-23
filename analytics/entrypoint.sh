#!/bin/sh
set -eu

APP_DIR="/usr/src/app"
if [ -d "${APP_DIR}/queries" ]; then
  SOURCE_QUERIES_DIR="${APP_DIR}/queries"
else
  echo "No source queries directory found in ${APP_DIR}" >&2
  exit 1
fi

if [ -d "${APP_DIR}/.latitude/app/queries" ]; then
  RUNTIME_QUERIES_DIR="${APP_DIR}/.latitude/app/queries"
else
  RUNTIME_QUERIES_DIR="${SOURCE_QUERIES_DIR}"
fi

# Latitude serves queries from .latitude/app/queries at runtime.
# Keep runtime queries synced from repository queries on every start.
mkdir -p "${RUNTIME_QUERIES_DIR}"
cp -R "${SOURCE_QUERIES_DIR}/." "${RUNTIME_QUERIES_DIR}/"

TEMPLATE="${RUNTIME_QUERIES_DIR}/source.yml.tpl"
TARGET="${RUNTIME_QUERIES_DIR}/source.yml"

: "${LATITUDE__POSTGRES_DB:=postgres}"
: "${LATITUDE__POSTGRES_USER:=postgres}"
: "${LATITUDE__POSTGRES_PWD:=postgres}"
: "${LATITUDE__POSTGRES_HOST:=wardrive_db}"
: "${LATITUDE__POSTGRES_PORT:=5432}"
: "${LATITUDE__POSTGRES_SCHEMA:=public}"

if [ -f "${TEMPLATE}" ]; then
  envsubst < "${TEMPLATE}" > "${TARGET}"
fi

exec node build
