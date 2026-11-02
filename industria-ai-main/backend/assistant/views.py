import logging
from rest_framework import status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from history.models import QuestionHistory
from machines.models import Machine
from manuals.models import Manual
from .serializers import AskQuestionSerializer, QuestionHistorySerializer
from .rag.pipeline import RAGPipeline
from accounts.permissions import IsEngineer

logger = logging.getLogger(__name__)


class AskQuestionView(APIView):
    """
    Submits an industrial question for a selected machine.
    Enforces strict machine-isolated RAG retrieval.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AskQuestionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        machine = serializer.validated_data['machine_id']
        question = serializer.validated_data['question'].strip()

        rag = RAGPipeline()
        rag_output = rag.answer_question(
            machine_id=machine.machine_id,
            question=question
        )

        status_result = rag_output.get("status", "answered")
        answer_text = rag_output.get("answer", "")
        citations = rag_output.get("citations", [])
        passages = rag_output.get("supporting_passages", [])

        # Enrich citations with manual_id so frontend can link directly to the PDF
        for c in citations:
            doc_id = c.get("document_id")
            manual = Manual.objects.filter(
                machine=machine,
                document_id=doc_id
            ).first()
            if manual:
                c["manual_id"] = manual.id

        # Record interaction into QuestionHistory
        history_entry = QuestionHistory.objects.create(
            user=request.user,
            selected_machine=machine,
            question=question,
            answer=answer_text,
            status=status_result,
            citations=citations,
            supporting_passages=passages
        )

        return Response({
            "history_id": history_entry.id,
            "selected_machine": {
                "id": machine.id,
                "machine_id": machine.machine_id,
                "model": machine.model,
                "name": machine.name
            },
            "question": question,
            "answer": answer_text,
            "status": status_result,
            "citations": citations,
            "supporting_passages": passages,
            "created_at": history_entry.created_at
        }, status=status.HTTP_200_OK)


class PersonalHistoryListView(generics.ListAPIView):
    """
    Returns personal question history for the authenticated user.
    """
    serializer_class = QuestionHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = QuestionHistory.objects.filter(user=self.request.user).select_related('selected_machine', 'user')
        machine_id = self.request.query_params.get('machine_id')
        if machine_id:
            qs = qs.filter(selected_machine__machine_id=machine_id)
        return qs


class PersonalHistoryDetailView(generics.RetrieveAPIView):
    """
    Returns details of a specific question history.
    Engineers can only access their own history; Admins/Supervisors can view any.
    """
    serializer_class = QuestionHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['ADMIN', 'SUPERVISOR'] or user.is_superuser:
            return QuestionHistory.objects.all().select_related('selected_machine', 'user')
        return QuestionHistory.objects.filter(user=user).select_related('selected_machine', 'user')
