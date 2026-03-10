import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import datetime
import json
from typing import Optional
from keep_alive import keep_alive

PREFIX = "!"
bot = commands.Bot(command_prefix=PREFIX, intents=discord.Intents.all())

reaction_log_settings = {}
REACTION_LOGS_FILE = "reaction_logs_settings.json"

def save_reaction_log_settings():
    with open(REACTION_LOGS_FILE, 'w') as f:
        json.dump({str(k): v for k, v in reaction_log_settings.items()}, f)

def load_reaction_log_settings():
    global reaction_log_settings
    try:
        if os.path.exists(REACTION_LOGS_FILE):
            with open(REACTION_LOGS_FILE, 'r') as f:
                data = json.load(f)
                reaction_log_settings = {int(k): v for k, v in data.items()}
    except Exception as e:
        print(f"Error loading reaction log settings: {e}")

@bot.tree.command(name="osay", description="Owner-only anonymous say")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.describe(
    message="The message you want the bot to say",
    channel_id="Channel ID to send to (optional)"
)
async def osay(interaction: discord.Interaction, message: str, channel_id: Optional[str] = None):
    if interaction.user.id != 888402430335799338:
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    if interaction.guild is None:
        if channel_id:
            try:
                target_channel = bot.get_channel(int(channel_id))
                if not target_channel:
                    await interaction.response.send_message(f"❌ Could not find channel with ID: {channel_id}", ephemeral=True)
                    return
                
                await target_channel.send(message)
                await interaction.response.send_message(f"✅ Anonymous message sent to {target_channel.mention} in {target_channel.guild.name}!", ephemeral=True)
            except ValueError:
                await interaction.response.send_message("❌ Invalid channel ID. Please provide a valid number.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Failed to send message: {str(e)}", ephemeral=True)
        else:
            await interaction.response.send_message(message)
            await interaction.channel.send(message)
    else:
        try:
            if channel_id:
                target_channel = bot.get_channel(int(channel_id))
                if not target_channel:
                    await interaction.response.send_message(f"❌ Could not find channel with ID: {channel_id}", ephemeral=True)
                    return
            else:
                target_channel = interaction.channel
            
            await target_channel.send(message)
            await interaction.response.send_message(f"✅ Anonymous message sent to {target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to send message: {str(e)}", ephemeral=True)

