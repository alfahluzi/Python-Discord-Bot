from services.discord_bot import DiscordBot
from utils.logger import Logger
from discord.ext.commands import Context 
logger = Logger(__file__)

logger.info("Load bot")
BOT = DiscordBot()

def main():
    """Fungsi utama untuk menjalankan aplikasi"""
    logger.info("Memulai aplikasi")
    
    try:
        # Register commands
        command = 'ai'
        @BOT.command(name=command)
        async def ask(ctx: Context):
            logger.debug(f"question: {ctx.message}")
            await BOT.message(ctx, command=command)
                
        # Run the bot
        logger.info("Menjalankan bot Discord")
        BOT.run_bot()

    except Exception as e:
        logger.error(f"Terjadi kesalahan saat menjalankan bot: {str(e)}")
        logger.exception("Detail error:")
        raise

if __name__ == "__main__":
    main() 