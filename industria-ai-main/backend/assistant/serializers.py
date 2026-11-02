from rest_framework import serializers
from history.models import QuestionHistory
from machines.models import Machine
from manuals.models import Manual


class AskQuestionSerializer(serializers.Serializer):
    machine_id = serializers.CharField(required=True)
    question = serializers.CharField(required=True, min_length=2)

    def validate_machine_id(self, value):
        try:
            return Machine.objects.get(machine_id=value)
        except Machine.DoesNotExist:
            raise serializers.ValidationError(f"Machine with ID '{value}' was not found.")


class QuestionHistorySerializer(serializers.ModelSerializer):
    machine_id = serializers.CharField(source='selected_machine.machine_id', read_only=True)
    machine_model = serializers.CharField(source='selected_machine.model', read_only=True)
    machine_name = serializers.CharField(source='selected_machine.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)

    class Meta:
        model = QuestionHistory
        fields = [
            'id', 'user', 'username', 'user_role', 'selected_machine', 'machine_id',
            'machine_model', 'machine_name', 'question', 'answer',
            'status', 'citations', 'supporting_passages', 'reviewed', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']

