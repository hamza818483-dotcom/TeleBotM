from typing import Any, Dict, List, Optional
from datetime import datetime

from .mongo_client import get_db


APP_CONFIG_ID = 'singleton'


class SettingsStore:
    def __init__(self):
        self.db = get_db()
        self.col_config = self.db['app_config']
        self.col_auth = self.db['authorized_users']
        self.col_dest = self.db['destinations']
        self.col_user_settings = self.db['user_settings']

    # App config
    def get_app_config(self) -> Dict[str, Any]:
        doc = self.col_config.find_one({'_id': APP_CONFIG_ID})
        return doc or {'_id': APP_CONFIG_ID}

    def set_app_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        self.col_config.update_one(
            {'_id': APP_CONFIG_ID},
            {'$set': updates, '$setOnInsert': {'created_at': datetime.utcnow()}},
            upsert=True,
        )
        return self.get_app_config()

    # Authorized users
    def list_authorized_users(self) -> List[Dict[str, Any]]:
        return list(self.col_auth.find({}, {'_id': 0}).sort('created_at', 1))

    def is_authorized(self, user_id: str) -> bool:
        return self.col_auth.count_documents({'user_id': user_id}, limit=1) > 0

    def add_authorized_user(self, user_id: str, added_by: Optional[str]) -> None:
        self.col_auth.update_one(
            {'user_id': user_id},
            {'$setOnInsert': {'user_id': user_id, 'added_by': added_by, 'created_at': datetime.utcnow()}},
            upsert=True,
        )

    def remove_authorized_user(self, user_id: str) -> None:
        self.col_auth.delete_one({'user_id': user_id})

    # Destinations
    def list_destinations(self, dest_type: Optional[str] = None) -> List[Dict[str, Any]]:
        query = {}
        if dest_type:
            query['type'] = dest_type
        return list(self.col_dest.find(query, {'_id': 0}).sort([('is_default', -1), ('created_at', 1)]))

    def upsert_destination(self, chat_id: str, dest_type: str, title: Optional[str], username: Optional[str], is_default: bool, added_by: Optional[str]) -> None:
        now = datetime.utcnow()
        self.col_dest.update_one(
            {'chat_id': chat_id},
            {'$set': {'type': dest_type, 'title': title, 'username': username, 'is_default': is_default, 'updated_at': now},
             '$setOnInsert': {'created_at': now, 'added_by': added_by}},
            upsert=True,
        )

    def remove_destination(self, chat_id: str) -> None:
        self.col_dest.delete_one({'chat_id': chat_id})

    def clear_default(self, dest_type: str) -> None:
        self.col_dest.update_many({'type': dest_type, 'is_default': True}, {'$set': {'is_default': False}})

    def set_default(self, chat_id: str) -> None:
        self.col_dest.update_one({'chat_id': chat_id}, {'$set': {'is_default': True}})

    # Per-user settings
    def get_user_settings(self, user_id: str) -> Dict[str, Any]:
        doc = self.col_user_settings.find_one({'_id': user_id})
        return doc or {'_id': user_id}

    def set_user_setting(self, user_id: str, key: str, value: Any) -> None:
        now = datetime.utcnow()
        self.col_user_settings.update_one(
            {'_id': user_id},
            {'$set': {key: value, 'updated_at': now},
             '$setOnInsert': {'created_at': now}},
            upsert=True,
        )

    def get_user_setting(self, user_id: str, key: str, default: Any = None) -> Any:
        doc = self.get_user_settings(user_id)
        return doc.get(key, default)

    def list_user_destinations(self, user_id: str, dest_type: Optional[str] = None) -> List[Dict[str, Any]]:
        query = {'user_id': user_id}
        if dest_type:
            query['type'] = dest_type
        return list(self.col_dest.find(query, {'_id': 0}).sort([('is_default', -1), ('created_at', 1)]))

    def upsert_user_destination(self, user_id: str, chat_id: str, dest_type: str, title: Optional[str], username: Optional[str], is_default: bool, added_by: Optional[str]) -> None:
        now = datetime.utcnow()
        self.col_dest.update_one(
            {'chat_id': chat_id, 'user_id': user_id},
            {'$set': {'type': dest_type, 'title': title, 'username': username, 'is_default': is_default, 'updated_at': now, 'user_id': user_id},
             '$setOnInsert': {'created_at': now, 'added_by': added_by}},
            upsert=True,
        )

    def clear_user_default(self, user_id: str, dest_type: str) -> None:
        self.col_dest.update_many({'user_id': user_id, 'type': dest_type, 'is_default': True}, {'$set': {'is_default': False}})

    def set_user_default_destination(self, user_id: str, chat_id: str) -> None:
        self.col_dest.update_one({'chat_id': chat_id, 'user_id': user_id}, {'$set': {'is_default': True}})

    def remove_user_destination(self, user_id: str, chat_id: str) -> None:
        self.col_dest.delete_one({'chat_id': chat_id, 'user_id': user_id})


