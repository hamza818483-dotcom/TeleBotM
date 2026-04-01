import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import os
import time
import random
from typing import List, Dict, Optional, Tuple
from .prompt import get_prompt
from .bangla_textbook_prompt import get_bangla_textbook_prompt
from .mbbs_prompt import get_medical_mcq_prompt
from .custom_prompt import build_custom_prompt, build_custom_text_prompt


load_dotenv()

class GeminiKeyManager:
    """
    Manages multiple Gemini API keys with automatic rotation and health tracking.
    """
    
    def __init__(self):
        self.keys: List[str] = []
        self.key_stats: Dict[str, Dict] = {}
        self.current_key_index = 0
        self._load_keys()
        self._initialize_stats()
    
    def _load_keys(self):
        """Load API keys from environment variables."""
        # Primary key (backward compatibility)
        primary_key = os.getenv('GEMINI_API_KEY')
        if primary_key:
            self.keys.append(primary_key)
        
        # Additional keys
        additional_keys = os.getenv('GEMINI_API_KEYS', '')
        if additional_keys:
            # Support comma-separated or newline-separated keys
            keys = [key.strip() for key in additional_keys.replace('\n', ',').split(',') if key.strip()]
            self.keys.extend(keys)
        
        # Remove duplicates while preserving order
        seen = set()
        self.keys = [key for key in self.keys if not (key in seen or seen.add(key))]
        
        if not self.keys:
            raise ValueError("No Gemini API keys found. Please set GEMINI_API_KEY or GEMINI_API_KEYS in .env file")
        
        print(f"[KEY] Loaded {len(self.keys)} Gemini API key(s)")
    
    def _initialize_stats(self):
        """Initialize statistics for each key."""
        for key in self.keys:
            self.key_stats[key] = {
                'success_count': 0,
                'failure_count': 0,
                'last_used': None,
                'last_error': None,
                'is_healthy': True,
                'consecutive_failures': 0
            }
    
    def get_current_key(self) -> str:
        """Get the current active API key."""
        if not self.keys:
            raise ValueError("No API keys available")
        return self.keys[self.current_key_index]
    
    def get_healthy_keys(self) -> List[str]:
        """Get all healthy API keys."""
        return [key for key in self.keys if self.key_stats[key]['is_healthy']]
    
    def rotate_key(self, reason: str = "manual"):
        """Rotate to the next available key."""
        healthy_keys = self.get_healthy_keys()
        
        if not healthy_keys:
            print("[WARNING] No healthy keys available, resetting all keys to healthy")
            self._reset_all_keys()
            healthy_keys = self.keys
        
        # Find next healthy key
        current_key = self.get_current_key()
        try:
            current_index = healthy_keys.index(current_key)
            next_index = (current_index + 1) % len(healthy_keys)
        except ValueError:
            next_index = 0
        
        self.current_key_index = self.keys.index(healthy_keys[next_index])
        print(f"[ROTATE] Rotated to key {self.current_key_index + 1}/{len(self.keys)} ({reason})")
    
    def _reset_all_keys(self):
        """Reset all keys to healthy status."""
        for key in self.keys:
            self.key_stats[key]['is_healthy'] = True
            self.key_stats[key]['consecutive_failures'] = 0
    
    def record_success(self, key: str):
        """Record a successful API call."""
        if key in self.key_stats:
            self.key_stats[key]['success_count'] += 1
            self.key_stats[key]['last_used'] = time.time()
            self.key_stats[key]['consecutive_failures'] = 0
            self.key_stats[key]['is_healthy'] = True
    
    def record_failure(self, key: str, error: str):
        """Record a failed API call."""
        if key in self.key_stats:
            self.key_stats[key]['failure_count'] += 1
            self.key_stats[key]['last_error'] = error
            self.key_stats[key]['consecutive_failures'] += 1
            
            # Mark key as unhealthy after 3 consecutive failures
            if self.key_stats[key]['consecutive_failures'] >= 3:
                self.key_stats[key]['is_healthy'] = False
                print(f"[UNHEALTHY] Key {self.keys.index(key) + 1} marked as unhealthy after {self.key_stats[key]['consecutive_failures']} failures")
    
    def get_key_stats(self) -> Dict:
        """Get statistics for all keys."""
        return {
            'total_keys': len(self.keys),
            'healthy_keys': len(self.get_healthy_keys()),
            'current_key_index': self.current_key_index,
            'key_details': {
                f"key_{i+1}": {
                    'success_count': stats['success_count'],
                    'failure_count': stats['failure_count'],
                    'is_healthy': stats['is_healthy'],
                    'consecutive_failures': stats['consecutive_failures'],
                    'last_error': stats['last_error']
                }
                for i, (key, stats) in enumerate(self.key_stats.items())
            }
        }
    
    def get_random_healthy_key(self) -> Optional[str]:
        """Get a random healthy key for load balancing."""
        healthy_keys = self.get_healthy_keys()
        if not healthy_keys:
            return None
        return random.choice(healthy_keys)

