from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrator'
        ENGINEER = 'ENGINEER', 'Engineer'
        SUPERVISOR = 'SUPERVISOR', 'Supervisor'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ENGINEER,
        help_text="Role determining application permissions"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_engineer_role(self):
        return self.role == self.Role.ENGINEER

    @property
    def is_supervisor_role(self):
        return self.role == self.Role.SUPERVISOR

    def __str__(self):
        return f"{self.username} ({self.role})"
