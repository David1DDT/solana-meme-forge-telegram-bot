"""Main file for launching bots - main + support."""
import asyncio, logging, os, sys
from bot import bot, dp
from support_bot import support_bot, support_dp, startup_support_bot
from settings import DEBUG_MODE, SOLANA_NETWORK

os.environ['DEBUG_MODE'] = str(DEBUG_MODE).lower()
os.environ['SOLANA_NETWORK'] = SOLANA_NETWORK

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

for path in [current_dir, parent_dir]:
    if path not in sys.path:
        sys.path.append(path)

logger.info(f"Operating mode: {'TEST' if DEBUG_MODE else 'PRODUCTION'}")
logger.info(f"Solana network: {SOLANA_NETWORK}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Script directory: {current_dir}")

for file in ['config.js', 'token-info.json']:
    for base in [os.getcwd(), current_dir, parent_dir,
                 os.path.join(current_dir, 'scripts'),
                 os.path.join(parent_dir, 'scripts')]:
        path = os.path.join(base, file)
        if os.path.exists(path):
            logger.info(f"File {file} found: {path}")
            break
    else:
        logger.warning(f"File {file} not found")


async def main():
    try:
        try:
            bot_info = await bot.get_me()
            logger.info(f"Main bot active: @{bot_info.username}")
        except Exception as e:
            logger.error(f"Main bot token validation failed: {e}")
            return

        try:
            webhook_info = await bot.get_webhook_info()
            if webhook_info.url:
                logger.warning(f"Main bot has webhook: {webhook_info.url}. Removing...")
                await bot.delete_webhook()
                logger.info("Main bot webhook removed")
        except Exception as e:
            logger.error(f"Error removing main bot webhook: {e}")

        try:
            support_info = await support_bot.get_me()
            logger.info(f"Support bot active: @{support_info.username}")

            support_webhook_info = await support_bot.get_webhook_info()
            if support_webhook_info.url:
                logger.warning(f"Support bot has webhook: {support_webhook_info.url}. Removing...")
                await support_bot.delete_webhook()
                logger.info("Support bot webhook removed")

            support_bot_valid = True
        except Exception as e:
            logger.error(f"Support bot token validation failed: {e}")
            support_bot_valid = False

        if support_bot_valid:
            await startup_support_bot()
            logger.info("Support bot initialized")
        else:
            logger.warning("Support bot disabled due to invalid token")

        await asyncio.sleep(2)
        logger.info("Starting polling...")

        tasks = [asyncio.create_task(dp.start_polling(bot))]

        if support_bot_valid:
            tasks.append(asyncio.create_task(support_dp.start_polling(support_bot)))
            logger.info("Both bots started")
        else:
            logger.info("Only main bot started")

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        for task in pending:
            task.cancel()

        for task in done:
            try:
                await task
            except Exception as e:
                logger.error(f"Bot finished with error: {e}")

    except Exception as e:
        logger.critical(f"Critical error starting bots: {e}")
        raise
    finally:
        try:
            from utils.payment_checker import close_session
            await close_session()
            logger.info("Payment checker session closed")
        except Exception as e:
            logger.error(f"Error closing payment session: {e}")

        try:
            await bot.session.close()
            logger.info("Main bot session closed")
        except Exception as e:
            logger.error(f"Error closing main bot session: {e}")

        try:
            await support_bot.session.close()
            logger.info("Support bot session closed")
        except Exception as e:
            logger.error(f"Error closing support bot session: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bots stopped")
    except Exception as e:
        logger.critical(f"Unhandled error: {e}")