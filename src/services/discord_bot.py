import discord
from discord.ext import commands
from config.config import DISCORD_TOKEN
from agent.groq_client import GroqClient
from utils.logger import Logger
from utils.supabase import TableRegistry
from tools.static import tools
    
class DiscordBot(commands.Bot):
    def __init__(self, command_prefix:str = "!"):
        self.logger = Logger("discord_bot")
        self.logger.info("Inisialisasi DiscordBot")
        
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        super().__init__(command_prefix=command_prefix, intents=intents)
        
        # Initialize Groq client
        self.groq_client = GroqClient()
                
    async def setup_hook(self):
        """Setup hook untuk bot"""
        self.logger.info("Menjalankan setup hook")
        # Di sini Anda bisa menambahkan setup tambahan
        pass
        
    async def on_ready(self):
        """Event handler ketika bot siap"""
        self.groq_client.setupKnowledge(
            data_dir = "src/data/knowledges",
            data_type = TableRegistry.DataRegistry
        )
        self.logger.info(f'{self.user} telah terhubung ke Discord!')
        
    async def ask_command(self, ctx: commands.Context, *, question: str):
        """Command untuk bertanya ke AI"""
        try:
            self.logger.info(f"Command ask dipanggil oleh {ctx.author} dengan pertanyaan: {question}")
            system_message = "You are an sigma boy agent!"
            
            response = self.groq_client.invoke(
                query=question,
                system_message=system_message,
            )
            await ctx.send(response)
                
        except Exception as e:
            error_message = f"Maaf, terjadi kesalahan: {str(e)}"
            self.logger.error(error_message)
            self.logger.exception("Detail error:")
            await ctx.send(error_message)
                
    def run_bot(self):
        """Menjalankan bot"""
        self.logger.info("Memulai bot Discord")
        self.run(DISCORD_TOKEN) 