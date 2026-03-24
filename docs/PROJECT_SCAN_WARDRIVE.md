# Wardrive project scan

**Date:** 2025-02-07  
**Scope:** `wardrive/` directory, `docker-compose.yml` / `podman-compose.yml`, dependencies, and configuration.

---

## 1. Project structure

```
wardriving_app/
├── docker-compose.yml      # Service orchestration (Docker Compose)
├── podman-compose.yml      # Service orchestration (Podman Compose)
├── Dockerfile              # Main image (wardrive + celery)
├── requirements.txt       # Python dependencies
├── nginx.conf              # Reverse proxy (Django, Metabase, CTFd)
├── start.sh / wait.sh      # App startup and DB wait
├── start_celery.sh         # Celery worker
├── start_celery_beat.sh    # Celery Beat
├── ctfd/                   # CTFd (own Dockerfile)
├── sql_bi_sources/         # SQL for BI
├── misc/                   # Scripts and miscellaneous HTML
└── wardrive/               # Django project
    ├── manage.py
    ├── wardrive/           # Django settings
    │   ├── settings.py
    │   ├── urls.py
    │   ├── celery.py
    │   ├── wsgi.py, asgi.py
    ├── api/                 # REST layer
    │   ├── urls.py
    │   ├── exception_handler.py
    │   ├── pagination.py
    │   ├── utils.py
    │   └── v1/
    │       ├── urls.py
    │       └── files/       # File upload endpoints
    │           ├── routers.py
    │           ├── views.py
    │           ├── serializers.py
    └── apps/
        ├── core/           # Base models (WardriveBaseModel, soft delete)
        ├── files/          # Upload, processing, Celery tasks
        ├── vendors/        # IEEE vendors
        └── wardriving/     # Wardriving models, LTEWardriving, DB views, SourceDevice
```

---

## 2. Dependencies

### 2.1 Docker Compose / Podman Compose – services

| Service | Image/Context | Dependencies | Main use |
| ------- | ------------- | ------------ | -------- |
| **wardrive** | `build: .` | wardrive_db | Django + Gunicorn |
| **wardrive_db** | postgres:17 | — | PostgreSQL |
| **redis** | redis:alpine | — | Cache/Celery backend (optional) |
| **rabbitmq** | rabbitmq:3.13-management | — | Celery broker (port 15672) |
| **celery_proc_0** | `build: .` | wardrive, redis, rabbitmq | Queue proc_0 |
| **celery_proc_1** | `build: .` | wardrive, redis, rabbitmq | Queue proc_1 |
| **celery-beat** | `build: .` | wardrive, redis | Scheduled tasks |
| **wardrive_bi** | metabase/metabase:v0.54.2 | — | BI (Metabase) |
| **wardrive_proxy** | nginx:1.28.0 | wardrive, wardrive_bi | Nginx (port 8000) |
| **ctfd_platform** | build ./ctfd | wardrive_db | CTFd at /ctf |

### 2.2 requirements.txt (Python)

- **Django** 5.2  
- **DRF** 3.16.0, **simplejwt** 5.5.0, **django-filter** 25.1  
- **django-cors-headers**, **django-environ**, **drf-yasg**  
- **psycopg2-binary** 2.9.10  
- **Celery** 5.5.3, **redis** 6.2.0, **django_celery_beat** 2.8.1  
- **gunicorn**, **whitenoise**, **watchdog**  
- **pandas** 2.3.1, **django-db-views**, **simplekml**, **flower**, **requests**

### 2.3 Consistency with settings.py

- **INSTALLED_APPS:** uses `"django_filters"`; the pip package is `django-filter`. Recent versions use the app name `django_filters` (correct).
- **Celery:** by default `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` point to Redis, but in docker-compose/podman-compose workers depend on **RabbitMQ**. Production `.env` should define the broker (e.g. `amqp://guest:guest@rabbitmq:5672//`).
- **CELERY_SHARDS:** default 4; compose only has 2 workers (`proc_0`, `proc_1`). Queues `proc_2` and `proc_3` have no worker unless you scale.

---

## 3. Relevant data flow

1. **Upload:** `POST /api/v1/files-uploaded/` → `FilesUploadedViewSet` → `MultipleFileUploadedCreateSerializer` → creates `FilesUploaded`.
2. **Signal:** `post_save` on `FilesUploaded` → `run_process_file()` → `process_file.apply_async()` with routing by `(uploaded_by, device_source)`.
3. **Celery:** `process_file` reads `CHOICES_FUNCTION_PROCESS[device_source]` in `apps.files.utils` and runs the matching parser (Marauder, Minino, RF WiFi/LTE, etc.).
4. **Processing:** functions in `utils.py` parse files, normalize rows, and call `bulk_upsert_by_keys` (Wardriving or LTEWardriving) using Redis locks per key to avoid duplicates/races.

---

## 4. Findings and risks

