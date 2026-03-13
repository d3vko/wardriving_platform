# Bugs and Bad Practices — Wardrive Project

This document lists identified bugs, possible bugs, and bad practices in the Python/Django codebase. Use it as a checklist for improvements and refactors.

---

## Critical / Security

### 1. Upload endpoint allows unauthenticated access
- **Where:** `api/v1/files/views.py` — `FilesUploadedViewSet.permission_classes = [permissions.AllowAny]`
- **Issue:** Anyone can upload files and trigger processing. In production this can lead to abuse, storage exhaustion, and unnecessary Celery load.
- **Recommendation:** Require authentication (e.g. JWT or session) or at least a shared secret / API key; avoid `AllowAny` for upload in production.

### 2. `ALLOWED_HOSTS = ["*"]`
- **Where:** `wardrive/settings.py`
- **Issue:** In production this weakens host-header validation and can help SSRF/cache poisoning.
- **Recommendation:** Set `ALLOWED_HOSTS` from environment to explicit domains (e.g. `env.list("ALLOWED_HOSTS", default=["localhost"])`).

### 3. `SECRET_KEY` with no default
- **Where:** `wardrive/settings.py` — `SECRET_KEY = env("SECRET_KEY")`
- **Issue:** App fails at startup if `SECRET_KEY` is missing. Good for production; bad for first-time dev setup without `.env`.
- **Recommendation:** Document in README that `.env` is required; optionally use a default only when `DEBUG=True` (and warn in logs).

---

## Bugs / Possible bugs

### 4. Exception handler can crash or serialize lists incorrectly
- **Where:** `api/exception_handler.py`
- **Issue:** `response.data["__all__"]` may be a list (common in DRF validation errors). Assigning it to `response.data = {"message": ...}` can store a list under `"message"` and break clients. If `response.data` is not a dict, `"__all__" in exc.detail` or the assignment can be wrong.
- **Recommendation:** Check `isinstance(response.data, dict)` and `"__all__" in response.data`; normalize `response.data["__all__"]` to a string (e.g. join if list) before setting `response.data = {"message": ...}`.

### 5. Redis lock released even when `acquire()` failed
- **Where:** `apps/files/utils.py` — `record_lock`, `record_lte_lock`
- **Issue:** If `lock.acquire()` raises (e.g. timeout, connection error), execution goes to `finally` and calls `lock.release()`. Releasing a lock that was never acquired can raise or behave incorrectly.
- **Recommendation:** Only call `lock.release()` when the lock was successfully acquired (e.g. use a flag or call `release()` inside the `try` after `yield` and set a flag so `finally` does not release on exception).

### 6. Task swallows exceptions and does not retry
- **Where:** `apps/files/tasks.py` — `process_file`
- **Issue:** `except Exception as e: return f"Error ..."` catches all exceptions and returns a string. The task is marked as successful, so Celery does not retry. The file stays `is_procesed=False` but there is no automatic retry.
- **Recommendation:** Either re-raise after logging so `autoretry_for` can retry, or catch a narrower exception and re-raise the rest. Optionally use a retry counter or dead-letter state for repeated failures.

### 7. Assumption of filesystem path for uploaded files
- **Where:** `apps/files/tasks.py` — `file_obj.source.path`
- **Issue:** `FileField.path` is only valid for default `FileSystemStorage`. With S3 or other remote storage, `path` may not exist or may be wrong, and processing will fail.
- **Recommendation:** Use `file_obj.source.open()`, or `storage.open(name)` and pass a file-like object to processors, so code works with any storage backend.

### 8. `MEDIA_URL` built with `os.path.join` and leading slash
- **Where:** `wardrive/settings.py` — `MEDIA_URL = os.path.join(FORCE_SCRIPT_NAME, "/media/")`
- **Issue:** A leading slash in `"/media/"` can make `os.path.join` ignore the preceding segment on some platforms, so `FORCE_SCRIPT_NAME` might not appear in `MEDIA_URL`.
- **Recommendation:** Build `MEDIA_URL` as string concatenation, e.g. `f"{FORCE_SCRIPT_NAME}/media/"`.strip("/") or normalize without relying on `os.path.join` for URLs.

### 9. Race in `FilesUploaded.save()` and duplicate detection
- **Where:** `apps/files/models.py` — `FilesUploaded.save()`
- **Issue:** Hash is computed and then `FilesUploaded.objects.filter(hash_sha256=...)` is run. Between two concurrent saves of the same file, both can see “no existing” and both set `is_procesed = False`; the signal will enqueue two tasks for the same logical file.
- **Recommendation:** Use `select_for_update` in a transaction, or a unique constraint on `hash_sha256` and handle `IntegrityError`, or enqueue the task only once (e.g. by a unique hash in a cache).

---

## Code quality / Maintainability

### 10. Typo in model field name: `is_procesed`
- **Where:** `apps/files/models.py` — `is_procesed`; used in migrations and `tasks.py`
- **Issue:** Typo (should be `is_processed`). Renaming requires a new migration and updating all references.
- **Recommendation:** Add a migration that renames the field to `is_processed` and update code and any docs.

### 11. Duplicate `CommonMiddleware`
- **Where:** `wardrive/settings.py` — `MIDDLEWARE` lists `django.middleware.common.CommonMiddleware` twice (lines 42 and 51).
- **Issue:** Redundant; no functional benefit.
- **Recommendation:** Remove the duplicate entry.

