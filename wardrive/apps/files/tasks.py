import os
import tempfile

from celery import shared_task

from apps.process import CHOICES_FUNCTION_PROCESS

from .models import FilesUploaded, AllowToLoadData


@shared_task(
    bind=True,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
    reject_on_worker_lost=True,
)
def process_file(self, file_pk, _uploaded_by_id=None, _device_source=None):
    if not AllowToLoadData.objects.filter(active=True).exists():
        return "Data loading is currently disabled."
    try:
        file_obj = FilesUploaded.objects.get(pk=file_pk, is_procesed=False)
    except FilesUploaded.DoesNotExist:
        return f"File with pk={file_pk} does not exist or is already processed."
    device_source = file_obj.device_source
    class_process_function = CHOICES_FUNCTION_PROCESS.get(device_source, None)

    if not class_process_function:
        return f"No processing function found for source: {device_source}"

    # Storage backends (e.g. S3) don't support .path; use a temp file so processors can open(path).
    tmp_path = None
    try:
        with file_obj.source.open("rb") as src:
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".tmp", delete=False
            ) as tmp:
                tmp.write(src.read())
                tmp_path = tmp.name
        new_added, updated, ignored = class_process_function(
            file_path=tmp_path,
            device_source=device_source,
            uploaded_by=file_obj.uploaded_by,
        )
        total = new_added + updated + ignored
        if total == 0:
            return (
                f"File {file_pk} - {file_obj}: no records parsed (0 new, 0 updated, 0 ignored). "
                f"Left is_procesed=False so you can fix the log or device type and re-queue."
            )
        file_obj.is_procesed = True
        file_obj.save()
        return f"File {file_pk} - {file_obj} processed successfully. Total of records in file {total}, Total new records {new_added}, Total updated found records {updated}, Total ignored {ignored}"
    except Exception as e:
        return f"Error while processing file {file_pk}: {str(e)}"
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
