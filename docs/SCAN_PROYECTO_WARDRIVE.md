# Scan del proyecto Wardrive

**Fecha:** 2025-02-07  
**Alcance:** directorio `wardrive/`, `docker-compose.yml` / `podman-compose.yml`, dependencias y configuración.

---

## 1. Estructura del proyecto

```
wardriving_app/
├── docker-compose.yml      # Orquestación de servicios (Docker Compose)
├── podman-compose.yml      # Orquestación de servicios (Podman Compose)
├── Dockerfile              # Imagen principal (wardrive + celery)
├── requirements.txt       # Dependencias Python
├── nginx.conf              # Proxy reverso (Django, Metabase, CTFd)
├── start.sh / wait.sh      # Arranque app y espera a DB
├── start_celery.sh         # Worker Celery
├── start_celery_beat.sh    # Celery Beat
├── ctfd/                   # CTFd (Dockerfile propio)
├── sql_bi_sources/         # SQL para BI
├── misc/                   # Scripts y HTML varios
└── wardrive/               # Proyecto Django
    ├── manage.py
    ├── wardrive/           # Configuración Django
    │   ├── settings.py
    │   ├── urls.py
    │   ├── celery.py
    │   ├── wsgi.py, asgi.py
    ├── api/                 # Capa REST
    │   ├── urls.py
    │   ├── exception_handler.py
    │   ├── pagination.py
    │   ├── utils.py
    │   └── v1/
    │       ├── urls.py
    │       └── files/       # Endpoints de subida de ficheros
    │           ├── routers.py
    │           ├── views.py
    │           ├── serializers.py
    └── apps/
        ├── core/           # Modelos base (WardriveBaseModel, soft delete)
        ├── files/          # Subida, procesamiento y tareas Celery
        ├── vendors/        # Vendors IEEE
        └── wardriving/     # Modelos Wardriving, LTEWardriving, vistas DB, SourceDevice
```

---

## 2. Dependencias

### 2.1 Docker Compose / Podman Compose – servicios

| Servicio          | Imagen/Contexto     | Dependencias        | Uso principal                    |
|-------------------|---------------------|---------------------|----------------------------------|
| **wardrive**      | `build: .`          | wardrive_db         | Django + Gunicorn                |
| **wardrive_db**   | postgres:17         | —                   | PostgreSQL                       |
| **redis**         | redis:alpine        | —                   | Cache/backend Celery (opcional)  |
| **rabbitmq**      | rabbitmq:3.13-management | —             | Broker Celery (puerto 15672)     |
| **celery_proc_0** | `build: .`          | wardrive, redis, rabbitmq | Cola proc_0              |
| **celery_proc_1** | `build: .`          | wardrive, redis, rabbitmq | Cola proc_1              |
| **celery-beat**   | `build: .`          | wardrive, redis     | Tareas programadas               |
| **wardrive_bi**   | metabase/metabase:v0.54.2 | —              | BI (Metabase)                    |
| **wardrive_proxy**| nginx:1.28.0       | wardrive, wardrive_bi | Nginx (puerto 8000)          |
| **ctfd_platform** | build ./ctfd        | wardrive_db         | CTFd en /ctf                     |

### 2.2 requirements.txt (Python)

- **Django** 5.2  
- **DRF** 3.16.0, **simplejwt** 5.5.0, **django-filter** 25.1  
- **django-cors-headers**, **django-environ**, **drf-yasg**  
- **psycopg2-binary** 2.9.10  
- **Celery** 5.5.3, **redis** 6.2.0, **django_celery_beat** 2.8.1  
- **gunicorn**, **whitenoise**, **watchdog**  
- **pandas** 2.3.1, **django-db-views**, **simplekml**, **flower**, **requests**

### 2.3 Coherencia con settings.py

- **INSTALLED_APPS:** se usa `"django_filters"`; el paquete pip es `django-filter`. En versiones recientes el nombre del app es `django_filters` (correcto).
- **Celery:** por defecto `CELERY_BROKER_URL` y `CELERY_RESULT_BACKEND` apuntan a Redis, pero en docker-compose/podman-compose los workers dependen de **RabbitMQ**. Se asume que en producción `.env` define el broker (p. ej. `amqp://guest:guest@rabbitmq:5672//`).
- **CELERY_SHARDS:** por defecto 4; en compose solo hay 2 workers (`proc_0`, `proc_1`). Las colas `proc_2` y `proc_3` no tienen worker si no se escalan.

---

## 3. Flujo de datos relevante

1. **Subida:** `POST /api/v1/files-uploaded/` → `FilesUploadedViewSet` → `MultipleFileUploadedCreateSerializer` → crea `FilesUploaded`.
2. **Señal:** `post_save` en `FilesUploaded` → `run_process_file()` → `process_file.apply_async()` con routing por `(uploaded_by, device_source)`.
3. **Celery:** `process_file` lee `CHOICES_FUNCTION_PROCESS[device_source]` en `apps.files.utils` y ejecuta la función de procesamiento correspondiente (Marauder, Minino, RF WiFi/LTE, etc.).
4. **Procesamiento:** las funciones en `utils.py` parsean ficheros, normalizan filas y llaman a `bulk_upsert_by_keys` (Wardriving o LTEWardriving) usando locks Redis por clave para evitar duplicados/condiciones de carrera.

---

## 4. Hallazgos y riesgos

### 4.1 Críticos / configuración

