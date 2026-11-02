from rest_framework import serializers
from .models import Manual
from machines.models import Machine


class ManualSerializer(serializers.ModelSerializer):
    machine_id = serializers.CharField(source='machine.machine_id', read_only=True)
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = Manual
        fields = [
            'id', 'machine', 'machine_id', 'document_id', 'title', 'revision',
            'pdf_file', 'uploaded_by', 'uploaded_by_username', 'uploaded_at',
            'indexing_status', 'chunk_count', 'page_count', 'error_message'
        ]
        read_only_fields = [
            'id', 'uploaded_by', 'uploaded_at', 'indexing_status',
            'chunk_count', 'page_count', 'error_message'
        ]


class ManualUploadSerializer(serializers.Serializer):
    machine_id = serializers.CharField(required=True)
    document_id = serializers.CharField(required=True)
    title = serializers.CharField(required=True)
    revision = serializers.CharField(default="1.0")
    pdf_file = serializers.FileField(required=True)

    def validate_pdf_file(self, value):
        if not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError("Only PDF manual documents are supported.")
        if value.size > 50 * 1024 * 1024:  # 50MB limit
            raise serializers.ValidationError("File size exceeds 50MB limit.")
        return value

    def validate_machine_id(self, value):
        try:
            return Machine.objects.get(machine_id=value)
        except Machine.DoesNotExist:
            raise serializers.ValidationError(f"Machine with ID '{value}' does not exist.")

