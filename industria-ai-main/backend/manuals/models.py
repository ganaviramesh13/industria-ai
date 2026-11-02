from django.db import models
from django.conf import settings
from machines.models import Machine


def manual_upload_path(instance, filename):
    return f"manuals/{instance.machine.machine_id}/{instance.document_id}_Rev{instance.revision.replace('.', '_')}_{filename}"


class Manual(models.Model):
    class IndexingStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        INDEXED = 'INDEXED', 'Indexed'
        FAILED = 'FAILED', 'Failed'

    machine = models.ForeignKey(
        Machine,
        on_delete=models.CASCADE,
        related_name='manuals',
        help_text="Machine this manual belongs to"
    )
    document_id = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Document Identifier (e.g. HP-OPS-01, HP-MNT-01, AC-OM-01)"
    )
    title = models.CharField(
        max_length=255,
        help_text="Document title (e.g. HP 200 Operations Manual)"
    )
    revision = models.CharField(
        max_length=20,
        default="1.0",
        help_text="Manual revision number (e.g. 1.0)"
    )
    pdf_file = models.FileField(
        upload_to='manuals/',
        help_text="Uploaded PDF document"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_manuals'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    indexing_status = models.CharField(
        max_length=20,
        choices=IndexingStatus.choices,
        default=IndexingStatus.PENDING,
        db_index=True
    )
    chunk_count = models.IntegerField(default=0, help_text="Number of indexed vector chunks")
    page_count = models.IntegerField(default=0, help_text="Number of pages in the PDF manual")
    error_message = models.TextField(blank=True, default="", help_text="Extraction/indexing error if failed")

    class Meta:
        ordering = ['machine', 'document_id', 'revision']
        unique_together = ('machine', 'document_id', 'revision')
        verbose_name = 'Manual'
        verbose_name_plural = 'Manuals'

    def __str__(self):
        return f"{self.document_id} Rev {self.revision} - {self.title} ({self.machine.machine_id})"
