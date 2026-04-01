import os
from urllib.parse import quote, quote_plus


def build_quiz_link(quiz_id: str) -> str:
    bot_username = os.getenv("BOT_USERNAME") or ""
    if not bot_username:
        # Fallback to start payload without username; user can share it manually
        return f"/start quiz_{quiz_id}"
    return f"https://t.me/{bot_username}?start={quote('quiz_' + quiz_id)}"


def build_quiz_share_url(quiz_id: str, title: str, description: str = "") -> str:
    link = build_quiz_link(quiz_id)
    share_text = f"{title}\n{description}".strip()
    return f"https://t.me/share/url?url={quote_plus(link)}&text={quote_plus(share_text or title)}"