@bot.tree.command(name="category-delete", description="Delete a category and all its channels")
@app_commands.describe(category="The category to delete")
async def category_delete(interaction: discord.Interaction, category: discord.CategoryChannel):
    if interaction.user.id != 888402430335799338:
        await interaction.response.send_message("❌ Owner only.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    
    channels_deleted = 0
    try:
        for channel in category.channels:
            await channel.delete(reason=f"Category delete command by {interaction.user}")
            channels_deleted += 1
            await asyncio.sleep(0.1)
        
        category_name = category.name
        await category.delete(reason=f"Category delete command by {interaction.user}")
        
        await interaction.followup.send(f"✅ Successfully deleted category **{category_name}** and its {channels_deleted} channels.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error deleting category: {str(e)}")

@bot.tree.command(name="category-perm", description="Add permissions for a role to all channels in a category")
@app_commands.describe(
    category="The category to update",
    role="The role to give permissions to",
    view_channel="Allow viewing channels",
    send_messages="Allow sending messages",
    connect="Allow connecting to voice",
    manage_channels="Allow managing channels"
)
@app_commands.choices(
    view_channel=[app_commands.Choice(name="Allow", value="allow"), app_commands.Choice(name="Deny", value="deny"), app_commands.Choice(name="Neutral", value="neutral")],
    send_messages=[app_commands.Choice(name="Allow", value="allow"), app_commands.Choice(name="Deny", value="deny"), app_commands.Choice(name="Neutral", value="neutral")],
    connect=[app_commands.Choice(name="Allow", value="allow"), app_commands.Choice(name="Deny", value="deny"), app_commands.Choice(name="Neutral", value="neutral")],
    manage_channels=[app_commands.Choice(name="Allow", value="allow"), app_commands.Choice(name="Deny", value="deny"), app_commands.Choice(name="Neutral", value="neutral")]
)
async def category_perm(
    interaction: discord.Interaction,
    category: discord.CategoryChannel,
    role: discord.Role,
    view_channel: Optional[str] = "neutral",
    send_messages: Optional[str] = "neutral",
    connect: Optional[str] = "neutral",
    manage_channels: Optional[str] = "neutral"
):
    if interaction.user.id != 888402430335799338:
        await interaction.response.send_message("❌ Owner only.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    def get_perm_value(val):
        if val == "allow": return True
        if val == "deny": return False
        return None

    overwrites = {
        'view_channel': get_perm_value(view_channel),
        'send_messages': get_perm_value(send_messages),
        'connect': get_perm_value(connect),
        'manage_channels': get_perm_value(manage_channels)
    }
    
    perms = discord.PermissionOverwrite(**{k: v for k, v in overwrites.items() if v is not None})

    success_count = 0
    try:
        await category.set_permissions(role, overwrite=perms, reason=f"Category-perm by {interaction.user}")
        
        for channel in category.channels:
            await channel.set_permissions(role, overwrite=perms, reason=f"Category-perm by {interaction.user}")
            success_count += 1
            await asyncio.sleep(0.1)

        await interaction.followup.send(f"✅ Successfully updated permissions for {role.mention} in category **{category.name}** and {success_count} channels.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error updating permissions: {str(e)}")

@bot.tree.command(name="reaction-logs-setup", description="Set the channel for reaction removal logs")
@app_commands.describe(channel="The channel to send reaction logs to")
async def reaction_logs_setup(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator and interaction.user.id != 888402430335799338:
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return
    
    guild_id = interaction.guild.id
    reaction_log_settings[guild_id] = {'channel_id': channel.id, 'enabled': True}
    
    save_reaction_log_settings()
    await interaction.response.send_message(f"✅ Reaction removal logs will be sent to {channel.mention} and are now **enabled**.", ephemeral=True)

@bot.tree.command(name="reaction-logs-toggle", description="Enable or disable reaction removal logs")
@app_commands.describe(status="Enable or disable")
@app_commands.choices(status=[
    app_commands.Choice(name="Enable", value="enable"),
    app_commands.Choice(name="Disable", value="disable")
])
async def reaction_logs_toggle(interaction: discord.Interaction, status: str):
    if not interaction.user.guild_permissions.administrator and interaction.user.id != 888402430335799338:
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return
    
    guild_id = interaction.guild.id
    if guild_id not in reaction_log_settings:
        await interaction.response.send_message("❌ Please set a log channel first using `/reaction-logs-setup`.", ephemeral=True)
        return
    
    enabled = status == "enable"
    reaction_log_settings[guild_id]['enabled'] = enabled
    save_reaction_log_settings()
    
    state = "enabled" if enabled else "disabled"
    await interaction.response.send_message(f"✅ Reaction removal logs are now **{state}**.", ephemeral=True)

@bot.event
async def on_raw_reaction_remove(payload):
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
        
    settings = reaction_log_settings.get(guild.id)
    if not settings or not settings.get('enabled') or not settings.get('channel_id'):
        return
        
    log_channel = guild.get_channel(settings['channel_id'])
    if not log_channel:
        return

    remover = bot.get_user(payload.user_id)
    remover_display = f"{remover.mention} ({remover.name})" if remover else f"User ID: {payload.user_id}"
    
    channel = guild.get_channel(payload.channel_id)
    channel_display = channel.mention if channel else f"Channel ID: {payload.channel_id}"
    
    message_link = f"https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id}"
    reaction_owner = "Unknown"
    
    try:
        msg_channel = guild.get_channel(payload.channel_id)
        if msg_channel:
            message = await msg_channel.fetch_message(payload.message_id)
            for reaction in message.reactions:
                if str(reaction.emoji) == str(payload.emoji):
                    async for user in reaction.users():
                        if user.id != payload.user_id:
                            reaction_owner = f"{user.mention} ({user.name})"
                            break
                    break
    except Exception:
        try:
            if guild.me.guild_permissions.view_audit_log:
                async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.message_update):
                    if entry.target.id == payload.message_id:
                        reaction_owner = f"{entry.user.mention} ({entry.user.name})"
                        break
        except Exception:
            pass
    
    embed = discord.Embed(
        title="🚫 Reaction Removed",
        description=f"**Removed by:** {remover_display}\n**Reaction owner:** {reaction_owner}\n**Channel:** {channel_display}\n**Emoji:** {payload.emoji}\n**Message:** [Jump to Message]({message_link})",
        color=discord.Color.orange(),
        timestamp=datetime.datetime.now()
    )
    
    try:
        await log_channel.send(embed=embed)
    except Exception:
        pass

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print(f"✅ Bot ID: {bot.user.id}")
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
        for cmd in synced:
            print(f"Registered command: /{cmd.name}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    load_reaction_log_settings()

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables!")
        exit(1)
    keep_alive()
    bot.run(TOKEN)
