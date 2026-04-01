import os
from typing import Optional

from pymongo import MongoClient


_client: Optional[MongoClient] = None


def get_mongo_client() -> MongoClient:
    global _client
    if _client is not None:
        return _client

    uri = os.getenv('MONGODB_URI')
    if not uri:
        raise ValueError('MONGODB_URI not set')

    _client = MongoClient(uri, appname='tss-bot')
    return _client


def get_db():
    client = get_mongo_client()
    db_name = os.getenv('MONGODB_DB', 'tss_bot')
    return client[db_name]


