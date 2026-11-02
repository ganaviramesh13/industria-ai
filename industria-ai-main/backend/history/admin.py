from django.contrib import admin
from .models import QuestionHistory


@admin.register(QuestionHistory)
class QuestionHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'selected_machine', 'short_question', 'status', 'created_at')
    list_filter = ('status', 'selected_machine', 'created_at')
    search_fields = ('question', 'answer', 'user__username', 'selected_machine__machine_id')

    def short_question(self, obj):
        return obj.question[:50] + "..." if len(obj.question) > 50 else obj.question
    short_question.short_description = "Question"