### 4.1 Critical / configuration

- **Empty REDIS_URL:** In `settings.py`, if `REDIS_HOST` is empty, `REDIS_URL` becomes `""`. In `apps.files.utils`, `Redis.from_url(settings.REDIS_URL)` runs at import. With an empty URL, Redis may fail unexpectedly. If processing uses Redis (locks), the service must have Redis configured and a valid `REDIS_URL`.
- **Startup without waiting for DB:** In `start.sh`, the wait script only runs when `ENVIRONMENT=local`. In containers the app does not wait for PostgreSQL; `migrate` can fail if the app starts before the DB. Recommendation: use `wait.sh` in containers too or `depends_on` with a condition (Postgres healthcheck) if Compose supports it.
- **Celery broker vs Compose:** By default the code uses Redis as broker; Compose declares RabbitMQ. Ensure `.env` (or env vars) sets `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` consistently with the services you run.

### 4.2 Code

- **`apps/files/utils.py` (~1020 lines):** Parsers (Marauder Flipper/Classic, Minino, RF WiFi/LTE, LTE wardriving), upsert helpers, Redis locks, and `CHOICES_FUNCTION_PROCESS`. Best refactor candidate: split by format/source (modules or packages) and keep only generic helpers in `utils` (bulk upsert, locks, types).
- **Mutable default arguments:** Several functions use `list()` as default (e.g. `process_format_flipper_marauder_wifi(lines=list(), ...)`). Safer pattern: use `None` and set `lines = lines or []` inside the function.
- **Exception handler:** In `api/exception_handler.py`, `response.data = {"message": response.data["__all__"]}` when `__all__` is in `exc.detail`. If `response.data` is not a dict or structure differs, it can break. Prefer type and key checks.
- **CTFd and Metabase:** CTFd shares PostgreSQL (`wardrive_db`) with another database (`ctfd`); Metabase has no `depends_on` or healthcheck waiting for others. Optional: healthcheck on `wardrive_bi` and document env vars if using an external DB for Metabase.

### 4.3 Minor

- **Duplicate `CommonMiddleware`:** `settings.py` lists `CommonMiddleware` twice in `MIDDLEWARE`; one is redundant.
- **Nginx:** `/wardriving/` uses `proxy_pass http://wardrive_upstream/;` (trailing slash), so the app receives requests without the `/wardriving` prefix. If the app uses `FORCE_SCRIPT_NAME` or paths assuming that prefix, Django must align (e.g. `FORCE_SCRIPT_NAME=/wardriving`).
- **Celery app name:** In `wardrive/celery.py` the app name is `"wardriving"` while the project is `wardrive`. Not a functional issue but can confuse logs/monitoring.

---

## 5. Docker/Podman Compose vs code summary

| Resource | Used in code / settings | Compose service |
| -------- | ------------------------ | --------------- |
| PostgreSQL | Django DB (`DB_*`) | wardrive_db |
| Redis | `REDIS_URL`, locks in files.utils | redis |
| RabbitMQ | Not default in settings | rabbitmq (broker expected via `.env`) |
| Metabase | Nginx /bi → wardrive_bi | wardrive_bi |
| CTFd | Nginx /ctf → ctfd_platform | ctfd_platform |

---

## 6. Refactoring recommendations

1. **Split `apps/files/utils.py`:**
   - Module (or package) for **parsers per format** (marauder_flipper, marauder_classic, minino, rf_wifi, rf_lte, lte_wardriving) returning normalized rows.
   - Module for **bulk upsert and locks** (or `core` if reused): `bulk_upsert_by_keys`, `record_lock`, `record_lte_lock`, `get_lock_*`, `wardriving_better_obj_fn`, etc.
   - In `files`, a single map `SourceDevice` → function (current `CHOICES_FUNCTION_PROCESS`) orchestrating parser + upsert.

2. **Configuration and startup:**
   - Make `REDIS_URL` explicit: if Redis is unused, do not initialize the client at import; if used, require a valid URL or fail at startup.
   - Unify startup: use `wait.sh` for DB in containers too, or Postgres healthcheck + `depends_on` with condition.
   - Document in README or `.env.example`: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `REDIS_HOST` / `REDIS_URL`, `DB_*`.

3. **Code quality:**
   - Remove mutable defaults; use `None` and assign inside functions.
   - Tighten exception handler (check type and keys before reassigning `response.data`).
   - Remove duplicate `CommonMiddleware` in `settings.py`.

4. **Docker/Podman Compose / Celery:**
   - Align `CELERY_SHARDS` with the number of workers in Compose, or document scaling workers for proc_2, proc_3.
   - Optional: healthcheck on `wardrive_db` and have `wardrive` wait before `migrate`.

This scan gives a clear basis to prioritize refactoring (especially `utils.py` and Redis/DB/Celery configuration) and to align docker-compose/podman-compose with actual runtime behavior.
