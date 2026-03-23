#!/bin/sh
set -eu

APP_DIR="/usr/src/app"
TEMPLATE="${APP_DIR}/queries/source.yml.tpl"
TARGET="${APP_DIR}/queries/source.yml"

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
