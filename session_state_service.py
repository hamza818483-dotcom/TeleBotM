"""
Centralized session state management service.

Consolidates scattered state management from handlers into a single service
for better organization, testability, and consistency.
"""

from typing import Dict, Any, Optional, Set, List
import asyncio


class SessionStateService:
    """
    Centralized service for managing user session state.
    
    Replaces scattered global dicts in config.py with a clean, organized interface.
    Provides thread-safe state management for concurrent users.
    """
    
    def __init__(self):
        # User-specific quiz data
        self._user_quiz_data: Dict[int, Dict[str, Any]] = {}
        
        # User mode selections
        self._user_modes: Dict[int, str] = {}
        self._user_textbook_modes: Dict[int, str] = {}
        self._user_mbbs_modes: Dict[int, bool] = {}
        self._user_exam_tag_modes: Dict[int, bool] = {}
        self._user_exam_tags: Dict[int, str] = {}
        
        # Media group tracking for batch image processing
        self._media_groups: Dict[str, List[bytes]] = {}
        self._processed_media_groups: Set[str] = set()
        self._media_group_status_messages: Dict[str, int] = {}
        self._media_group_tasks: Dict[str, asyncio.Task] = {}
        
        # Poll collection state
        self._user_collected_polls: Dict[int, List[Dict]] = {}
        self._user_poll_collection_mode: Dict[int, bool] = {}
        self._user_poll_status_messages: Dict[int, int] = {}
        
        # PDF handling state
        self._user_waiting_for_pdf_pages: Dict[int, bool] = {}
        self._user_pdf_documents: Dict[int, Any] = {}
        self._user_last_images: Dict[int, List[bytes]] = {}
        self._user_pdf_image_source_mode: Dict[int, bool] = {}
        self._user_image_source_batches: Dict[int, Dict] = {}
        
        # User topics
        self._user_topics: Dict[int, int] = {}
        self._user_source_images: Dict[int, List[bytes]] = {}
        
        # Locks for thread safety
        self._locks: Dict[int, asyncio.Lock] = {}
    
    def _get_lock(self, user_id: int) -> asyncio.Lock:
        """Get or create a lock for a user."""
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]
    
    # ===== Quiz Data =====
    
    def get_quiz_data(self, user_id: int) -> Dict[str, Any]:
        """Get user's quiz data."""
        return self._user_quiz_data.get(user_id, {})
    
    def set_quiz_data(self, user_id: int, data: Dict[str, Any]) -> None:
        """Set user's quiz data."""
        self._user_quiz_data[user_id] = data
    
    def clear_quiz_data(self, user_id: int) -> None:
        """Clear user's quiz data."""
        self._user_quiz_data.pop(user_id, None)
    
    # ===== User Modes =====
    
    def get_mode(self, user_id: int) -> Optional[str]:
        """Get user's selected mode."""
        return self._user_modes.get(user_id)
    
    def set_mode(self, user_id: int, mode: str) -> None:
        """Set user's mode."""
        self._user_modes[user_id] = mode
    
    def get_textbook_mode(self, user_id: int) -> Optional[str]:
        """Get user's textbook mode."""
        return self._user_textbook_modes.get(user_id)
    
    def set_textbook_mode(self, user_id: int, mode: str) -> None:
        """Set user's textbook mode."""
        self._user_textbook_modes[user_id] = mode
    
    def is_mbbs_mode(self, user_id: int) -> bool:
        """Check if user has MBBS mode enabled."""
        return self._user_mbbs_modes.get(user_id, False)
    
    def set_mbbs_mode(self, user_id: int, enabled: bool) -> None:
        """Set user's MBBS mode."""
        self._user_mbbs_modes[user_id] = enabled
    
    def is_exam_tag_mode(self, user_id: int) -> bool:
        """Check if user has exam tag mode enabled."""
        return self._user_exam_tag_modes.get(user_id, False)
    
    def set_exam_tag_mode(self, user_id: int, enabled: bool) -> None:
        """Set user's exam tag mode."""
        self._user_exam_tag_modes[user_id] = enabled
    
    def get_exam_tag(self, user_id: int) -> Optional[str]:
        """Get user's exam tag."""
        return self._user_exam_tags.get(user_id)
    
    def set_exam_tag(self, user_id: int, tag: str) -> None:
        """Set user's exam tag."""
        self._user_exam_tags[user_id] = tag
    
    # ===== Media Groups =====
    
    def add_media_group(self, media_group_id: str, images: List[bytes]) -> None:
        """Add a media group."""
        self._media_groups[media_group_id] = images
    
    def get_media_group(self, media_group_id: str) -> Optional[List[bytes]]:
        """Get a media group."""
        return self._media_groups.get(media_group_id)
    
    def mark_media_group_processed(self, media_group_id: str) -> None:
        """Mark a media group as processed."""
        self._processed_media_groups.add(media_group_id)
    
    def is_media_group_processed(self, media_group_id: str) -> bool:
        """Check if a media group was processed."""
        return media_group_id in self._processed_media_groups
    
    def set_media_group_status_message(self, media_group_id: str, message_id: int) -> None:
        """Set status message ID for a media group."""
        self._media_group_status_messages[media_group_id] = message_id
    
    def get_media_group_status_message(self, media_group_id: str) -> Optional[int]:
        """Get status message ID for a media group."""
        return self._media_group_status_messages.get(media_group_id)
    
    def set_media_group_task(self, media_group_id: str, task: asyncio.Task) -> None:
        """Set async task for a media group."""
        self._media_group_tasks[media_group_id] = task
    
    def get_media_group_task(self, media_group_id: str) -> Optional[asyncio.Task]:
        """Get async task for a media group."""
        return self._media_group_tasks.get(media_group_id)
    
    def clear_media_group(self, media_group_id: str) -> None:
        """Clear all data for a media group."""
        self._media_groups.pop(media_group_id, None)
        self._processed_media_groups.discard(media_group_id)
        self._media_group_status_messages.pop(media_group_id, None)
        self._media_group_tasks.pop(media_group_id, None)
    
    # ===== Poll Collection =====
    
    def get_collected_polls(self, user_id: int) -> List[Dict]:
        """Get user's collected polls."""
        return self._user_collected_polls.get(user_id, [])
    
    def add_collected_poll(self, user_id: int, poll_data: Dict) -> None:
        """Add a poll to user's collection."""
        if user_id not in self._user_collected_polls:
            self._user_collected_polls[user_id] = []
        self._user_collected_polls[user_id].append(poll_data)
    
    def clear_collected_polls(self, user_id: int) -> None:
        """Clear user's collected polls."""
        self._user_collected_polls[user_id] = []
    
    def is_poll_collection_enabled(self, user_id: int) -> bool:
        """Check if poll collection is enabled."""
        return self._user_poll_collection_mode.get(user_id, False)
    
    def set_poll_collection_mode(self, user_id: int, enabled: bool) -> None:
        """Enable/disable poll collection."""
        self._user_poll_collection_mode[user_id] = enabled
    
    def set_poll_status_message(self, user_id: int, message_id: int) -> None:
        """Set poll collection status message ID."""
        self._user_poll_status_messages[user_id] = message_id
    
    def get_poll_status_message(self, user_id: int) -> Optional[int]:
        """Get poll collection status message ID."""
        return self._user_poll_status_messages.get(user_id)
    
    # ===== PDF Handling =====
    
    def is_waiting_for_pdf_pages(self, user_id: int) -> bool:
        """Check if user is waiting for PDF pages."""
        return self._user_waiting_for_pdf_pages.get(user_id, False)
    
    def set_waiting_for_pdf_pages(self, user_id: int, waiting: bool) -> None:
        """Set if user is waiting for PDF pages."""
        self._user_waiting_for_pdf_pages[user_id] = waiting
    
    def set_pdf_document(self, user_id: int, document: Any) -> None:
        """Store PDF document for user."""
        self._user_pdf_documents[user_id] = document
    
    def get_pdf_document(self, user_id: int) -> Optional[Any]:
        """Get user's PDF document."""
        return self._user_pdf_documents.get(user_id)
    
    def set_last_images(self, user_id: int, images: List[bytes]) -> None:
        """Store user's last images."""
        self._user_last_images[user_id] = images
    
    def get_last_images(self, user_id: int) -> List[bytes]:
        """Get user's last images."""
        return self._user_last_images.get(user_id, [])
    
    def is_pdf_image_source_mode(self, user_id: int) -> bool:
        """Check if user is in PDF image source mode."""
        return self._user_pdf_image_source_mode.get(user_id, False)
    
    def set_pdf_image_source_mode(self, user_id: int, enabled: bool) -> None:
        """Set PDF image source mode."""
        self._user_pdf_image_source_mode[user_id] = enabled
    
    def set_image_source_batch(self, user_id: int, batch_data: Dict) -> None:
        """Store image source batch."""
        self._user_image_source_batches[user_id] = batch_data
    
    def get_image_source_batch(self, user_id: int) -> Optional[Dict]:
        """Get user's image source batch."""
        return self._user_image_source_batches.get(user_id)
    
    # ===== Topics and Images =====
    
    def set_user_topic(self, user_id: int, topic_id: int) -> None:
        """Set user's active topic."""
        self._user_topics[user_id] = topic_id
    
    def get_user_topic(self, user_id: int) -> Optional[int]:
        """Get user's active topic."""
        return self._user_topics.get(user_id)
    
    def set_source_images(self, user_id: int, images: List[bytes]) -> None:
        """Store source images."""
        self._user_source_images[user_id] = images
    
    def get_source_images(self, user_id: int) -> List[bytes]:
        """Get source images."""
        return self._user_source_images.get(user_id, [])
    
    # ===== Cleanup =====
    
    def clear_user_state(self, user_id: int) -> None:
        """Clear all state for a user."""
        self._user_quiz_data.pop(user_id, None)
        self._user_modes.pop(user_id, None)
        self._user_textbook_modes.pop(user_id, None)
        self._user_mbbs_modes.pop(user_id, None)
        self._user_exam_tag_modes.pop(user_id, None)
        self._user_exam_tags.pop(user_id, None)
        self._user_topics.pop(user_id, None)
        self._user_source_images.pop(user_id, None)
        self._user_waiting_for_pdf_pages.pop(user_id, None)
        self._user_pdf_documents.pop(user_id, None)
        self._user_last_images.pop(user_id, None)
        self._user_pdf_image_source_mode.pop(user_id, None)
        self._user_image_source_batches.pop(user_id, None)
        self._user_collected_polls.pop(user_id, None)
        self._user_poll_collection_mode.pop(user_id, None)
        self._user_poll_status_messages.pop(user_id, None)
        self._locks.pop(user_id, None)


# Global singleton instance
session_state_service = SessionStateService()
