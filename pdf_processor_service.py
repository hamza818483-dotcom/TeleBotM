"""
Enhanced PDF processing service implementing the complete pipeline:
- Download → Storage → Tracking → Conversion → Extraction → Export

Based on best practices from tested MCQ bot implementation.
"""

import asyncio
import os
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import fitz  # PyMuPDF
from PIL import Image
import io

logger = logging.getLogger(__name__)


@dataclass
class PDFProcessingState:
    """Tracks state during PDF processing."""
    timestamp: int  # Processing session ID (ms)
    pdf_path: str
    page_range: Optional[Tuple[int, int]]
    custom_name: Optional[str]
    total_pages: int
    all_questions: List[Dict] = None
    all_raw_texts: List[str] = None
    last_page_num: Optional[int] = None
    last_page_extracted: int = 0
    current_retry_count: int = 0
    
    def __post_init__(self):
        if self.all_questions is None:
            self.all_questions = []
        if self.all_raw_texts is None:
            self.all_raw_texts = []


class PDFProcessorService:
    """Enhanced PDF processing with caching, tracking, and retries."""
    
    # Global image cache to prevent reprocessing
    _image_cache: Dict[str, List[Dict]] = {}
    
    # Temp file tracking for cleanup
    _temp_files: List[str] = []
    
    # Processing state tracking
    _processing_states: Dict[str, PDFProcessingState] = {}
    
    MAX_PAGE_RETRIES = 3
    CLEANUP_INTERVAL = 60  # seconds
    
    def __init__(self):
        self._last_cleanup = time.time()
    
    @staticmethod
    def _generate_session_id() -> int:
        """Generate unique session ID based on millisecond timestamp."""
        return int(time.time() * 1000)
    
    @staticmethod
    def _get_temp_image_path(session_id: int, page_num: int) -> str:
        """Generate temp image path with session tracking."""
        return f"temp_page_{session_id}_{page_num}.jpg"
    
    async def process_pdf(
        self,
        pdf_path: str,
        page_range: Optional[str] = None,
        custom_name: Optional[str] = None,
        progress_callback=None
    ) -> Tuple[List[Dict], List[str], Optional[str]]:
        """
        Complete PDF processing pipeline.
        
        Args:
            pdf_path: Path to downloaded PDF
            page_range: Optional "start-end" format (e.g., "1-10")
            custom_name: Custom name for outputs
            progress_callback: Async function(message) for progress updates
        
        Returns:
            (questions, raw_responses, error_message)
        """
        session_id = self._generate_session_id()
        logger.info(f"Starting PDF processing session {session_id}: {pdf_path}")
        
        try:
            # Parse page range
            parsed_range = self._parse_page_range(page_range, pdf_path)
            if not parsed_range and page_range:
                return [], [], "Invalid page range format"
            
            start_page, end_page = parsed_range or (1, self._get_pdf_page_count(pdf_path))
            
            # Initialize state
            state = PDFProcessingState(
                timestamp=session_id,
                pdf_path=pdf_path,
                page_range=parsed_range,
                custom_name=custom_name,
                total_pages=end_page - start_page + 1
            )
            self._processing_states[str(session_id)] = state
            
            # Convert PDF to images
            await self._send_progress(progress_callback, "📄 Converting PDF to images...")
            images = self._pdf_to_images(pdf_path, start_page, end_page)
            
            if not images:
                return [], [], "Failed to convert PDF to images"
            
            # Process each page
            for idx, (page_num, image_pil) in enumerate(images, 1):
                await self._process_page(
                    session_id,
                    page_num,
                    image_pil,
                    idx,
                    state,
                    progress_callback
                )
            
            logger.info(
                f"Completed session {session_id}: "
                f"{len(state.all_questions)} questions extracted"
            )
            
            return state.all_questions, state.all_raw_texts, None
            
        except Exception as e:
            error_msg = f"PDF processing failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return [], [], error_msg
        
        finally:
            # Cleanup
            await self._cleanup_session(session_id)
    
    async def _process_page(
        self,
        session_id: int,
        page_num: int,
        image_pil: Image.Image,
        page_index: int,
        state: PDFProcessingState,
        progress_callback
    ) -> None:
        """Process single PDF page with retry logic."""
        temp_path = self._get_temp_image_path(session_id, page_num)
        
        try:
            # Save temp image
            image_pil.save(temp_path, 'JPEG')
            self._temp_files.append(temp_path)
            
            # Retry loop for this page
            for retry_attempt in range(self.MAX_PAGE_RETRIES):
                state.current_retry_count = retry_attempt
                
                # Update progress
                progress_msg = (
                    f"📄 Processing page {page_num} "
                    f"({page_index}/{state.total_pages})"
                )
                if retry_attempt > 0:
                    progress_msg += f" [Retry {retry_attempt}/{self.MAX_PAGE_RETRIES}]"
                
                if state.last_page_num and state.last_page_extracted:
                    progress_msg += (
                        f"\n✅ Previous: {state.last_page_extracted} questions "
                        f"(Total: {len(state.all_questions)})"
                    )
                
                await self._send_progress(progress_callback, progress_msg)
                
                # Extract questions from image
                try:
                    questions, raw_text = await self._extract_questions_from_image(temp_path)
                    
                    if questions:
                        state.all_questions.extend(questions)
                        state.last_page_extracted = len(questions)
                        state.last_page_num = page_num
                        
                        if raw_text:
                            state.all_raw_texts.append(raw_text)
                        
                        logger.info(
                            f"Session {session_id}, Page {page_num}: "
                            f"{len(questions)} questions extracted"
                        )
                        break  # Success, exit retry loop
                    else:
                        # No questions found, retry
                        if retry_attempt < self.MAX_PAGE_RETRIES - 1:
                            await asyncio.sleep(2)
                            continue
                        else:
                            logger.warning(
                                f"Session {session_id}, Page {page_num}: "
                                f"No questions after {self.MAX_PAGE_RETRIES} attempts"
                            )
                
                except Exception as e:
                    logger.error(
                        f"Session {session_id}, Page {page_num}, "
                        f"Attempt {retry_attempt + 1}: {str(e)}"
                    )
                    if retry_attempt < self.MAX_PAGE_RETRIES - 1:
                        await asyncio.sleep(1)
                    else:
                        logger.error(
                            f"Session {session_id}, Page {page_num}: "
                            f"Failed after {self.MAX_PAGE_RETRIES} attempts"
                        )
        
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    self._temp_files.remove(temp_path)
                    logger.debug(f"Cleaned up temp file: {temp_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup {temp_path}: {e}")
    
    def _pdf_to_images(
        self,
        pdf_path: str,
        start_page: int,
        end_page: int
    ) -> List[Tuple[int, Image.Image]]:
        """Convert PDF pages to PIL Images."""
        try:
            doc = fitz.open(pdf_path)
            images = []
            
            for page_idx in range(start_page - 1, min(end_page, doc.page_count)):
                try:
                    page = doc[page_idx]
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for quality
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    images.append((page_idx + 1, img))  # Return 1-indexed page number
                except Exception as e:
                    logger.error(f"Failed to convert page {page_idx + 1}: {e}")
                    continue
            
            doc.close()
            return images
        
        except Exception as e:
            logger.error(f"PDF to images conversion failed: {e}")
            return []
    
    async def _extract_questions_from_image(
        self,
        image_path: str
    ) -> Tuple[List[Dict], Optional[str]]:
        """Extract questions from image using AI service."""
        # Check cache first
        if image_path in self._image_cache:
            logger.info(f"Returning cached result for image: {image_path}")
            return self._image_cache[image_path], None
        
        try:
            # Import gemini service
            from services.async_gemini_service import async_gemini_service
            
            # Extract questions
            result = await async_gemini_service.extract_quiz_from_image(image_path)
            
            if result:
                questions, raw_text = result if isinstance(result, tuple) else (result, None)
                
                # Cache result
                self._image_cache[image_path] = questions
                
                return questions, raw_text
            
            return [], None
        
        except Exception as e:
            logger.error(f"Question extraction failed for {image_path}: {e}")
            return [], None
    
    def _parse_page_range(
        self,
        page_range_str: Optional[str],
        pdf_path: str
    ) -> Optional[Tuple[int, int]]:
        """Parse page range like '1-10' or '5'."""
        if not page_range_str:
            return None
        
        try:
            total_pages = self._get_pdf_page_count(pdf_path)
            
            if '-' in page_range_str:
                parts = page_range_str.split('-')
                start = int(parts[0].strip())
                end = int(parts[1].strip())
            else:
                start = end = int(page_range_str.strip())
            
            if 1 <= start <= total_pages and 1 <= end <= total_pages and start <= end:
                return (start, end)
            else:
                logger.warning(
                    f"Invalid page range: {page_range_str} (PDF has {total_pages} pages)"
                )
                return None
        
        except Exception as e:
            logger.error(f"Failed to parse page range '{page_range_str}': {e}")
            return None
    
    @staticmethod
    def _get_pdf_page_count(pdf_path: str) -> int:
        """Get total pages in PDF."""
        try:
            doc = fitz.open(pdf_path)
            count = doc.page_count
            doc.close()
            return count
        except Exception as e:
            logger.error(f"Failed to get page count: {e}")
            return 0
    
    async def _cleanup_session(self, session_id: int) -> None:
        """Clean up session data."""
        if str(session_id) in self._processing_states:
            del self._processing_states[str(session_id)]
        
        # Periodic full cleanup
        if time.time() - self._last_cleanup > self.CLEANUP_INTERVAL:
            self._cleanup_temp_files()
            self._last_cleanup = time.time()
    
    def _cleanup_temp_files(self) -> None:
        """Clean up orphaned temp files."""
        for temp_file in self._temp_files[:]:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                self._temp_files.remove(temp_file)
                logger.debug(f"Cleaned up orphaned: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {temp_file}: {e}")
    
    @staticmethod
    async def _send_progress(callback, message: str) -> None:
        """Send progress update if callback provided."""
        if callback:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    def get_cache_stats(self) -> Dict:
        """Get current cache statistics."""
        return {
            'cached_images': len(self._image_cache),
            'pending_temp_files': len(self._temp_files),
            'active_sessions': len(self._processing_states),
            'cache_size_bytes': sum(
                len(str(k)) + len(str(v))
                for k, v in self._image_cache.items()
            )
        }
    
    def clear_cache(self) -> None:
        """Clear image cache (useful for memory management)."""
        cache_size = len(self._image_cache)
        self._image_cache.clear()
        logger.info(f"Cleared image cache ({cache_size} entries)")


# Singleton instance
pdf_processor_service = PDFProcessorService()
