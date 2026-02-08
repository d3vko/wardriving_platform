from django.db import models
from django.db.models.query import QuerySet
from django.utils.translation import pgettext_lazy
from django.utils.timezone import now

from apps.wardriving import SourceDevice


class SoftQuerySet(QuerySet):
    def delete(self):
        # Updates logical delete state
        return super(SoftQuerySet, self).update(deleted_at=now())

    def hard_delete(self):
        # Permanently deletes the object
        return super(SoftQuerySet, self).delete()

    def alive(self):
        # Filters active (non-deleted) objects
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        # Filters logically deleted objects
        return self.exclude(deleted_at__isnull=True)


class SoftDeleteManager(models.Manager):
    def __init__(self, *args, **kwargs):
        self.alive_only = kwargs.pop("alive_only", True)
        super(SoftDeleteManager, self).__init__(*args, **kwargs)

    def get_queryset(self):
        if self.alive_only:
            return SoftQuerySet(self.model).filter(deleted_at__isnull=self.alive_only)
        return SoftQuerySet(self.model)

    def hard_delete(self):
        return self.get_queryset().hard_delete()


class BaseModel(models.Model):
    # Base Model you can copy for another base model SoftDelete
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=pgettext_lazy("Wardrive Base Model field", "created at"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=pgettext_lazy("Wardrive Base Model field", "updated at"),
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=pgettext_lazy("Wardrive Base Model field", "deleted at"),
    )
    objects = SoftDeleteManager()
    all_objects = SoftDeleteManager(alive_only=False)

    class Meta:
        abstract = True

    def can_delete(self):
        return True

    def delete(self):
        self.can_delete()
        # Performs logical delete in DB
        self.deleted_at = now()
        self.save()

    def recover(self):
        # Restores the object (clears deleted_at)
        self.deleted_at = None
        self.save()

    def hard_delete(self):
        # Permanently deletes the record
        super().delete()

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)


class WardriveBaseModel(BaseModel):
    # Fields for conquest wardriving
    first_seen = models.DateTimeField(verbose_name="First Seen", default=now)
    uploaded_by = models.TextField(verbose_name="Uploaded by", default="")
    device_source = models.CharField(
        max_length=50,
        verbose_name="Source",
        choices=SourceDevice.CHOICES,
        default=SourceDevice.UNKNOWN,
    )

    class Meta:
        abstract = True
