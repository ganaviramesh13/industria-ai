from django.db import models


class Machine(models.Model):
    machine_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique Machine Identifier (e.g. M-HP200, M-AC90)"
    )
    name = models.CharField(
        max_length=150,
        help_text="Standard machine name (e.g. Hydraulic forming press)"
    )
    model = models.CharField(
        max_length=100,
        help_text="Model designation (e.g. HP-200, AC-90)"
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Technical specifications and operational description"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['machine_id']
        verbose_name = 'Machine'
        verbose_name_plural = 'Machines'

    def __str__(self):
        return f"{self.machine_id} - {self.model} ({self.name})"
