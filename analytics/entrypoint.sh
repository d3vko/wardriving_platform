#!/bin/sh
set -eu

APP_DIR="/usr/src/app"
if [ -d "${APP_DIR}/build/queries" ]; then
  QUERIES_DIR="${APP_DIR}/build/queries"
elif [ -d "${APP_DIR}/queries" ]; then
  QUERIES_DIR="${APP_DIR}/queries"
else
  echo "No queries directory found in ${APP_DIR}" >&2
  exit 1
fi

TEMPLATE="${QUERIES_DIR}/source.yml.tpl"
TARGET="${QUERIES_DIR}/source.yml"

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
