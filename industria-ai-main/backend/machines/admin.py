from django.contrib import admin
from .models import Machine


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ('machine_id', 'model', 'name', 'created_at')
    search_fields = ('machine_id', 'model', 'name')
    ordering = ('machine_id',)
