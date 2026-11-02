import os
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings
import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

logger = logging.getLogger(__name__)


class LocalSentenceTransformerEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    Offline-resilient SentenceTransformer embedding function using cached all-MiniLM-L6-v2.
    """
    _instance = None
    _model = None

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        if LocalSentenceTransformerEmbeddingFunction._model is None:
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            try:
                from sentence_transformers import SentenceTransformer
                LocalSentenceTransformerEmbeddingFunction._model = SentenceTransformer(model_name)
                logger.info(f"Loaded SentenceTransformer '{model_name}' in offline mode.")
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer in offline mode: {e}. Trying fallback.")
                from sentence_transformers import SentenceTransformer
                LocalSentenceTransformerEmbeddingFunction._model = SentenceTransformer(model_name)

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = LocalSentenceTransformerEmbeddingFunction._model.encode(
            input,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        return embeddings.tolist()

    @staticmethod
    def name() -> str:
        return "sentence_transformer_minilm"


class VectorStoreService:
    """
    Manages persistent ChromaDB vector storage, indexing, and machine-isolated search.
    """

    def __init__(self, collection_name: str = "industrial_manuals"):
        self.persist_directory = str(getattr(settings, 'VECTOR_STORE_DIR', os.path.join(settings.BASE_DIR.parent, 'vector_store')))
        os.makedirs(self.persist_directory, exist_ok=True)

        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.embedding_function = LocalSentenceTransformerEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )

    def delete_document_chunks(self, machine_id: str, document_id: str, revision: Optional[str] = None) -> int:
        """
        Deletes all chunks belonging to a specific document to prevent duplication upon re-indexing.
        """
        try:
            where_clause = {
                "$and": [
                    {"machine_id": {"$eq": str(machine_id)}},
                    {"document_id": {"$eq": str(document_id)}}
                ]
            }
            if revision:
                where_clause["$and"].append({"revision": {"$eq": str(revision)}})

            existing = self.collection.get(where=where_clause)
            existing_ids = existing.get("ids", [])
            if existing_ids:
                self.collection.delete(ids=existing_ids)
                logger.info(f"Purged {len(existing_ids)} old chunks for {document_id} Rev {revision} on {machine_id}")
                return len(existing_ids)
            return 0
        except Exception as e:
            logger.warning(f"Error purging old chunks for {document_id}: {e}")
            return 0

    def index_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """
        Inserts chunks into the ChromaDB collection.
        Automatically deduplicates if chunks with the same ID already exist.
        """
        if not chunks:
            return 0

        # Purge any existing chunks for this specific document first
        sample = chunks[0]["metadata"]
        self.delete_document_chunks(
            machine_id=sample["machine_id"],
            document_id=sample["document_id"],
            revision=sample.get("revision")
        )

        ids = [c["chunk_id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Indexed {len(chunks)} chunks into ChromaDB.")
        return len(chunks)

    def query_machine(
        self,
        machine_id: str,
        query_text: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        CRITICAL ISOLATION: Queries ChromaDB enforcing metadata filter by machine_id.
        No passages from any other machine can ever be returned.
        """
        # Hard isolation filter at vector retrieval level
        filter_clause = {"machine_id": {"$eq": str(machine_id)}}

        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
            where=filter_clause
        )

        retrieved_passages = []
        if not results or not results.get("documents") or not results["documents"][0]:
            return []

        doc_list = results["documents"][0]
        meta_list = results["metadatas"][0]
        id_list = results["ids"][0]
        dist_list = results.get("distances", [[0.0] * len(doc_list)])[0]

        for text, meta, chunk_id, distance in zip(doc_list, meta_list, id_list, dist_list):
            # Double check isolation invariant
            if meta.get("machine_id") != str(machine_id):
                logger.error(f"SECURITY BREACH DETECTED: Filter leaked chunk {chunk_id} from {meta.get('machine_id')} into {machine_id}")
                continue

            retrieved_passages.append({
                "chunk_id": chunk_id,
                "text": text,
                "machine_id": meta.get("machine_id"),
                "document_id": meta.get("document_id"),
                "document_title": meta.get("document_title"),
                "revision": meta.get("revision"),
                "page_number": meta.get("page_number"),
                "distance": float(distance),
                "similarity": round(1.0 - float(distance), 4) if distance is not None else 1.0
            })

        return retrieved_passages

