#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

VAR_NAME="ENVIRONMENT"

if [ -z "${!VAR_NAME:-}" ]; then
    # If Env does not exist, then create it with the value 'container'
    export ENVIRONMENT="container"
fi

if [ "$ENVIRONMENT" == "local" ]; then
    echo "Install missing dependencies for local stage"
    apt update > /dev/null 2>&1 
    apt install -y netcat-openbsd > /dev/null 2>&1
    echo "Wait until database is already to use"
    bash /code/wait.sh $DB_HOST:$DB_PORT
fi


# Run Django migrations
python /code/wardrive/manage.py migrate


if [ "${ENVIRONMENT}" == "local" ]; then
    echo "Starting Django development server"
    python /code/wardrive/manage.py runserver 0.0.0.0:8000
else
    echo "Starting Daphne (ASGI: HTTP + WebSocket)"
    python /code/wardrive/manage.py collectstatic --noinput
    export PYTHONPATH=/code/wardrive
    # KML export can take a long time on large date ranges. Daphne defaults are too low:
    #   websocket_connect_timeout=5s  → handshake killed while server is busy
    #   ping_timeout=30s              → idle WS closed during silent KML generation
    #   application_close_timeout=10s → "took too long to shut down" warnings
    # Align all WS timeouts with nginx/frontend (1.5 h).
    exec daphne -b 0.0.0.0 -p 8000 \
        --websocket_connect_timeout 5400 \
        --websocket_timeout 5400 \
        --ping-interval 120 \
        --ping-timeout 5400 \
        --application-close-timeout 5400 \
        wardrive.asgi:application
fi
