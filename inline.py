from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.deeplink import build_quiz_link, build_quiz_share_url


def build_creation_summary_keyboard(quiz_id: str, title: str, description: str):
    link = build_quiz_link(quiz_id)
    share_url = build_quiz_share_url(quiz_id, title, description)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Preview & start here", callback_data=f"quiz:prompt:{quiz_id}")],
        [InlineKeyboardButton("Start in a group", url=share_url)],
        [InlineKeyboardButton("Copy link", callback_data=f"quiz:copy_link:{quiz_id}")]
    ])


def build_creation_settings_keyboard(shuffle_q: bool, shuffle_o: bool, negative: bool):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"Shuffle Questions: {'ON' if shuffle_q else 'OFF'}", callback_data="quiz:set:shuffle_q"),
            InlineKeyboardButton(f"Shuffle Options: {'ON' if shuffle_o else 'OFF'}", callback_data="quiz:set:shuffle_o"),
        ],
        [
            InlineKeyboardButton(f"Negative (-0.25): {'ON' if negative else 'OFF'}", callback_data="quiz:set:negative"),
        ],
        [InlineKeyboardButton("Done", callback_data="quiz:settings_done")]
    ])


