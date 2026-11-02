from django.urls import path
from .views import (
    SupervisorDashboardView,
    SupervisorQuestionListView,
    MarkReviewedView,
    KnowledgeGapsView
)

urlpatterns = [
    path('dashboard/', SupervisorDashboardView.as_view(), name='supervisor_dashboard'),
    path('questions/', SupervisorQuestionListView.as_view(), name='supervisor_questions'),
    path('questions/<int:pk>/review/', MarkReviewedView.as_view(), name='supervisor_mark_reviewed'),
    path('knowledge-gaps/', KnowledgeGapsView.as_view(), name='supervisor_knowledge_gaps'),
]
