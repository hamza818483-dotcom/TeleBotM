from bot.quiz_bot import QuizBot
from utils.system_logger import set_bot_start_time, log_event
import time
import logging
import sys
import signal
import asyncio

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("quizgen_bot")

# Disable httpx and telegram request logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

def main():
    max_retries = 3
    retry_count = 0
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    while retry_count < max_retries:
        try:
            logger.info("Starting QuizGen Bot with multi-user optimizations...")
            set_bot_start_time()  # Track bot start time
            log_event("INFO", "Bot starting up")
            bot = QuizBot()
            log_event("INFO", "Bot initialized successfully")
            bot.run()
        except KeyboardInterrupt:
            logger.info("Bot stopped manually by user")
            log_event("INFO", "Bot stopped manually by user")
            break
        except Exception as e:
            retry_count += 1
            logger.error(f"Error in bot: {str(e)}")
            log_event("ERROR", f"Bot error: {str(e)}", error=e)
            
            if retry_count < max_retries:
                wait_time = 10 * retry_count  # Increase wait time with each retry
                logger.info(f"Restarting in {wait_time} seconds... (Attempt {retry_count}/{max_retries})")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to restart after {max_retries} attempts. Please check your API keys and configuration.")
                break

if __name__ == '__main__':
    main()