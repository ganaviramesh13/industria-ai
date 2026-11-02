from django.urls import path
from .views import (
    ManualListView,
    ManualDetailView,
    ManualUploadView,
    ManualReindexView,
    ManualPDFStreamView
)

urlpatterns = [
    path('', ManualListView.as_view(), name='manual_list'),
    path('upload/', ManualUploadView.as_view(), name='manual_upload'),
    path('<int:pk>/', ManualDetailView.as_view(), name='manual_detail'),
    path('<int:pk>/reindex/', ManualReindexView.as_view(), name='manual_reindex'),
    path('<int:pk>/pdf/', ManualPDFStreamView.as_view(), name='manual_pdf_stream'),
]

