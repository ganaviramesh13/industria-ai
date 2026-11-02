import os
import logging
from django.http import FileResponse, Http404
from rest_framework import status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Manual
from .serializers import ManualSerializer, ManualUploadSerializer
from accounts.permissions import IsAdministrator
from assistant.rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)


class ManualListView(generics.ListAPIView):
    serializer_class = ManualSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Manual.objects.all().select_related('machine', 'uploaded_by')
        machine_id = self.request.query_params.get('machine_id')
        if machine_id:
            queryset = queryset.filter(machine__machine_id=machine_id)
        return queryset


class ManualDetailView(generics.RetrieveAPIView):
    queryset = Manual.objects.all().select_related('machine', 'uploaded_by')
    serializer_class = ManualSerializer
    permission_classes = [permissions.IsAuthenticated]


class ManualUploadView(APIView):
    """
    CRITICAL ACCESS CONTROL: Only Administrators can upload manuals.
    Engineers and Supervisors receive HTTP 403 Forbidden.
    """
    permission_classes = [IsAdministrator]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = ManualUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        machine = serializer.validated_data['machine_id']
        document_id = serializer.validated_data['document_id']
        title = serializer.validated_data['title']
        revision = serializer.validated_data['revision']
        pdf_file = serializer.validated_data['pdf_file']

        # Create or update manual record
        manual, created = Manual.objects.update_or_create(
            machine=machine,
            document_id=document_id,
            revision=revision,
            defaults={
                'title': title,
                'pdf_file': pdf_file,
                'uploaded_by': request.user,
                'indexing_status': Manual.IndexingStatus.PROCESSING,
                'error_message': ''
            }
        )

        # Trigger RAG Ingestion Pipeline
        try:
            rag = RAGPipeline()
            result = rag.ingest_manual(
                pdf_path=manual.pdf_file.path,
                machine_id=machine.machine_id,
                document_id=document_id,
                title=title,
                revision=revision
            )
            manual.page_count = result["page_count"]
            manual.chunk_count = result["chunk_count"]
            manual.indexing_status = Manual.IndexingStatus.INDEXED
            manual.error_message = ""
            manual.save()

            return Response(ManualSerializer(manual).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Ingestion failed for manual {document_id}: {str(e)}")
            manual.indexing_status = Manual.IndexingStatus.FAILED
            manual.error_message = str(e)
            manual.save()
            return Response({
                "error": f"Document uploaded but indexing failed: {str(e)}",
                "manual": ManualSerializer(manual).data
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ManualReindexView(APIView):
    """
    Re-index an existing manual document.
    Admin only.
    """
    permission_classes = [IsAdministrator]

    def post(self, request, pk):
        try:
            manual = Manual.objects.get(pk=pk)
        except Manual.DoesNotExist:
            return Response({"error": "Manual not found."}, status=status.HTTP_404_NOT_FOUND)

        manual.indexing_status = Manual.IndexingStatus.PROCESSING
        manual.save()

        try:
            rag = RAGPipeline()
            result = rag.ingest_manual(
                pdf_path=manual.pdf_file.path,
                machine_id=manual.machine.machine_id,
                document_id=manual.document_id,
                title=manual.title,
                revision=manual.revision
            )
            manual.page_count = result["page_count"]
            manual.chunk_count = result["chunk_count"]
            manual.indexing_status = Manual.IndexingStatus.INDEXED
            manual.error_message = ""
            manual.save()

            return Response({
                "message": f"Successfully re-indexed {manual.document_id} Rev {manual.revision}",
                "manual": ManualSerializer(manual).data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Re-indexing failed: {e}")
            manual.indexing_status = Manual.IndexingStatus.FAILED
            manual.error_message = str(e)
            manual.save()
            return Response({"error": f"Re-indexing failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ManualPDFStreamView(APIView):
    """
    Serves the PDF file safely for inline viewing and jumping to specific page numbers.
    Accessible to authenticated users (Engineers, Supervisors, Admins).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            manual = Manual.objects.get(pk=pk)
        except Manual.DoesNotExist:
            raise Http404("Manual not found.")

        if not manual.pdf_file or not os.path.exists(manual.pdf_file.path):
            raise Http404("PDF file not found on disk.")

        response = FileResponse(open(manual.pdf_file.path, 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(manual.pdf_file.name)}"'
        return response
