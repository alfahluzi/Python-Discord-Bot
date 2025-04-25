from discord.ext.commands import Bot 
import discord
from config.config import DISCORD_TOKEN
from utils.logger import Logger
from agent.agent_client import AgentClient
from discord.ext.commands import Context
class DiscordBot(Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.logger = Logger(__file__)
        self.logger.info("Inisialisasi DiscordBot")
        self.ai_agent = AgentClient()

    async def message(self, ctx: Context, command=None):
        """Handle message from user"""
        try:
            # Process with AI agent
            response = self.ai_agent.invoke(
                guild_id=str(ctx.guild.id),
                thread_id=str(ctx.channel.id),
                user_id=str(ctx.author.id),
                query=ctx.message.content.replace(f"!{command}", "")
            )
            
            # Send response
            await ctx.send(response.content)
            
        except Exception as e:
            error_message = f"Maaf, terjadi kesalahan: {str(e)}"
            self.logger.error(error_message)
            self.logger.exception("Detail error:")
            await ctx.send(error_message)
                
    def run_bot(self):
        """Menjalankan bot"""
        self.logger.info("Memulai bot Discord")
        self.run(DISCORD_TOKEN) 
        
