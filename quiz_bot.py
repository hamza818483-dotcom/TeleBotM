from telegram.ext import Application
from telegram.request import HTTPXRequest
from dotenv import load_dotenv
import os
import logging
import sys
import traceback
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Set up detailed logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Disable HTTP request logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# Load environment variables first
load_dotenv()

class QuizBot:
    def __init__(self):
        from utils.system_logger import log_event
        from services.settings_service import settings_service
        logger.info("Initializing QuizBot...")
        log_event("INFO", "Initializing QuizBot")
        
        # Validate environment variables
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            log_event("ERROR", "BOT_TOKEN not found in .env file")
            raise ValueError("BOT_TOKEN not found in .env file")
        
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not gemini_api_key:
            log_event("ERROR", "GEMINI_API_KEY not found in .env file")
            raise ValueError("GEMINI_API_KEY not found in .env file")
        logger.info("API key validation successful")
        log_event("INFO", "API key validation successful")
            
        auth_users = os.getenv('AUTHORIZED_USERS')
        if not auth_users:
            logger.warning("AUTHORIZED_USERS not configured in .env file")
        else:
            logger.info(f"Authorized users configured: {auth_users}")
        
        # Initialize settings (seed from env on first run)
        try:
            settings_service.seed_from_env_if_empty()
            cfg_summary = {
                'quiz_marker': settings_service.get_quiz_marker(),
                'explanation_mode': settings_service.get_explanation_mode(),
                'channels': len(settings_service.list_channels()),
                'groups': len(settings_service.list_groups()),
                'authorized_users': len(settings_service.list_authorized_users()),
            }
            logger.info(f"Settings initialized: {cfg_summary}")
            log_event("INFO", f"Settings initialized: {cfg_summary}")
        except Exception as e:
            logger.warning(f"Settings initialization warning: {e}")
            log_event("ERROR", f"Settings initialization warning: {e}", error=e)

        # Create thread pool executor for CPU-intensive tasks
        # Increased workers for better concurrent processing
        max_workers = int(os.getenv('THREAD_POOL_WORKERS', '20'))
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="quiz_worker")
        
        # Initialize the application with optimized settings for multiple users
        try:
            logger.info("Building Telegram application with optimized settings...")
            
            # Create HTTPX request with connection pooling and timeouts
            # Increased connection pool for better concurrent request handling
            connection_pool_size = int(os.getenv('CONNECTION_POOL_SIZE', '100'))
            request = HTTPXRequest(
                connection_pool_size=connection_pool_size,  # Increased for multiple users
                read_timeout=60,          # Increased read timeout for large files
                write_timeout=60,         # Increased write timeout
                connect_timeout=15,       # Connection timeout
                pool_timeout=20,          # Increased pool timeout for high concurrency
            )
            
            self.application = Application.builder().token(bot_token).request(request).build()
            
            logger.info("Telegram application built successfully with optimized settings")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram application: {str(e)}")
            raise

    def setup_handlers(self):
        """Set up all message handlers"""
        try:
            from utils.system_logger import log_event
            logger.info("Setting up message handlers...")
            log_event("INFO", "Setting up message handlers")
            from bot.handlers import setup_handlers
            setup_handlers(self.application)
            
            # Add post-init callback to start session cleanup task
            original_post_init = getattr(self.application, 'post_init', None)
            
            async def post_init(app):
                from services.session_manager import session_manager
                session_manager.start_cleanup_task()
                if original_post_init:
                    await original_post_init(app)
            
            self.application.post_init = post_init
            
            logger.info("Handlers are set up successfully!")
            log_event("INFO", "Handlers set up successfully")
        except Exception as e:
            logger.error(f"Failed to set up handlers: {str(e)}")
            log_event("ERROR", f"Failed to set up handlers: {str(e)}", error=e)
            traceback.print_exc()
            raise

    def run(self):
        """Start the bot"""
        try:
            logger.info("Starting bot setup...")
            self.setup_handlers()
            logger.info("QuizGen Bot is running! Press Ctrl+C to stop.")
            
            # Set up error handler
            self.application.add_error_handler(self.error_handler)
            
            # Run the bot with polling and optimized settings
            self.application.run_polling(
                allowed_updates=["message", "callback_query", "poll_answer"],
                drop_pending_updates=True,  # Drop pending updates on startup
            )
        except Exception as e:
            logger.error(f"Error running bot: {str(e)}")
            traceback.print_exc()
            raise
        finally:
            # Cleanup resources
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        try:
            logger.info("Cleaning up resources...")
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=True)
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def error_handler(self, update, context):
        """Handle errors in the telegram updates"""
        from utils.system_logger import log_event
        error_msg = f"Update {update} caused error: {context.error}"
        logger.error(error_msg)
        log_event("ERROR", error_msg, error=context.error)
        traceback.print_exc()
