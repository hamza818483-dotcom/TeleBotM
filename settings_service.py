import os
import time
from typing import Any, Dict, List, Optional, Tuple

from .settings_store import SettingsStore


class SettingsService:
    def __init__(self, ttl_seconds: int = 30):
        self.store = SettingsStore()
        self.ttl = ttl_seconds
        self._cache: Dict[str, Tuple[float, Any]] = {}

    # Cache helpers
    def _get_cached(self, key: str):
        item = self._cache.get(key)
        if not item:
            return None
        ts, value = item
        if time.time() - ts > self.ttl:
            return None
        return value

    def _set_cached(self, key: str, value: Any):
        self._cache[key] = (time.time(), value)

    def invalidate(self):
        self._cache.clear()

    # Seeding from env on first run
    def seed_from_env_if_empty(self):
        cfg = self.store.get_app_config()
        if 'seeded' in cfg:
            return
        updates = {}
        for key, env_key in [
            ('quiz_marker', 'QUIZ_MARKER'),
            ('quiz_explanation_link', 'QUIZ_EXPLANATION_LINK'),
            ('explanation_mode', 'EXPLANATION_MODE'),
        ]:
            val = os.getenv(env_key)
            if val is not None and val != '':
                updates[key] = val
        # Default destinations (global, not per-user)
        channel_id = os.getenv('CHANNEL_ID')
        group_id = os.getenv('GROUP_ID')
        if channel_id:
            self.store.upsert_destination(channel_id, 'channel', None, None, True, 'env')
        if group_id:
            self.store.upsert_destination(group_id, 'group', None, None, True, 'env')
        updates['seeded'] = True
        self.store.set_app_config(updates)

        # Seed authorized users from env
        auth_users = [u.strip() for u in os.getenv('AUTHORIZED_USERS', '').split(',') if u.strip()]
        for uid in auth_users:
            self.store.add_authorized_user(uid, 'env')
    
    def get_default_channel_id(self, user_id: Optional[str] = None) -> Optional[int]:
        """Get default channel ID for user, with fallback to global"""
        if user_id:
            channels = self.list_channels(user_id)
            for d in channels:
                if d.get('is_default'):
                    try:
                        return int(d.get('chat_id'))
                    except (ValueError, TypeError):
                        pass
        # Fallback to global
        channels = self.list_channels()
        for d in channels:
            if d.get('is_default'):
                try:
                    return int(d.get('chat_id'))
                except (ValueError, TypeError):
                    pass
        # Final fallback to env
        channel_id = os.getenv('CHANNEL_ID')
        if channel_id:
            try:
                return int(channel_id)
            except (ValueError, TypeError):
                pass
        return None
    
    def get_default_group_id(self, user_id: Optional[str] = None) -> Optional[int]:
        """Get default group ID for user, with fallback to global"""
        if user_id:
            groups = self.list_groups(user_id)
            for d in groups:
                if d.get('is_default'):
                    try:
                        return int(d.get('chat_id'))
                    except (ValueError, TypeError):
                        pass
        # Fallback to global
        groups = self.list_groups()
        for d in groups:
            if d.get('is_default'):
                try:
                    return int(d.get('chat_id'))
                except (ValueError, TypeError):
                    pass
        # Final fallback to env
        group_id = os.getenv('GROUP_ID')
        if group_id:
            try:
                return int(group_id)
            except (ValueError, TypeError):
                pass
        return None

    # Getters (per-user with fallback to global)
    def get_quiz_marker(self, user_id: Optional[str] = None) -> str:
        if user_id:
            # Check user-specific setting first
            user_val = self.store.get_user_setting(user_id, 'quiz_marker')
            if user_val:
                return user_val
        # Fallback to global
        cache_key = f'quiz_marker_{user_id or "global"}'
        val = self._get_cached(cache_key)
        if val is not None:
            return val
        cfg = self.store.get_app_config()
        val = cfg.get('quiz_marker') or ''
        if not val:
            val = os.getenv('QUIZ_MARKER', '')
        self._set_cached(cache_key, val)
        return val

    def get_explanation_link(self, user_id: Optional[str] = None) -> str:
        if user_id:
            user_val = self.store.get_user_setting(user_id, 'quiz_explanation_link')
            if user_val:
                return user_val
        cache_key = f'quiz_explanation_link_{user_id or "global"}'
        val = self._get_cached(cache_key)
        if val is not None:
            return val
        cfg = self.store.get_app_config()
        val = cfg.get('quiz_explanation_link') or ''
        if not val:
            val = os.getenv('QUIZ_EXPLANATION_LINK', '')
        self._set_cached(cache_key, val)
        return val

    def get_explanation_mode(self, user_id: Optional[str] = None) -> str:
        if user_id:
            user_val = self.store.get_user_setting(user_id, 'explanation_mode')
            if user_val:
                return user_val
        cache_key = f'explanation_mode_{user_id or "global"}'
        val = self._get_cached(cache_key)
        if val is not None:
            return val
        cfg = self.store.get_app_config()
        val = cfg.get('explanation_mode') or os.getenv('EXPLANATION_MODE', 'off')
        self._set_cached(cache_key, val)
        return val

    def list_channels(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if user_id:
            return self.store.list_user_destinations(user_id, 'channel')
        return self.store.list_destinations('channel')

    def list_groups(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if user_id:
            return self.store.list_user_destinations(user_id, 'group')
        return self.store.list_destinations('group')

    def list_authorized_users(self) -> List[Dict[str, Any]]:
        return self.store.list_authorized_users()

    def is_authorized(self, user_id: str) -> bool:
        # If Mongo has no admin yet, allow env-based fallback
        if self.store.col_auth.estimated_document_count() == 0:
            env_auth = [u.strip() for u in os.getenv('AUTHORIZED_USERS', '').split(',') if u.strip()]
            return user_id in env_auth or len(env_auth) == 0
        return self.store.is_authorized(user_id)

    # Mutations (per-user)
    def set_quiz_marker(self, value: str, user_id: Optional[str] = None):
        if user_id:
            self.store.set_user_setting(user_id, 'quiz_marker', value)
        else:
            self.store.set_app_config({'quiz_marker': value})
        self.invalidate()

    def set_explanation_link(self, value: str, user_id: Optional[str] = None):
        if user_id:
            self.store.set_user_setting(user_id, 'quiz_explanation_link', value)
        else:
            self.store.set_app_config({'quiz_explanation_link': value})
        self.invalidate()

    def toggle_explanations(self, user_id: Optional[str] = None) -> str:
        current = self.get_explanation_mode(user_id)
        new_val = 'off' if str(current).lower() == 'on' else 'on'
        if user_id:
            self.store.set_user_setting(user_id, 'explanation_mode', new_val)
        else:
            self.store.set_app_config({'explanation_mode': new_val})
        self.invalidate()
        return new_val

    def add_destination(self, chat_id: str, dest_type: str, title: Optional[str], username: Optional[str], make_default: bool, added_by: Optional[str], user_id: Optional[str] = None):
        if user_id:
            if make_default:
                self.store.clear_user_default(user_id, dest_type)
            self.store.upsert_user_destination(user_id, chat_id, dest_type, title, username, make_default, added_by)
        else:
            if make_default:
                self.store.clear_default(dest_type)
            self.store.upsert_destination(chat_id, dest_type, title, username, make_default, added_by)

    def set_default_destination(self, chat_id: str, dest_type: str, user_id: Optional[str] = None):
        if user_id:
            # User-specific: check if destination exists, if not error
            user_dests = self.store.list_user_destinations(user_id, dest_type)
            exists = any(d.get('chat_id') == chat_id for d in user_dests)
            
            if not exists:
                raise ValueError(f"Destination {chat_id} not found. Please add it first using 'Add {dest_type.capitalize()}' button.")
            
            # Clear other defaults and set this one
            self.store.clear_user_default(user_id, dest_type)
            self.store.set_user_default_destination(user_id, chat_id)
            self.invalidate()
        else:
            # Global: set default
            self.store.clear_default(dest_type)
            self.store.set_default(chat_id)
            self.invalidate()

    def remove_destination(self, chat_id: str, user_id: Optional[str] = None):
        if user_id:
            self.store.remove_user_destination(user_id, chat_id)
        else:
            self.store.remove_destination(chat_id)

    def add_authorized_user(self, user_id: str, added_by: Optional[str]):
        self.store.add_authorized_user(user_id, added_by)

    def remove_authorized_user(self, user_id: str):
        self.store.remove_authorized_user(user_id)


# Global service instance
settings_service = SettingsService()


