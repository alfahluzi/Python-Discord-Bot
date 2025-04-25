from services.discord_bot import DiscordBot
from utils.logger import Logger
from discord.ext.commands import Context 
import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os

class CodeChangeHandler(FileSystemEventHandler):
    def __init__(self, bot):
        self.bot = bot
        self.last_modified = time.time()
        
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            current_time = time.time()
            if current_time - self.last_modified > 1:  # Prevent multiple reloads
                self.last_modified = current_time
                print("\nPerubahan kode terdeteksi! Memulai ulang bot...")
                self.bot.close()
                os.execv(sys.executable, ['python'] + sys.argv)

def main():
    """Fungsi utama untuk menjalankan bot"""
    logger = Logger(__file__)
    logger.info("Memulai aplikasi Discord Bot")
    
    try:
        bot = DiscordBot()
        command = 'ai'
        # Register commands
        @bot.command(name=command)
        async def ask(ctx: Context):
            logger.debug(f"question: {ctx.message}")
            await bot.message(ctx, command=command)
        
        # Setup file watcher
        event_handler = CodeChangeHandler(bot)
        observer = Observer()
        observer.schedule(event_handler, path='src', recursive=True)
        observer.start()
        
        # Run the bot
        logger.info("Menjalankan bot Discord dengan hot-reload aktif")
        bot.run_bot()

    except Exception as e:
        logger.error(f"Terjadi kesalahan saat menjalankan bot: {str(e)}")
        logger.exception("Detail error:")
        raise

if __name__ == "__main__":
    main() 