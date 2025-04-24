from services.discord_bot import DiscordBot
from utils.logger import Logger

def main():
    """Fungsi utama untuk menjalankan bot"""
    logger = Logger(__file__)
    logger.info("Memulai aplikasi Discord Bot")
    
    try:
        bot = DiscordBot()

        # Register commands
        @bot.command(name='ask')
        async def ask(ctx, *, question: str):
            await bot.ask_command(ctx, question=question)
        
        # Run the bot
        logger.info("Menjalankan bot Discord")
        bot.run_bot()

    except Exception as e:
        logger.error(f"Terjadi kesalahan saat menjalankan bot: {str(e)}")
        logger.exception("Detail error:")
        raise

if __name__ == "__main__":
    main() 