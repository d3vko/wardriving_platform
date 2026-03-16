from django.db import transaction

from .models import FilesUploaded
from .tasks import process_file


def run_process_file(file_upload_id: int = None, instance: FilesUploaded = None):
    if file_upload_id:
        try:
            instance = FilesUploaded.objects.get(pk=file_upload_id)
        except FilesUploaded.DoesNotExist:
            return
    if instance:
        uploaded_by_id = getattr(instance, "uploaded_by", None)
        device_source = getattr(instance, "device_source", None)

        def _enqueue():
            process_file.apply_async(
                args=(instance.pk,),
                kwargs={
                    "_uploaded_by_id": uploaded_by_id,
                    "_device_source": device_source,
                },
                ignore_result=True,
            )

        transaction.on_commit(_enqueue)
