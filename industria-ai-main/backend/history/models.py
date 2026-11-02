from django.db import models
from django.conf import settings
from machines.models import Machine


class QuestionHistory(models.Model):
    class Status(models.TextChoices):
        ANSWERED = 'answered', 'Answered'
        INSUFFICIENT_EVIDENCE = 'insufficient_evidence', 'Insufficient Evidence'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='question_history',
        help_text="Engineer or user who submitted the query"
    )
    selected_machine = models.ForeignKey(
        Machine,
        on_delete=models.CASCADE,
        related_name='question_history',
        help_text="Machine targeted by the query"
    )
    question = models.TextField(help_text="Original engineer question")
    answer = models.TextField(help_text="Generated answer or insufficient evidence statement")
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.ANSWERED,
        db_index=True
    )
    citations = models.JSONField(
        default=list,
        blank=True,
        help_text="List of source citations with doc_id, title, rev, page_number, and passage"
    )
    supporting_passages = models.JSONField(
        default=list,
        blank=True,
        help_text="Full text and metadata of retrieved passages used as evidence"
    )
    reviewed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Supervisor has reviewed this query"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Question History'
        verbose_name_plural = 'Question Histories'

    def __str__(self):
        return f"[{self.selected_machine.machine_id}] {self.user.username}: {self.question[:40]}... ({self.status})"
