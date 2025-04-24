from services.discord_bot import DiscordBot
from utils.logger import Logger
from discord.ext.commands import Context 

def main():
    """Fungsi utama untuk menjalankan bot"""
    logger = Logger(__file__)
    logger.info("Memulai aplikasi Discord Bot")
    
    try:
        bot = DiscordBot()
        prefix = 'ai'
        # Register commands
        @bot.command(name=prefix)
        async def ask(ctx: Context):
            logger.debug(f"question: {ctx.message}")
            await bot.message(ctx, prefix=prefix)
        
        # Run the bot
        logger.info("Menjalankan bot Discord")
        bot.run_bot()

    except Exception as e:
        logger.error(f"Terjadi kesalahan saat menjalankan bot: {str(e)}")
        logger.exception("Detail error:")
        raise

if __name__ == "__main__":
    main() 