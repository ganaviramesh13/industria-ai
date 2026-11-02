import logging
import pymupdf
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class PDFExtractor:
    """
    Extracts text from PDF documents preserving original 1-based page numbering.
    """

    @staticmethod
    def extract_pages(pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extracts text page-by-page from the given PDF.
        Returns a list of dicts: [{'page_number': 1, 'text': '...', 'char_count': int}]
        """
        pages = []
        try:
            doc = pymupdf.open(pdf_path)
            total_pages = len(doc)
            logger.info(f"Opening PDF '{pdf_path}', total pages: {total_pages}")

            for page_idx in range(total_pages):
                page_num = page_idx + 1  # 1-based index matching printed manual folios
                page = doc[page_idx]
                text = page.get_text("text")

                cleaned_text = text.strip()
                if not cleaned_text:
                    logger.warning(f"Page {page_num} in '{pdf_path}' is empty or contains no extractable text.")
                    continue

                pages.append({
                    "page_number": page_num,
                    "text": cleaned_text,
                    "char_count": len(cleaned_text)
                })

            doc.close()
            return pages

        except Exception as e:
            logger.error(f"Error extracting PDF text from '{pdf_path}': {str(e)}")
            raise RuntimeError(f"Failed to process PDF '{pdf_path}': {str(e)}")

