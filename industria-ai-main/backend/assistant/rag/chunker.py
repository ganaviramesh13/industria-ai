import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ManualChunker:
    """
    Chunks extracted manual pages into overlapping segments while preserving paragraph context
    and enriching every chunk with strict machine and document metadata.
    """

    def __init__(self, target_chunk_size: int = 500, overlap_size: int = 100):
        self.target_chunk_size = target_chunk_size
        self.overlap_size = overlap_size

    def chunk_document(
        self,
        pages: List[Dict[str, Any]],
        machine_id: str,
        document_id: str,
        title: str,
        revision: str
    ) -> List[Dict[str, Any]]:
        """
        Splits each page into overlapping chunks. Chunks are confined to a single page
        to ensure page-level citation accuracy and avoid multi-page cross contamination.
        """
        all_chunks = []

        clean_rev = revision.replace(".", "_")

        for page_data in pages:
            page_num = page_data["page_number"]
            page_text = page_data["text"]

            # Split into paragraphs/sections first
            paragraphs = [p.strip() for p in re.split(r'\n\s*\n', page_text) if p.strip()]

            if not paragraphs:
                continue

            current_chunk = ""
            chunk_idx = 1

            for para in paragraphs:
                # If paragraph alone is larger than target_chunk_size, split by sentences or lines
                if len(para) > self.target_chunk_size:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    for sent in sentences:
                        if len(current_chunk) + len(sent) > self.target_chunk_size and current_chunk:
                            chunk_id = f"{document_id}_rev{clean_rev}_p{page_num}_c{chunk_idx}"
                            all_chunks.append({
                                "chunk_id": chunk_id,
                                "text": current_chunk.strip(),
                                "metadata": {
                                    "machine_id": str(machine_id),
                                    "document_id": str(document_id),
                                    "document_title": str(title),
                                    "revision": str(revision),
                                    "page_number": int(page_num),
                                    "chunk_identifier": chunk_id
                                }
                            })
                            chunk_idx += 1
                            # Overlap from the end of current chunk
                            current_chunk = current_chunk[-self.overlap_size:] + " " + sent
                        else:
                            current_chunk = (current_chunk + " " + sent).strip()
                else:
                    if len(current_chunk) + len(para) > self.target_chunk_size and current_chunk:
                        chunk_id = f"{document_id}_rev{clean_rev}_p{page_num}_c{chunk_idx}"
                        all_chunks.append({
                            "chunk_id": chunk_id,
                            "text": current_chunk.strip(),
                            "metadata": {
                                "machine_id": str(machine_id),
                                "document_id": str(document_id),
                                "document_title": str(title),
                                "revision": str(revision),
                                "page_number": int(page_num),
                                "chunk_identifier": chunk_id
                            }
                        })
                        chunk_idx += 1
                        current_chunk = current_chunk[-self.overlap_size:] + "\n" + para
                    else:
                        current_chunk = (current_chunk + "\n\n" + para).strip()

            # Flush remaining chunk on this page
            if current_chunk.strip():
                chunk_id = f"{document_id}_rev{clean_rev}_p{page_num}_c{chunk_idx}"
                all_chunks.append({
                    "chunk_id": chunk_id,
                    "text": current_chunk.strip(),
                    "metadata": {
                        "machine_id": str(machine_id),
                        "document_id": str(document_id),
                        "document_title": str(title),
                        "revision": str(revision),
                        "page_number": int(page_num),
                        "chunk_identifier": chunk_id
                    }
                })

        logger.info(
            f"Chunked manual {document_id} (Rev {revision}, {machine_id}) into {len(all_chunks)} chunks across {len(pages)} pages."
        )
        return all_chunks

