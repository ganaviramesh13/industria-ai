from django.urls import path
from .views import AskQuestionView, PersonalHistoryListView, PersonalHistoryDetailView

urlpatterns = [
    path('ask/', AskQuestionView.as_view(), name='assistant_ask'),
    path('history/', PersonalHistoryListView.as_view(), name='assistant_history'),
    path('history/<int:pk>/', PersonalHistoryDetailView.as_view(), name='assistant_history_detail'),
]

