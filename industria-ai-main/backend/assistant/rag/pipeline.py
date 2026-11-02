import logging
from typing import Dict, Any, List, Optional
from .extractor import PDFExtractor
from .chunker import ManualChunker
from .vector_store import VectorStoreService
from .generator import RAGGenerator

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Central orchestration facade for the INDUSTRIA AI RAG system.
    Coordinates document extraction, chunking, persistent vector indexing,
    machine-isolated retrieval, grounded answer generation, and citation formatting.
    """

    def __init__(self):
        self.extractor = PDFExtractor()
        self.chunker = ManualChunker(target_chunk_size=450, overlap_size=80)
        self.vector_store = VectorStoreService()
        self.generator = RAGGenerator()

    def ingest_manual(
        self,
        pdf_path: str,
        machine_id: str,
        document_id: str,
        title: str,
        revision: str = "1.0"
    ) -> Dict[str, Any]:
        """
        Ingests a manual PDF:
        1. Extracts text per page preserving 1-based page numbers.
        2. Chunks page texts with full machine & document metadata.
        3. Persists vectors into ChromaDB (with automatic deduplication).
        """
        logger.info(f"Starting ingestion for {document_id} Rev {revision} ({machine_id}) from {pdf_path}")
        pages = self.extractor.extract_pages(pdf_path)
        if not pages:
            raise ValueError(f"No extractable text found in manual {pdf_path}")

        chunks = self.chunker.chunk_document(
            pages=pages,
            machine_id=machine_id,
            document_id=document_id,
            title=title,
            revision=revision
        )

        indexed_count = self.vector_store.index_chunks(chunks)

        return {
            "page_count": len(pages),
            "chunk_count": indexed_count,
            "status": "INDEXED"
        }

    def answer_question(
        self,
        machine_id: str,
        question: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Processes an engineer question with strict machine isolation:
        1. Enforces metadata filter: machine_id = selected_machine_id.
        2. Queries ChromaDB for most relevant passages.
        3. Synthesizes grounded answer and creates page-level citations.
        4. Handles insufficient evidence scenarios safely.
        """
        # Step 1: Query ChromaDB with strict machine isolation
        passages = self.vector_store.query_machine(
            machine_id=machine_id,
            query_text=question,
            top_k=top_k
        )

        # Step 2: Generate grounded response
        result = self.generator.generate_response(
            question=question,
            machine_id=machine_id,
            passages=passages
        )

        return result