- **REDIS_URL vacío:** En `settings.py`, si `REDIS_HOST` está vacío, `REDIS_URL` queda `""`. En `apps.files.utils` se hace `Redis.from_url(settings.REDIS_URL)` al importar. Con URL vacía, Redis puede fallar o comportarse de forma inesperada. Si el procesamiento usa Redis (locks), el servicio debe tener Redis configurado y `REDIS_URL` válido.
- **Arranque sin esperar a la DB:** En `start.sh`, la espera con `wait.sh` solo se ejecuta cuando `ENVIRONMENT=local`. En entorno container no se espera a PostgreSQL; `migrate` puede fallar si el contenedor arranca antes que la DB. Recomendación: usar `wait.sh` también en container o `depends_on` con condition (healthcheck de postgres) si la versión de Compose lo permite.
- **Broker Celery vs Compose:** Por defecto el código usa Redis como broker; Compose declara RabbitMQ. Hay que asegurar que `.env` (o variables de entorno) definan `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` de forma coherente con los servicios que realmente se usen.

### 4.2 Código

- **`apps/files/utils.py` (~1020 líneas):** Concentra parsers (Marauder Flipper/Classic, Minino, RF WiFi/LTE, LTE wardriving), helpers de upsert, locks Redis y el mapa `CHOICES_FUNCTION_PROCESS`. Es el mejor candidato para refactor: dividir por formato/fuente (módulos o paquetes) y dejar en `utils` solo helpers genéricos (bulk upsert, locks, tipos).
- **Argumentos mutables por defecto:** En varias funciones (p. ej. `process_format_flipper_marauder_wifi(lines=list(), ...)`) se usa `list()` como default. Aunque en la práctica no se modifica la lista por defecto, es un antipatrón; es más seguro usar `None` y dentro de la función `lines = lines or []`.
- **Exception handler:** En `api/exception_handler.py` se hace `response.data = {"message": response.data["__all__"]}` cuando `__all__` está en `exc.detail`. Si `response.data` no es un dict o no tiene la estructura esperada, puede provocar errores. Conviene comprobar tipo y existencia de claves.
- **CTFd y Metabase:** CTFd usa la misma PostgreSQL (`wardrive_db`) con otra base (`ctfd`); Metabase no declara `depends_on` ni healthcheck que espere a otros servicios. Opcional: healthcheck en `wardrive_bi` y, si se usa BD externa para Metabase, documentar variables de entorno.

### 4.3 Menores

- **Duplicado `CommonMiddleware`:** En `settings.py` hay dos entradas de `CommonMiddleware` en `MIDDLEWARE`; una es redundante.
- **Nginx:** La ruta `/wardriving/` hace `proxy_pass http://wardrive_upstream/;` (con barra final), por lo que la app recibe requests sin el prefijo `/wardriving`. Si la app usa `FORCE_SCRIPT_NAME` o rutas que asuman ese prefijo, debe estar alineado en Django (p. ej. `FORCE_SCRIPT_NAME=/wardriving`).
- **Celery app name:** En `wardrive/celery.py` el nombre de la app es `"wardriving"`; el proyecto se llama `wardrive`. Funcionalmente no es problema, pero puede generar confusión en logs/monitorización.

---

## 5. Resumen de dependencias Docker/Podman Compose vs código

| Recurso    | Usado en código / settings        | Servicio Compose |
|-----------|------------------------------------|-------------------|
| PostgreSQL| DB Django (env DB_*)               | wardrive_db       |
| Redis     | REDIS_URL, locks en files.utils    | redis             |
| RabbitMQ  | No por defecto en settings         | rabbitmq (broker esperado vía .env) |
| Metabase  | Nginx /bi → wardrive_bi            | wardrive_bi       |
| CTFd      | Nginx /ctf → ctfd_platform         | ctfd_platform     |

---

## 6. Recomendaciones para refactorización

1. **Dividir `apps/files/utils.py`:**
   - Módulo (o paquete) para **parsers por formato** (marauder_flipper, marauder_classic, minino, rf_wifi, rf_lte, lte_wardriving) con funciones que devuelvan filas normalizadas.
   - Módulo de **bulk upsert y locks** (o en `core` si se reutiliza): `bulk_upsert_by_keys`, `record_lock`, `record_lte_lock`, `get_lock_*`, `wardriving_better_obj_fn`, etc.
   - En `files` dejar un único punto que mapee `SourceDevice` → función (actual `CHOICES_FUNCTION_PROCESS`) y que estas funciones orquesten parser + upsert.

2. **Configuración y arranque:**
   - Hacer `REDIS_URL` explícito: si no se usa Redis, no inicializar el cliente en módulo; si se usa, exigir URL válida o fallar al arrancar.
   - Unificar arranque: usar `wait.sh` para DB también en container o definir healthcheck de postgres y `depends_on` con condition.
   - Documentar en README o `.env.example` las variables necesarias: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `REDIS_HOST`/`REDIS_URL`, `DB_*`.

3. **Calidad de código:**
   - Eliminar argumentos por defecto mutables; usar `None` y asignar dentro de la función.
   - Revisar y acotar el exception handler (comprobar tipo y claves antes de reasignar `response.data`).
   - Quitar el middleware `CommonMiddleware` duplicado en `settings.py`.

4. **Docker/Podman Compose / Celery:**
   - Alinear `CELERY_SHARDS` con el número de workers definidos en Compose, o documentar que hay que escalar workers para proc_2, proc_3.
   - Opcional: añadir healthcheck a `wardrive_db` y que `wardrive` espere a que esté listo antes de `migrate`.

Con este scan tienes una base clara para priorizar la refactorización (sobre todo `utils.py` y configuración Redis/DB/Celery) y alinear docker-compose/podman-compose con el comportamiento real del código.
