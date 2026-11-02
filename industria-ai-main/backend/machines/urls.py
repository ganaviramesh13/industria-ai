from django.urls import path
from .views import MachineListCreateView, MachineDetailUpdateView

urlpatterns = [
    path('', MachineListCreateView.as_view(), name='machine_list_create'),
    path('<int:pk>/', MachineDetailUpdateView.as_view(), name='machine_detail_update'),
]

