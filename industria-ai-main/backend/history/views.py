from django.db.models import Count, Q
from rest_framework import status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import QuestionHistory
from assistant.serializers import QuestionHistorySerializer
from accounts.permissions import IsSupervisor
from machines.models import Machine


class SupervisorDashboardView(APIView):
    """
    Returns aggregated audit metrics and machine-wise statistics.
    Read-only, strictly for Supervisors and Administrators.
    """
    permission_classes = [IsSupervisor]

    def get(self, request):
        total_questions = QuestionHistory.objects.count()
        answered_count = QuestionHistory.objects.filter(status=QuestionHistory.Status.ANSWERED).count()
        insufficient_count = QuestionHistory.objects.filter(status=QuestionHistory.Status.INSUFFICIENT_EVIDENCE).count()
        reviewed_count = QuestionHistory.objects.filter(reviewed=True).count()

        # Machine-wise distribution
        machine_stats = []
        for m in Machine.objects.all():
            m_total = QuestionHistory.objects.filter(selected_machine=m).count()
            m_answered = QuestionHistory.objects.filter(selected_machine=m, status=QuestionHistory.Status.ANSWERED).count()
            m_insufficient = QuestionHistory.objects.filter(selected_machine=m, status=QuestionHistory.Status.INSUFFICIENT_EVIDENCE).count()
            machine_stats.append({
                "machine_id": m.machine_id,
                "model": m.model,
                "name": m.name,
                "total_questions": m_total,
                "answered_count": m_answered,
                "insufficient_count": m_insufficient
            })

        # Knowledge gaps summary
        gaps_qs = QuestionHistory.objects.filter(
            status=QuestionHistory.Status.INSUFFICIENT_EVIDENCE
        ).select_related('selected_machine', 'user')[:5]
        gaps_serialized = QuestionHistorySerializer(gaps_qs, many=True).data

        # Recent 10 queries
        recent = QuestionHistory.objects.select_related('selected_machine', 'user')[:10]
        recent_serialized = QuestionHistorySerializer(recent, many=True).data

        return Response({
            "metrics": {
                "total_questions": total_questions,
                "answered_questions": answered_count,
                "unanswered_questions": insufficient_count,
                "insufficient_evidence_questions": insufficient_count,
                "reviewed_questions": reviewed_count,
                "evidence_rate_percentage": round((answered_count / total_questions * 100), 1) if total_questions > 0 else 0.0
            },
            "machine_distribution": machine_stats,
            "knowledge_gaps": gaps_serialized,
            "recent_questions": recent_serialized
        }, status=status.HTTP_200_OK)


class SupervisorQuestionListView(generics.ListAPIView):
    """
    Comprehensive, filterable question history across all engineers.
    Supports filtering by machine_id, engineer (username/id), status, and date.
    """
    serializer_class = QuestionHistorySerializer
    permission_classes = [IsSupervisor]

    def get_queryset(self):
        qs = QuestionHistory.objects.all().select_related('selected_machine', 'user')

        # Filter by machine
        machine_id = self.request.query_params.get('machine_id')
        if machine_id:
            qs = qs.filter(selected_machine__machine_id=machine_id)

        # Filter by status (answered vs insufficient_evidence)
        q_status = self.request.query_params.get('status')
        if q_status:
            qs = qs.filter(status=q_status)

        # Filter by reviewed status
        reviewed_param = self.request.query_params.get('reviewed')
        if reviewed_param is not None:
            if reviewed_param.lower() in ('true', '1'):
                qs = qs.filter(reviewed=True)
            elif reviewed_param.lower() in ('false', '0'):
                qs = qs.filter(reviewed=False)

        # Filter by engineer username
        engineer = self.request.query_params.get('engineer')
        if engineer:
            qs = qs.filter(user__username__icontains=engineer)

        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        date_to = self.request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        return qs


class MarkReviewedView(APIView):
    """
    PATCH /api/supervisor/questions/<pk>/review/
    Allows Supervisors and Administrators to mark questions as reviewed.
    """
    permission_classes = [IsSupervisor]

    def patch(self, request, pk):
        try:
            entry = QuestionHistory.objects.get(pk=pk)
        except QuestionHistory.DoesNotExist:
            return Response({"error": "Question history entry not found."}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('reviewed', True)
        if isinstance(new_status, str):
            new_status = new_status.lower() in ('true', '1', 'yes')

        entry.reviewed = bool(new_status)
        entry.save(update_fields=['reviewed'])

        return Response({
            "message": "Question review status updated successfully.",
            "entry": QuestionHistorySerializer(entry).data
        }, status=status.HTTP_200_OK)


class KnowledgeGapsView(APIView):
    """
    GET /api/supervisor/knowledge-gaps/
    Returns all questions flagged with insufficient evidence,
    highlighting technical areas missing from the current manuals.
    """
    permission_classes = [IsSupervisor]

    def get(self, request):
        qs = QuestionHistory.objects.filter(
            status=QuestionHistory.Status.INSUFFICIENT_EVIDENCE
        ).select_related('selected_machine', 'user')

        machine_id = request.query_params.get('machine_id')
        if machine_id:
            qs = qs.filter(selected_machine__machine_id=machine_id)

        data = QuestionHistorySerializer(qs, many=True).data
        return Response({
            "count": len(data),
            "results": data
        }, status=status.HTTP_200_OK)
