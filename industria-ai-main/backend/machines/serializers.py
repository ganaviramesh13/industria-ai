from rest_framework import serializers
from .models import Machine


class MachineSerializer(serializers.ModelSerializer):
    manuals_count = serializers.SerializerMethodField()

    class Meta:
        model = Machine
        fields = ['id', 'machine_id', 'name', 'model', 'description', 'created_at', 'manuals_count']
        read_only_fields = ['id', 'created_at', 'manuals_count']

    def get_manuals_count(self, obj):
        return obj.manuals.count()