# Global key manager instance
key_manager = GeminiKeyManager()

def setup_gemini(use_random_key: bool = False):
    """
    Initialize and configure the Gemini AI model with multi-key support.
    
    Args:
        use_random_key (bool): If True, use a random healthy key for load balancing
    
    Returns:
        Tuple[genai.GenerativeModel, str]: Configured Gemini model instance and the API key used
        
    Raises:
        ValueError: If no API keys are available
    """
    if use_random_key:
        api_key = key_manager.get_random_healthy_key()
        if not api_key:
            raise ValueError("No healthy API keys available")
    else:
        api_key = key_manager.get_current_key()
    
    genai.configure(api_key=api_key)
    
    # Simpler model initialization without unsupported config
    model = genai.GenerativeModel('gemini-2.5-flash')
    return model, api_key

def read_prompt():
    """Get the prompt text from the prompt module"""
    return get_prompt()

def extract_quiz_from_image(image_bytes, max_retries: int = 3):
    """
    Extract quiz content from an image using Gemini AI with multi-key support and automatic rotation.
    
    Args:
        image_bytes (bytes): Raw image data in bytes format
        max_retries (int): Maximum number of retry attempts with different keys
        
    Returns:
        str: Extracted text content from the image after processing
        
    Example:
        >>> with open('quiz_image.jpg', 'rb') as img:
        >>>     result = extract_quiz_from_image(img.read())
        >>> print(result)
    """
    image = Image.open(BytesIO(image_bytes))
    prompt = read_prompt()
    
    for attempt in range(max_retries):
        try:
            # Use random key for load balancing on first attempt, then rotate on failures
            use_random = (attempt == 0)
            model, api_key = setup_gemini(use_random_key=use_random)
            
            start_time = time.time()
            print(f"Starting Gemini API request (attempt {attempt + 1}/{max_retries}) at {start_time}")
            
            try:
                # Call without timeout parameter
                response = model.generate_content([prompt, image])
                
                end_time = time.time()
                print(f"Received response from Gemini 💬 in {end_time - start_time:.2f} seconds")
                
                if not response or not hasattr(response, 'text'):
                    print("Error: Empty or invalid response from Gemini API")
                    key_manager.record_failure(api_key, "Empty or invalid response")
                    if attempt < max_retries - 1:
                        key_manager.rotate_key("empty response")
                        continue
                    return "[]"  # Return empty JSON array as string
                
                # Record successful API call
                key_manager.record_success(api_key)
                return response.text
                
            except Exception as e:
                error_msg = str(e)
                print(f"Gemini API error (attempt {attempt + 1}): {error_msg}")
                key_manager.record_failure(api_key, error_msg)
                
                # Rotate to next key if this isn't the last attempt
                if attempt < max_retries - 1:
                    key_manager.rotate_key(f"API error: {error_msg[:50]}...")
                    continue
                else:
                    return "[]"  # Return empty JSON array as string
                    
        except Exception as e:
            print(f"Error in extract_quiz_from_image (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                key_manager.rotate_key(f"Setup error: {str(e)[:50]}...")
                continue
            return "[]"  # Return empty JSON array as string
    
    return "[]"  # Return empty JSON array as string

def extract_bangla_questions_from_textbook(image_bytes, max_retries: int = 3):
    """
    Extract and generate Bengali MCQs from a textbook image using Gemini AI with multi-key support and automatic rotation.
    
    Args:
        image_bytes (bytes): Raw image data in bytes format
        max_retries (int): Maximum number of retry attempts with different keys
        
    Returns:
        str: Generated Bengali MCQs in JSON format
        
    Example:
        >>> with open('textbook_image.jpg', 'rb') as img:
        >>>     result = extract_bangla_questions_from_textbook(img.read())
        >>> print(result)
    """
    image = Image.open(BytesIO(image_bytes))
    prompt = get_bangla_textbook_prompt()
    
    for attempt in range(max_retries):
        try:
            # Use random key for load balancing on first attempt, then rotate on failures
            use_random = (attempt == 0)
            model, api_key = setup_gemini(use_random_key=use_random)
            
            start_time = time.time()
            print(f"Starting Gemini API request for Bengali textbook (attempt {attempt + 1}/{max_retries}) at {start_time}")
            
            try:
                # Call without timeout parameter
                response = model.generate_content([prompt, image])
                
                end_time = time.time()
                print(f"Received Bengali MCQs from Gemini 💬 in {end_time - start_time:.2f} seconds")
                
                if not response or not hasattr(response, 'text'):
                    print("Error: Empty or invalid response from Gemini API")
                    key_manager.record_failure(api_key, "Empty or invalid response")
                    if attempt < max_retries - 1:
                        key_manager.rotate_key("empty response")
                        continue
                    return "[]"  # Return empty JSON array as string
                
                # Record successful API call
                key_manager.record_success(api_key)
                return response.text
                
            except Exception as e:
                error_msg = str(e)
                print(f"Gemini API error for Bengali textbook mode (attempt {attempt + 1}): {error_msg}")
                key_manager.record_failure(api_key, error_msg)
                
                # Rotate to next key if this isn't the last attempt
                if attempt < max_retries - 1:
                    key_manager.rotate_key(f"API error: {error_msg[:50]}...")
                    continue
                else:
                    return "[]"  # Return empty JSON array as string
                    
        except Exception as e:
            print(f"Error in extract_bangla_questions_from_textbook (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                key_manager.rotate_key(f"Setup error: {str(e)[:50]}...")
                continue
            return "[]"  # Return empty JSON array as string
    
    return "[]"  # Return empty JSON array as string


def extract_mbbs_questions_from_textbook(image_bytes, max_retries: int = 3):
    """
    Extract and generate medical MCQs from a textbook image using Gemini AI with multi-key support and automatic rotation.
    
    Args:
        image_bytes (bytes): Raw image data in bytes format
        max_retries (int): Maximum number of retry attempts with different keys
        
    Returns:
        str: Generated medical MCQs in JSON format
        
    Example:
        >>> with open('medical_textbook_image.jpg', 'rb') as img:
        >>>     result = extract_mbbs_questions_from_textbook(img.read())
        >>> print(result)
    """
    image = Image.open(BytesIO(image_bytes))
    prompt = get_medical_mcq_prompt()
    
    for attempt in range(max_retries):
        try:
            # Use random key for load balancing on first attempt, then rotate on failures
            use_random = (attempt == 0)
            model, api_key = setup_gemini(use_random_key=use_random)
            
            start_time = time.time()
            print(f"Starting Gemini API request for MBBS medical MCQs (attempt {attempt + 1}/{max_retries}) at {start_time}")
            
            try:
                # Call without timeout parameter
                response = model.generate_content([prompt, image])
                
                end_time = time.time()
                print(f"Received MBBS medical MCQs from Gemini 💬 in {end_time - start_time:.2f} seconds")
                
                if not response or not hasattr(response, 'text'):
                    print("Error: Empty or invalid response from Gemini API")
                    key_manager.record_failure(api_key, "Empty or invalid response")
                    if attempt < max_retries - 1:
                        key_manager.rotate_key("empty response")
                        continue
                    return "[]"  # Return empty JSON array as string
                
                # Record successful API call
                key_manager.record_success(api_key)
                return response.text
                
            except Exception as e:
                error_msg = str(e)
                print(f"Gemini API error for MBBS medical MCQs (attempt {attempt + 1}): {error_msg}")
                key_manager.record_failure(api_key, error_msg)
                
                # Rotate to next key if this isn't the last attempt
                if attempt < max_retries - 1:
                    key_manager.rotate_key(f"API error: {error_msg[:50]}...")
                    continue
                else:
                    return "[]"  # Return empty JSON array as string
                    
        except Exception as e:
            print(f"Error in extract_mbbs_questions_from_textbook (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                key_manager.rotate_key(f"Setup error: {str(e)[:50]}...")
                continue
            return "[]"  # Return empty JSON array as string
    
    return "[]"  # Return empty JSON array as string


def extract_custom_quiz_from_image(
    image_bytes,
    user_prompt: str,
    max_retries: int = 3,
    question_count: Optional[int] = None,
):
    """
    Generate Bengali MCQs from an image using a user-provided custom prompt.
    Enforces the same JSON schema the bot expects.
    """
    image = Image.open(BytesIO(image_bytes))
    prompt = build_custom_prompt(user_prompt, question_count)
    
    for attempt in range(max_retries):
        try:
            use_random = (attempt == 0)
            model, api_key = setup_gemini(use_random_key=use_random)
            
            start_time = time.time()
            print(f"Starting Gemini custom request (attempt {attempt + 1}/{max_retries}) at {start_time}")
            
            try:
                response = model.generate_content([prompt, image])
                end_time = time.time()
                print(f"Received custom response from Gemini in {end_time - start_time:.2f} seconds")
                
                if not response or not hasattr(response, 'text'):
                    key_manager.record_failure(api_key, "Empty or invalid response")
                    if attempt < max_retries - 1:
                        key_manager.rotate_key("empty response")
                        continue
                    return "[]"
                
                key_manager.record_success(api_key)
                return response.text
            
            except Exception as e:
                error_msg = str(e)
                print(f"Gemini custom API error (attempt {attempt + 1}): {error_msg}")
                key_manager.record_failure(api_key, error_msg)
                if attempt < max_retries - 1:
                    key_manager.rotate_key(f"API error: {error_msg[:50]}...")
                    continue
                else:
                    return "[]"
        except Exception as e:
            print(f"Error in extract_custom_quiz_from_image (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                key_manager.rotate_key(f"Setup error: {str(e)[:50]}...")
                continue
            return "[]"
    
    return "[]"


def extract_custom_quiz_from_text(
    text_content: str,
    user_prompt: str,
    max_retries: int = 3,
    question_count: Optional[int] = None,
) -> str:
    """
    Generate Bengali MCQs directly from textual content (no images) using Gemini.
    """
    prompt = build_custom_text_prompt(user_prompt, text_content, question_count)

    for attempt in range(max_retries):
        try:
            use_random = (attempt == 0)
            model, api_key = setup_gemini(use_random_key=use_random)

            start_time = time.time()
            print(f"Starting Gemini custom TEXT request (attempt {attempt + 1}/{max_retries})")

            try:
                response = model.generate_content(prompt)
                end_time = time.time()
                print(f"Received custom TEXT response in {end_time - start_time:.2f} seconds")

                if not response or not hasattr(response, 'text'):
                    key_manager.record_failure(api_key, "Empty or invalid text response")
                    if attempt < max_retries - 1:
                        key_manager.rotate_key("empty text response")
                        continue
                    return "[]"

                key_manager.record_success(api_key)
                return response.text

            except Exception as e:
                error_msg = str(e)
                print(f"Gemini custom TEXT API error (attempt {attempt + 1}): {error_msg}")
                key_manager.record_failure(api_key, error_msg)
                if attempt < max_retries - 1:
                    key_manager.rotate_key(f"API error: {error_msg[:50]}...")
                    continue
                return "[]"
        except Exception as e:
            print(f"Error in extract_custom_quiz_from_text (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                key_manager.rotate_key(f"Setup error: {str(e)[:50]}...")
                continue
            return "[]"

    return "[]"

# Utility functions for key management
def get_key_status():
    """
    Get the current status of all API keys.
    
    Returns:
        Dict: Status information including healthy keys count and detailed stats
    """
    return key_manager.get_key_stats()

def rotate_key_manually():
    """
    Manually rotate to the next available API key.
    
    Returns:
        str: The new active key
    """
    key_manager.rotate_key("manual rotation")
    return key_manager.get_current_key()

def reset_key_health():
    """
    Reset all keys to healthy status (useful for recovery after maintenance).
    
    Returns:
        int: Number of keys reset
    """
    key_manager._reset_all_keys()
    return len(key_manager.keys)

def get_healthy_key_count():
    """
    Get the number of currently healthy API keys.
    
    Returns:
        int: Number of healthy keys
    """
    return len(key_manager.get_healthy_keys())