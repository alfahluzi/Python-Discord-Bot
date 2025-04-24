import discord
from discord.ext.commands import Context, Bot
from config.config import DISCORD_TOKEN
from agent.agent_client import AgentClient
from utils.logger import Logger
from utils.supabase import TableRegistry
    
class DiscordBot(Bot):
    def __init__(self, command_prefix:str = "!"):
        self.logger = Logger("discord_bot")
        self.logger.info("Inisialisasi DiscordBot")
        
        # Set up intents
        intents = discord.Intents.all()  # Menggunakan semua intents untuk memastikan bot dapat melihat semua yang diperlukan
        super().__init__(command_prefix=command_prefix, intents=intents)
        
        # Initialize Groq client
        self.ai_agent = AgentClient()
        
                
    async def setup_hook(self):
        """Setup hook untuk bot"""
        self.logger.info("Menjalankan setup hook")
        pass
        
    async def on_ready(self):
        """Event handler ketika bot siap"""
        # self.ai_agent.retriever.setupKnowledge(
        #     data_dir = "src/data/knowledges",
        #     data_type = TableRegistry.DataRegistry
        # )
        self.logger.info(f'{self.user} telah terhubung ke Discord!')
        self.logger.info(f'Command yang tersedia: {[cmd.name for cmd in self.commands]}')
        
    async def message(self, context: Context, prefix:str):
        """Command untuk bertanya ke AI"""
        question = context.message.content[len(prefix):]
        if question is "":
            await context.send("Mohon berikan pertanyaan setelah command !ask")
            return
            
        try:
            self.logger.info(f"Command ask dipanggil oleh {context.author} dengan pertanyaan: {question}")
            system_message = "You are an child agent!"
            await context.send(f"Session ID: {context.channel.id}")
            response = self.ai_agent.invoke(
                thread_id=str(context.channel.id),
                query=question,
                system_message=system_message,
            )
            await context.send(response.content)
                
        except Exception as e:
            error_message = f"Maaf, terjadi kesalahan: {str(e)}"
            self.logger.error(error_message)
            self.logger.exception("Detail error:")
            await context.send(error_message)
                
    def run_bot(self):
        """Menjalankan bot"""
        self.logger.info("Memulai bot Discord")
        self.run(DISCORD_TOKEN) 
        
