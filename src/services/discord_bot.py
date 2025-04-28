from discord.ext.commands import Bot 
from discord.ext import commands
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

        @self.command(name='ai')
        async def __(ctx: Context):
            """Handle message from user"""
            try:
                # Process with AI agent
                response = self.ai_agent.invoke(
                    guild_id=str(ctx.guild.id),
                    thread_id=str(ctx.channel.id),
                    user_id=str(ctx.author.name),
                    query=ctx.message.content.replace(f"!ai", "")
                )
                
                # Kirim respons
                if len(response.content) > 2000:
                    await ctx.send(response.content[:2000])
                else:
                    await ctx.send(response.content)
                
            except Exception as e:
                error_message = f"Maaf, terjadi kesalahan: {str(e)}"
                self.logger.error(error_message)
                self.logger.exception("Detail error:")
                await ctx.send(error_message) 
        
        @self.command(name="ping")
        async def __(ctx):
            """Ping command to check bot responsiveness"""
            await ctx.send("Pong!")

    def run_bot(self):
        """Menjalankan bot"""
        self.logger.info("Discord Loop Event is running!")
        self.run(DISCORD_TOKEN)

    async def on_ready(self):
        self.ai_agent = AgentClient(self)        
        self.logger.info(f"Bot is ready with {len(self.ai_agent.tools)} available tools")
        
    

