from rest_framework import generics, permissions
from .models import Machine
from .serializers import MachineSerializer
from accounts.permissions import IsAdministrator


class MachineListCreateView(generics.ListCreateAPIView):
    queryset = Machine.objects.all()
    serializer_class = MachineSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [IsAdministrator()]


class MachineDetailUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Machine.objects.all()
    serializer_class = MachineSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [IsAdministrator()]
