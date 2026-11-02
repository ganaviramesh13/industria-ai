from django.contrib import admin
from .models import Manual


@admin.register(Manual)
class ManualAdmin(admin.ModelAdmin):
    list_display = ('document_id', 'revision', 'title', 'machine', 'indexing_status', 'page_count', 'chunk_count', 'uploaded_at')
    list_filter = ('indexing_status', 'machine', 'revision')
    search_fields = ('document_id', 'title', 'machine__machine_id')
