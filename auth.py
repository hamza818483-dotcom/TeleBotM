import os
from functools import wraps

from services.settings_service import settings_service

def get_authorized_users():
    """Get list of authorized users from environment variables"""
    # Prefer Mongo; fallback to env
    users = [u.get('user_id') for u in settings_service.list_authorized_users()]
    if users:
        return users
    auth_users = os.getenv('AUTHORIZED_USERS', '')
    return [uid.strip() for uid in auth_users.split(',') if uid.strip()]

def check_authorization(func):
    """Decorator to check if the user is authorized to use the bot"""
    @wraps(func)
    async def wrapper(update, context):
        try:
            # Check if we have a valid update with user info
            user = None
            if update.effective_user:
                user = update.effective_user
            elif update.callback_query and update.callback_query.from_user:
                user = update.callback_query.from_user
            
            if not user:
                return
                
            user_id = str(user.id)
            authorized_users = get_authorized_users()
            is_admin = settings_service.is_authorized(user_id)
            if is_admin or not authorized_users or user_id in authorized_users:
                return await func(update, context)
            else:
                if hasattr(update, 'message') and update.message:
                    await update.message.reply_text(
                        "⛔️ You are not authorized to use this bot.\n"
                        "Please contact the administrator for access."
                    )
                elif hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.answer(
                        "⛔️ You are not authorized to use this bot.",
                        show_alert=True
                    )
        except Exception as e:
            print(f"Authorization error: {str(e)}")
            
    return wrapper 