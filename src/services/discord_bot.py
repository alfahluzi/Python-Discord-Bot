from discord.ext.commands import Bot 
from discord.ext import commands
import discord
from config.config import DISCORD_TOKEN
from utils.logger import Logger
from agent.agent_client import AgentClient
from discord.ext.commands import Context
from discord import Interaction, app_commands
from utils.supabase import supabase_client
from datetime import datetime
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
                response = await self.ai_agent.invoke(
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

        @self.tree.command(name="ai_message")
        @app_commands.describe(message="Message")
        async def __(interaction: Interaction, message:str):
            """Handle message from user"""
            try:
                await interaction.response.defer()

                # Process with AI agent
                response = await self.ai_agent.invoke(
                    guild_id=str(interaction.guild.id),
                    thread_id=str(interaction.channel.id),
                    user_id=str(interaction.user.id),
                    query=message
                )
                
                # Kirim respons
                if len(response.content) > 2000:
                    await interaction.followup.send(response.content[:2000])
                else:
                    await interaction.followup.send(response.content)
                
            except Exception as e:
                error_message = f"Maaf, terjadi kesalahan: {str(e)}"
                self.logger.error(error_message)
                self.logger.exception("Detail error:")
                await interaction.followup.send(error_message) 

        @self.tree.command(name="setup_ids")
        @app_commands.describe(
            issue_category_id = "Issue category id",
        )
        async def __(interaction: Interaction, issue_category_id:str):
            try:
                await interaction.response.defer()

                guild_id = interaction.guild.id
                old_data = None
                response_get_data = supabase_client.table("discord_settings").select("*").eq("guild_id", guild_id).execute()
                if response_get_data.data:
                    await interaction.followup.send(f"Previous response: {response_get_data.data}")
                    old_data = response_get_data.data[0]

                data_payload = {
                    "issue_category_id": issue_category_id if issue_category_id != "" else old_data["data"]["issue_category_id"] or None ,
                }
                payload = {
                    "guild_id": guild_id,
                    "data": data_payload,
                    "update_at": datetime.now().isoformat() if response_get_data.data else None
                }
                if response_get_data.data:
                    response_create_data = supabase_client.table("discord_settings").update(payload).eq("guild_id", guild_id).execute()
                else:
                    response_create_data = supabase_client.table("discord_settings").insert(payload).execute()

                await interaction.followup.send(f"Success save data with result: {response_create_data.data or "Success"}")
            except Exception as e:
                await interaction.followup.send(f"Maaf, terjadi kesalahan saat mengatur ID kategori masalah:\n{e}")
                self.logger.error(f"Terjadi kesalahan saat mengatur ID kategori masalah: {str(e)}")
                self.logger.exception("Detail error:")


    def run_bot(self):
        """Menjalankan bot"""
        self.logger.info("Discord Loop Event is running!")
        self.run(DISCORD_TOKEN)
    
    async def on_ready(self):
        self.ai_agent = AgentClient(self, temperature=0.1)
        try:
            synced = await self.tree.sync()
            self.logger.info(f"Synced {len(synced)} commands")
        except Exception as e:
            self.logger.info(f"Error syncing commands: {e}")
        self.logger.info(f"Bot is ready with {len(self.ai_agent.tools)} available tools")
        
    