### 12. Unused import in views
- **Where:** `api/v1/files/views.py` — `from api.utils import is_swagger_fake_view`
- **Issue:** `is_swagger_fake_view` is never used in the file.
- **Recommendation:** Remove the import (or use it where intended, e.g. in serializers or permission checks).

### 13. Serializer `uploaded_by` unbounded and required
- **Where:** `api/v1/files/serializers.py` — `uploaded_by = serializers.CharField()`
- **Issue:** No `max_length` (DB has no limit on the model field either) and no `required=False`. Large input is possible; validation is minimal.
- **Recommendation:** Add `max_length` (and align with model if it gets one), and set `required=False` with default `""` if that matches the model.

### 14. Heavy work in `FilesUploaded.save()`
- **Where:** `apps/files/models.py` — `save()` computes hash, runs a query for duplicate hash, and may create `SourcesWithCopy`.
- **Issue:** Every save (including the one from the Celery task that only flips `is_procesed`) runs the hash logic and the duplicate query. For task-triggered saves the hash is skipped (already set), but the duplicate query still runs.
- **Recommendation:** Skip duplicate-check and signal-related logic when only “internal” fields change (e.g. `is_procesed`), or move duplicate detection to a service layer called only on upload.

---

## Configuration / Environment

### 15. `REDIS_URL` empty when Redis is not configured
- **Where:** `wardrive/settings.py` — `REDIS_URL = ""` when `REDIS_HOST` is falsy.
- **Issue:** Code that uses Redis (e.g. locks in `apps/files/utils.py`) already handles `get_redis_client()` returning `None`. No crash, but worth documenting.
- **Recommendation:** Document in README/deploy docs that Redis is optional and locks are no-ops when Redis is unavailable.

### 16. Celery shards vs workers
- **Where:** `wardrive/settings.py` — `CELERY_SHARDS = 4`; docker-compose/podman-compose defines only `proc_0` and `proc_1` workers.
- **Issue:** Queues `proc_2` and `proc_3` have no workers; tasks routed there are never consumed.
- **Recommendation:** Set `CELERY_SHARDS=2` in production when using two workers, or add workers for `proc_2`/`proc_3`, and document in README or Compose.

### 17. `hash(key) % n` for sharding
- **Where:** `wardrive/settings.py` — `_shard_for(..., n=CELERY_SHARDS)` uses `hash(key) % n`.
- **Issue:** In Python, `hash()` is salted between process runs, so the same key can map to different queues across restarts. Distribution is still even, but the same (uploaded_by, device_source) may change queue after restart.
- **Recommendation:** Accept as best-effort sharding, or use a stable hash (e.g. `hashlib.sha256(key.encode()).digest()` and take bytes as int) if you need stable routing.

---

## Best practices (recommendations)

### 18. Return value contract of processors
- **Where:** `apps/process/*` and `apps/files/tasks.py`
- **Issue:** `process_file` expects a 3-tuple `(new_added, updated, ignored)`. All current processors return that, but there is no shared type or interface.
- **Recommendation:** Define a small `Protocol` or base signature (e.g. `ProcessResult` tuple or dataclass) and document it in `apps/process/__init__.py` so new processors cannot break the task by returning something else.

### 19. No rate limiting on upload
- **Where:** Upload API
- **Issue:** With `AllowAny`, a single client can upload many files and overload storage and Celery.
- **Recommendation:** Add throttling (e.g. DRF `Throttle` classes or nginx limit_req) and, if possible, authentication so limits can be per-user.

### 20. Logging
- **Where:** Project-wide
- **Issue:** Little structured logging; task failures and processing results are only returned as strings, not logged consistently.
- **Recommendation:** Use Python `logging` (and optionally structured logs) in tasks and processors: log start/end, record counts, and exceptions with level and context.

---

## Summary table

| #  | Severity    | Category        | Location / topic                    |
|----|-------------|------------------|-------------------------------------|
| 1  | Critical    | Security         | AllowAny on upload                  |
| 2  | Critical    | Security         | ALLOWED_HOSTS                       |
| 3  | Medium      | Config           | SECRET_KEY default                  |
| 4  | Bug         | API              | exception_handler __all__           |
| 5  | Bug         | Locks            | Redis lock release on failed acquire|
| 6  | Bug         | Celery           | Exception swallowed, no retry       |
| 7  | Bug         | Storage          | source.path vs remote storage       |
| 8  | Bug         | Config           | MEDIA_URL os.path.join              |
| 9  | Bug         | Concurrency      | FilesUploaded.save() race           |
| 10 | Minor       | Naming           | is_procesed typo                    |
| 11 | Minor       | Config           | Duplicate CommonMiddleware          |
| 12 | Minor       | Dead code        | is_swagger_fake_view import         |
| 13 | Minor       | Validation       | uploaded_by serializer              |
| 14 | Performance | Models           | save() duplicate query              |
| 15 | Doc         | Config           | REDIS_URL optional                  |
| 16 | Config      | Celery           | CELERY_SHARDS vs workers            |
| 17 | Config      | Celery           | hash() for sharding                 |
| 18 | Design      | Processors       | Return type contract                |
| 19 | Security    | Rate limiting    | Upload throttling                   |
| 20 | Ops         | Logging          | Structured logging                  |

---

*Document generated from static review of the wardrive codebase. Revisit after major changes.*
