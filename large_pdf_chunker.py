"""
Smart PDF chunking for large files (>20MB).
Splits PDFs into manageable chunks for processing.
"""

import os
import tempfile
from typing import List, Tuple
import fitz  # PyMuPDF


class LargePDFChunker:
    """Intelligently splits large PDFs into chunks."""
    
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
    MAX_CHUNK_SIZE = 15 * 1024 * 1024  # 15MB per chunk
    PAGES_PER_CHUNK = 50  # Fallback: split every 50 pages
    
    @staticmethod
    def should_chunk(file_size: int) -> bool:
        """Check if file needs chunking."""
        return file_size > LargePDFChunker.MAX_FILE_SIZE
    
    @staticmethod
    def get_pdf_page_count(pdf_path: str) -> int:
        """Get number of pages in PDF."""
        try:
            doc = fitz.open(pdf_path)
            count = doc.page_count
            doc.close()
            return count
        except Exception as e:
            print(f"Error counting PDF pages: {e}")
            return 0
    
    @staticmethod
    def chunk_pdf(pdf_path: str, file_size: int) -> List[Tuple[str, int, int]]:
        """
        Split PDF into chunks.
        Returns: List of (chunk_path, start_page, end_page)
        """
        if not LargePDFChunker.should_chunk(file_size):
            return [(pdf_path, 1, LargePDFChunker.get_pdf_page_count(pdf_path))]
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = doc.page_count
            doc.close()
            
            chunks = []
            current_page = 1
            chunk_num = 0
            
            while current_page <= total_pages:
                # Calculate end page for this chunk
                end_page = min(current_page + LargePDFChunker.PAGES_PER_CHUNK - 1, total_pages)
                
                # Create temporary file for chunk
                chunk_path = f"{pdf_path}.chunk_{chunk_num}.pdf"
                
                # Extract pages for this chunk
                doc = fitz.open(pdf_path)
                chunk_doc = fitz.open()
                for page_num in range(current_page - 1, end_page):
                    chunk_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                chunk_doc.save(chunk_path)
                chunk_doc.close()
                doc.close()
                
                chunks.append((chunk_path, current_page, end_page))
                current_page = end_page + 1
                chunk_num += 1
            
            return chunks
            
        except Exception as e:
            print(f"Error chunking PDF: {e}")
            return [(pdf_path, 1, LargePDFChunker.get_pdf_page_count(pdf_path))]
    
    @staticmethod
    def cleanup_chunks(chunks: List[Tuple[str, int, int]]) -> None:
        """Delete temporary chunk files."""
        for chunk_path, _, _ in chunks:
            if chunk_path.endswith('.chunk_') or '.chunk_' in chunk_path:
                try:
                    os.unlink(chunk_path)
                except Exception as e:
                    print(f"Error cleaning up chunk {chunk_path}: {e}")


large_pdf_chunker = LargePDFChunker()
