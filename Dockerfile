FROM python:3.13-slim AS builder

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /code
COPY . .

RUN sed -i 's/\r$//g' start.sh wait.sh start_celery.sh start_celery_beat.sh \
    && chmod +x start.sh wait.sh start_celery.sh start_celery_beat.sh

CMD ["/code/start.sh"]