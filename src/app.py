from services.discord_bot import DiscordBot
from utils.logger import Logger
from discord.ext.commands import Context 

logger = Logger(__file__)


def main():
    """Fungsi utama untuk menjalankan aplikasi"""
    logger.info("Memulai aplikasi")
    
    logger.info("Load bot")
    BOT = DiscordBot()
    
    try:
        # Run the bot
        logger.info("Menjalankan bot Discord")
        BOT.run_bot()

    except Exception as e:
        logger.error(f"Terjadi kesalahan saat menjalankan bot: {str(e)}")
        logger.exception("Detail error:")
        raise

if __name__ == "__main__":
    main() 