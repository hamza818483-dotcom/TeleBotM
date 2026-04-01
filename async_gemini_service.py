import asyncio
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import os
import time
import random
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from .prompt import get_prompt
from .bangla_textbook_prompt import get_bangla_textbook_prompt
from .mbbs_prompt import get_medical_mcq_prompt

load_dotenv()

class AsyncGeminiService:
    """
    Async wrapper for Gemini API calls to prevent blocking the event loop.
    """
    
    def __init__(self, executor: ThreadPoolExecutor = None):
        self.executor = executor or ThreadPoolExecutor(max_workers=5, thread_name_prefix="gemini_worker")
        self.key_manager = None
        self._initialize_key_manager()
    
    def _initialize_key_manager(self):
        """Initialize the key manager from the synchronous service"""
        try:
            from .gemini_service import key_manager
            self.key_manager = key_manager
        except ImportError:
            # Fallback if import fails
            self.key_manager = None
    
    async def extract_quiz_from_image_async(self, image_bytes: bytes, max_retries: int = 3) -> str:
        """
        Async version of extract_quiz_from_image to prevent blocking.
        
        Args:
            image_bytes (bytes): Raw image data in bytes format
            max_retries (int): Maximum number of retry attempts with different keys
            
        Returns:
            str: Extracted text content from the image after processing
        """
        loop = asyncio.get_event_loop()
        
        # Run the synchronous function in a thread pool
        result = await loop.run_in_executor(
            self.executor,
            self._extract_quiz_sync,
            image_bytes,
            max_retries
        )
        return result
    
    async def extract_bangla_questions_from_textbook_async(self, image_bytes: bytes, max_retries: int = 3) -> str:
        """
        Async version of extract_bangla_questions_from_textbook to prevent blocking.
        
        Args:
            image_bytes (bytes): Raw image data in bytes format
            max_retries (int): Maximum number of retry attempts with different keys
            
        Returns:
            str: Generated Bengali MCQs in JSON format
        """
        loop = asyncio.get_event_loop()
        
        # Run the synchronous function in a thread pool
        result = await loop.run_in_executor(
            self.executor,
            self._extract_bangla_questions_sync,
            image_bytes,
            max_retries
        )
        return result
    
    async def extract_mbbs_questions_from_textbook_async(self, image_bytes: bytes, max_retries: int = 3) -> str:
        """
        Async version of extract_mbbs_questions_from_textbook to prevent blocking.
        
        Args:
            image_bytes (bytes): Raw image data in bytes format
            max_retries (int): Maximum number of retry attempts with different keys
            
        Returns:
            str: Generated medical MCQs in JSON format
        """
        loop = asyncio.get_event_loop()
        
        # Run the synchronous function in a thread pool
        result = await loop.run_in_executor(
            self.executor,
            self._extract_mbbs_questions_sync,
            image_bytes,
            max_retries
        )
        return result
    
    async def extract_custom_quiz_async(
        self,
        image_bytes: bytes,
        user_prompt: str,
        max_retries: int = 3,
        question_count: Optional[int] = None,
    ) -> str:
        """Async wrapper for custom prompt based extraction."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            self._extract_custom_sync,
            image_bytes,
            user_prompt,
            max_retries,
            question_count,
        )
        return result

    async def extract_custom_quiz_from_text_async(
        self,
        text_content: str,
        user_prompt: str,
        max_retries: int = 3,
        question_count: Optional[int] = None,
    ) -> str:
        """Async wrapper for text-based custom quiz generation."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._extract_custom_text_sync,
            text_content,
            user_prompt,
            max_retries,
            question_count,
        )
    
    def _extract_quiz_sync(self, image_bytes: bytes, max_retries: int) -> str:
        """Synchronous version for thread pool execution"""
        try:
            from .gemini_service import extract_quiz_from_image
            return extract_quiz_from_image(image_bytes, max_retries)
        except Exception as e:
            print(f"Error in async quiz extraction: {str(e)}")
            return "[]"
    
    def _extract_bangla_questions_sync(self, image_bytes: bytes, max_retries: int) -> str:
        """Synchronous version for thread pool execution"""
        try:
            from .gemini_service import extract_bangla_questions_from_textbook
            return extract_bangla_questions_from_textbook(image_bytes, max_retries)
        except Exception as e:
            print(f"Error in async Bengali questions extraction: {str(e)}")
            return "[]"
    
    def _extract_mbbs_questions_sync(self, image_bytes: bytes, max_retries: int) -> str:
        """Synchronous version for thread pool execution"""
        try:
            from .gemini_service import extract_mbbs_questions_from_textbook
            return extract_mbbs_questions_from_textbook(image_bytes, max_retries)
        except Exception as e:
            print(f"Error in async MBBS questions extraction: {str(e)}")
            return "[]"
    
    def _extract_custom_sync(
        self,
        image_bytes: bytes,
        user_prompt: str,
        max_retries: int,
        question_count: Optional[int] = None,
    ) -> str:
        try:
            from .gemini_service import extract_custom_quiz_from_image
            return extract_custom_quiz_from_image(image_bytes, user_prompt, max_retries, question_count)
        except Exception as e:
            print(f"Error in async custom extraction: {str(e)}")
            return "[]"

    def _extract_custom_text_sync(
        self,
        text_content: str,
        user_prompt: str,
        max_retries: int,
        question_count: Optional[int] = None,
    ) -> str:
        try:
            from .gemini_service import extract_custom_quiz_from_text
            return extract_custom_quiz_from_text(text_content, user_prompt, max_retries, question_count)
        except Exception as e:
            print(f"Error in async custom text extraction: {str(e)}")
            return "[]"
    
    def cleanup(self):
        """Clean up the executor"""
        if self.executor:
            self.executor.shutdown(wait=False)

# Global async service instance
async_gemini_service = AsyncGeminiService()
