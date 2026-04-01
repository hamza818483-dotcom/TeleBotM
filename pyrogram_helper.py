"""
Pyrogram helper service for downloading large files (>20MB) that PTB cannot handle.
This service runs alongside python-telegram-bot to handle large file downloads.
"""
import os
import asyncio
import logging
import tempfile
from typing import Optional
from pyrogram import Client
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class PyrogramHelper:
    """Helper class to download large files using Pyrogram"""
    
    _client: Optional[Client] = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_client(cls) -> Optional[Client]:
        """Get or create Pyrogram client instance (singleton) using user account for large file downloads"""
        if cls._client is None:
            async with cls._lock:
                if cls._client is None:  # Double-check locking
                    try:
                        # Try user account first (for files >20MB)
                        api_id = os.getenv('TELEGRAM_API_ID')
                        api_hash = os.getenv('TELEGRAM_API_HASH')
                        session_string = os.getenv('TELEGRAM_SESSION_STRING')
                        
                        if api_id and api_hash:
                            # Use user account (can download up to 2GB)
                            try:
                                api_id_int = int(api_id)
                            except ValueError:
                                logger.error("TELEGRAM_API_ID must be a valid integer")
                                return None
                            
                            # Use session string if provided (for CI/CD, GitHub Actions, etc.)
                            if session_string:
                                # When using session_string, name is still required but session file won't be created
                                # The session_string contains all authentication info
                                if not session_string.strip():
                                    logger.error("TELEGRAM_SESSION_STRING is empty")
                                    return None
                                
                                cls._client = Client(
                                    "tss_bot_pyrogram_user",
                                    api_id=api_id_int,
                                    api_hash=api_hash,
                                    session_string=session_string.strip(),
                                    no_updates=True  # Don't handle updates, just download files
                                )
                                logger.info("Using session string for Pyrogram authentication")
                                
                                try:
                                    await cls._client.start()
                                    logger.info("Pyrogram user account client initialized successfully with session string (supports files up to 2GB)")
                                except Exception as start_error:
                                    logger.error(f"Failed to start Pyrogram client with session string: {str(start_error)}")
                                    logger.error("Please verify your TELEGRAM_SESSION_STRING is valid and not expired")
                                    cls._client = None
                                    return None
                            else:
                                # For interactive auth, use session name to save session file
                                cls._client = Client(
                                    "tss_bot_pyrogram_user",
                                    api_id=api_id_int,
                                    api_hash=api_hash,
                                    no_updates=True  # Don't handle updates, just download files
                                )
                                
                                try:
                                    await cls._client.start()
                                    logger.info("Pyrogram user account client initialized successfully (supports files up to 2GB)")
                                except Exception as start_error:
                                    logger.error(f"Failed to start Pyrogram client: {str(start_error)}")
                                    logger.error("If running in CI/CD, you must set TELEGRAM_SESSION_STRING to avoid interactive authentication")
                                    cls._client = None
                                    return None
                        else:
                            # Fallback to bot token (20MB limit)
                            bot_token = os.getenv('BOT_TOKEN')
                            if not bot_token:
                                logger.error("Either TELEGRAM_API_ID/API_HASH or BOT_TOKEN must be set for Pyrogram")
                                return None
                            
                            logger.warning("Using bot token for Pyrogram (20MB limit). For larger files, set TELEGRAM_API_ID and TELEGRAM_API_HASH")
                            cls._client = Client(
                                "tss_bot_pyrogram",
                                bot_token=bot_token,
                                no_updates=True,
                                in_memory=True
                            )
                            
                            await cls._client.start()
                            logger.info("Pyrogram bot client initialized successfully (20MB limit)")
                            
                    except Exception as e:
                        logger.error(f"Failed to initialize Pyrogram client: {str(e)}")
                        cls._client = None
                        return None
        
        return cls._client
    
    @classmethod
    async def download_large_file(cls, chat_id: int, message_id: int, bot_id: Optional[int] = None, bot_username: Optional[str] = None) -> Optional[bytes]:
        """
        Download a large file using Pyrogram
        
        Args:
            chat_id: Telegram chat ID (from bot's perspective)
            message_id: Telegram message ID containing the document
            bot_id: Bot's Telegram ID (optional, for private chat conversion)
            bot_username: Bot's username (optional, preferred for user accounts)
            
        Returns:
            File bytes if successful, None otherwise
        """
        try:
            client = await cls.get_client()
            if not client:
                logger.error("Pyrogram client not available")
                return None
            
            logger.info(f"Attempting to download message {message_id} from chat {chat_id}")
            
            # Determine the correct chat_id for user account
            # If chat_id is positive (user ID in private chat), and we're using user account,
            # we need to access the chat from user's perspective (bot's username or ID)
            actual_chat_id = chat_id
            
            # Check if we're using user account (not bot token)
            session_string = os.getenv('TELEGRAM_SESSION_STRING')
            api_id = os.getenv('TELEGRAM_API_ID')
            api_hash = os.getenv('TELEGRAM_API_HASH')
            is_user_account = bool(api_id and api_hash)
            
            # For user accounts accessing private chats with bots
            if is_user_account and chat_id > 0:
                # Private chat from bot's perspective (chat_id = user ID)
                # From user account's perspective, use bot's username (preferred) or bot ID
                if bot_username:
                    actual_chat_id = bot_username
                    logger.info(f"Using user account: Converting chat_id from {chat_id} (user ID) to bot username '{bot_username}'")
                elif bot_id and bot_id < 0:
                    actual_chat_id = bot_id
                    logger.info(f"Using user account: Converting chat_id from {chat_id} (user ID) to {actual_chat_id} (bot ID)")
                else:
                    # Try original chat_id first (might work in some cases)
                    actual_chat_id = chat_id
                    logger.info(f"Using user account: Trying original chat_id {chat_id} (user ID)")
            
            # Try to get the message - support both int chat_id and username
            message = None
            last_error = None
            successful_chat_id = None
            
            # Try multiple chat_id formats for user accounts
            chat_ids_to_try = [actual_chat_id]
            if is_user_account and chat_id > 0:
                # Add fallback options
                if bot_username and actual_chat_id != bot_username:
                    chat_ids_to_try.append(bot_username)
                if bot_id and actual_chat_id != bot_id:
                    chat_ids_to_try.append(bot_id)
                # Also try original chat_id as last resort
                if actual_chat_id != chat_id:
                    chat_ids_to_try.append(chat_id)
            
            for try_chat_id in chat_ids_to_try:
                try:
                    logger.info(f"Trying to get message {message_id} from chat: {try_chat_id}")
                    message = await client.get_messages(try_chat_id, message_id)
                    if message:
                        logger.info(f"Successfully found message using chat_id: {try_chat_id}")
                        successful_chat_id = try_chat_id
                        # Log message details for debugging
                        logger.debug(f"Message type: {type(message)}")
                        logger.debug(f"Message has document: {bool(message.document)}")
                        logger.debug(f"Message has photo: {bool(message.photo)}")
                        logger.debug(f"Message is forwarded: {bool(message.forward_from or message.forward_from_chat)}")
                        if message.forward_from or message.forward_from_chat:
                            logger.info("Message is forwarded - checking if original message is accessible")
                        break
                except Exception as get_msg_error:
                    last_error = get_msg_error
                    logger.warning(f"Failed with chat_id {try_chat_id}: {str(get_msg_error)}")
                    continue
            
            if not message:
                logger.error(f"Failed to get message after trying all chat_id formats")
                logger.error(f"Original Chat ID: {chat_id}, Message ID: {message_id}")
                logger.error(f"Tried chat_ids: {chat_ids_to_try}")
                if last_error:
                    logger.error(f"Last error: {str(last_error)}")
                logger.error("Note: User account must have access to the chat where the message was sent")
                logger.error("Make sure the user account has started a chat with the bot")
                return None
            
            # Check what media type the message has
            media_type = None
            if message.document:
                media_type = "document"
            elif message.photo:
                media_type = "photo"
            elif message.video:
                media_type = "video"
            elif message.audio:
                media_type = "audio"
            elif message.voice:
                media_type = "voice"
            elif message.video_note:
                media_type = "video_note"
            elif message.sticker:
                media_type = "sticker"
            elif message.animation:
                media_type = "animation"
            
            if not message.document:
                logger.error(f"Message {message_id} does not contain a document")
                if media_type:
                    logger.error(f"Message contains {media_type} instead of document")
                    logger.error("Note: PyrogramHelper.download_large_file() is designed for document downloads")
                    logger.error("For photos, videos, or other media types, use the appropriate download method")
                else:
                    logger.error("Message appears to be text-only or has no media")
                    logger.error(f"Message text preview: {message.text[:100] if message.text else 'N/A'}")
                
                # Check if message is forwarded and try to access original
                if message.forward_from_chat or message.forward_from:
                    logger.warning("Message is forwarded - original document may not be accessible")
                    logger.warning("Try sending the file directly (not forwarded) for best results")
                
                # Additional debugging info
                logger.error(f"Message ID: {message_id}, Chat ID used: {successful_chat_id if successful_chat_id else 'N/A'}")
                logger.error("This may happen if:")
                logger.error("1. The message was forwarded and the document isn't accessible")
                logger.error("2. The message type changed (e.g., photo instead of document)")
                logger.error("3. The user account doesn't have permission to access the document")
                logger.error("4. The message was deleted or edited")
                
                return None
            
            # Download the file
            logger.info(f"Downloading large file via Pyrogram: {message.document.file_name}")
            
            # Download to a temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                # Download the file
                file_path = await client.download_media(
                    message,
                    file_name=tmp_path,
                    progress=None  # No progress callback for now
                )
                
                # Read the file content
                if file_path and os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    os.remove(file_path)  # Clean up temp file
                    logger.info(f"Successfully downloaded {len(content)} bytes via Pyrogram")
                    return content
                else:
                    logger.error("Failed to download file via Pyrogram - file not found")
                    return None
            except Exception as download_error:
                # Clean up temp file on error
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except:
                        pass
                raise download_error
                
        except Exception as e:
            logger.error(f"Error downloading file via Pyrogram: {str(e)}")
            return None
    
    @classmethod
    async def download_document_to_path(
        cls,
        chat_id: int,
        message_id: int,
        dest_path: Optional[str] = None,
        bot_id: Optional[int] = None,
        bot_username: Optional[str] = None,
    ) -> Optional[str]:
        """
        Download a document using Pyrogram and persist it to disk.

        Args:
            chat_id: Telegram chat ID
            message_id: Telegram message ID
            dest_path: Optional explicit destination path. If not provided, a temp file is used.
            bot_id/bot_username: Helpers for private chats when using user accounts.

        Returns:
            Absolute file path if successful, None otherwise.
        """
        content = await cls.download_large_file(chat_id, message_id, bot_id, bot_username)
        if not content:
            return None

        if dest_path is None:
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            dest_path = tmp_file.name
            tmp_file.close()

        try:
            with open(dest_path, "wb") as f:
                f.write(content)
            logger.info(f"Saved large file to {dest_path}")
            return dest_path
        except Exception as e:
            logger.error(f"Failed to write downloaded file to {dest_path}: {e}")
            try:
                if os.path.exists(dest_path):
                    os.remove(dest_path)
            except Exception:
                pass
            return None
    
    @classmethod
    async def stop(cls):
        """Stop the Pyrogram client"""
        if cls._client:
            try:
                await cls._client.stop()
                logger.info("Pyrogram client stopped")
            except Exception as e:
                logger.error(f"Error stopping Pyrogram client: {str(e)}")
            finally:
                cls._client = None

