from hashlib import sha256
import datetime
import re
from typing import Dict
from interactions import Button, ButtonStyle, Embed, EmbedField, Extension, Color
import interactions

from database import RedisDB

class SyncBlacklistsExtension(Extension):
    WHITELIST_KEY = "whitelisted_users"
    FORCE_OVERRIDE_USER_ID = "708812851229229208"
    BLACKLIST_CHANNEL_PATTERN = re.compile(r'.*blacklist*.', re.IGNORECASE)
    
    def __init__(self, bot):
        self.bot = bot
        self.db = RedisDB(db=0)
        self.db_whitelist = RedisDB(db=1)
        self.db_servers = RedisDB(db=2)
        
    async def is_user_whitelisted(self, user_id):
        if str(user_id) == self.FORCE_OVERRIDE_USER_ID: return True
        return self.db_whitelist.redis.sismember(self.WHITELIST_KEY, str(user_id))
    
    @interactions.slash_command(
        name="sync_blacklists",
        description="Syncs the bot's blacklists to the channel and server.",
    )
    async def sync_blacklists(self, ctx: interactions.SlashContext):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not whitelisted!", ephemeral=True)
            return
        
        await ctx.defer(ephemeral=True)
        msg = await ctx.send("Syncing blacklists...")

        keys_values = self.db.list_all_users_info()
        if not keys_values:
            await ctx.send("There are no blacklisted users.", ephemeral=True)
            return

        current_sync_hash = sha256(str(keys_values).encode('utf-8')).hexdigest()
        print(f"current_sync_hash: {current_sync_hash}")

        guild = ctx.guild
        if not guild:
            await ctx.send("This command cannot be used in DMs.", ephemeral=True)
            return

        if not guild.me.guild_permissions.BAN_MEMBERS:
            await ctx.send("I do not have permission to ban members in this server.", ephemeral=True)
            return

        if self.db_servers.check_if_guild_synced(str(guild.id), current_sync_hash):
            sync_details = self.db_servers.get_sync_details(str(guild.id))
            users_synced = sync_details.get("count", 'N/A')
            channel_id = sync_details.get("channel_id", 'N/A')
            await ctx.send(f"Blacklist in this guild is already up to date. Channel ID: {channel_id}, Users Synced: {users_synced}", ephemeral=True)
            return

        guild_synced_count = 0

        for user_id in keys_values.keys():
            try:
                await guild.ban(user_id, reason="Blacklisted by the bot.")
                guild_synced_count += 1
            except Exception as e:
                print(f"Error banning user {user_id} in guild {guild.id}: {e}")

        blacklist_channels = [channel for channel in guild.channels if self.BLACKLIST_CHANNEL_PATTERN.match(channel.name) or channel.name in ["blacklist", "blacklists"]]
        if not blacklist_channels:
            print(f"Blacklist channel not found in guild {guild.id}.")
            await ctx.send(f"Blacklist channel not found in this guild.", ephemeral=True)
            return
        print(blacklist_channels)

        for user_id, user_info in keys_values.items():
            embed = Embed(
                title=f"{user_info.get('username', 'N/A')} has been blacklisted!",
                description=f"Here's some detailed information about the blacklist:",
                color=Color.random(),
                fields=[
                    EmbedField(name="User ID", value=f"`{user_id}`", inline=True),
                    EmbedField(name="📜 Reason", value=f"*{user_info.get('reason', 'N/A')}*", inline=False),
                    EmbedField(name="🔗 Proof Link", value=f"[Click Here]({user_info.get('proof_link', 'N/A')})", inline=False),
                    EmbedField(name="Folder ID", value=f"`{user_info.get('folder_id', 'N/A')}`", inline=True),
                ],
                footer=f"Blacklist synced by {ctx.author.display_name}",
                timestamp=datetime.datetime.now().isoformat(),
            )
            view_images_link_button = Button(
                style=ButtonStyle.LINK,
                label="View Images",
                url=user_info.get('proof_link', 'N/A'),
            )
            view_images_direct_button = Button(
                style=ButtonStyle.PRIMARY,
                label="View Images Directly",
                custom_id="view_images_direct",
            )
            action_row = interactions.ActionRow(view_images_link_button, view_images_direct_button)
            for blacklist_channel in blacklist_channels:
                await blacklist_channel.send(embed=embed, components=[action_row], ephemeral=True)
        
        if blacklist_channels:
            first_blacklist_channel_id = blacklist_channels[0].id
            self.db_servers.set_last_sync_details(str(guild.id), current_sync_hash)
            self.db_servers.record_sync_details(str(guild.id), first_blacklist_channel_id, str(len(keys_values)))

        await ctx.send(f"Synced {guild_synced_count} blacklisted users in this guild. Channel ID: {blacklist_channel.id}", ephemeral=True)
        await ctx.edit(content="Syncing blacklists completed.", message=msg)

    async def try_ban(self,guild,user_id):
        try:
            await guild.ban(user_id, reason="Blacklisted by the bot.")
            return True
        except (interactions.errors.Forbidden, interactions.errors.HTTPException, Exception) as e:
            print(f"Error banning user {user_id} in guild {guild.id}: {e}")
            return False
    
    @interactions.slash_command(name="syncbans", description="Syncs the bot's blacklists to the channel and server.")
    async def syncbans(self, ctx: interactions.SlashContext):
        if not await self.is_user_whitelisted(ctx.author.id):
            return await ctx.send("You are not whitelisted!", ephemeral=True)
        await ctx.defer(ephemeral=True)
        keys_values: Dict[str, Dict[str, str]] = self.db.list_all_users_info()
        if not keys_values: return await ctx.send("There are no blacklisted users.", ephemeral=True)
        guild = ctx.guild
        if not guild: return await ctx.send("This command cannot be used in DMs.", ephemeral=True)
        if not guild.me.guild_permissions.BAN_MEMBERS: return await ctx.send("I do not have permission to ban members in this server.", ephemeral=True)
        current_sync_hash: str = sha256(str(keys_values).encode('utf-8')).hexdigest()
        print(f"current_sync_hash: {current_sync_hash}")
        if self.db_servers.check_if_guild_synced(str(guild.id), current_sync_hash):
            sync_details: Dict[str, str] = self.db_servers.get_sync_details(str(guild.id))
            print(f"sync_details: {sync_details}")
            return await ctx.send(f"Blacklist in this guild is already up to date. Channel ID: {sync_details.get('channel_id', 'N/A')}, Users Synced: {sync_details.get('count', 'N/A')}", ephemeral=True)
        guild_synced_count: int = 0
        for user_id in keys_values.keys():
            if not await self.is_user_whitelisted(user_id):
                if await self.try_ban(guild, user_id): guild_synced_count += 1
        await ctx.send(f"Synced {guild_synced_count} blacklisted users in this guild.", ephemeral=True)
    
    @interactions.slash_command(name="purge", description="purges all embeds and messages in channel")
    async def purge(self, ctx: interactions.SlashContext):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not whitelisted!", ephemeral=True)
            return
        try:
            await ctx.channel.purge()
            await ctx.send("Purged all messages and embeds in this channel.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"Error purging channel: {e}", ephemeral=True)
    
    """
    @interactions.slash_command(
        name="sync_blacklists",
        description="Syncs the bot's blacklists to the channel and server.",
    )
    async def sync_blacklists(self, ctx: interactions.SlashContext):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not whitelisted!", ephemeral=True)
            return
        
        msg = await ctx.send("Syncing blacklists...", ephemeral=True)
        
        keys_values = self.db.list_all_users_info()
        if not keys_values:
            await ctx.send("There are no blacklisted users.", ephemeral=True)
            return
        
        current_sync_hash = sha256(str(keys_values).encode('utf-8')).hexdigest()
        print(f"current_sync_hash: {current_sync_hash}")
        total_users = len(keys_values)
        synced_count = 0
        synced_details = {}
        users_attempted_sync = set()
        
        for guild in self.bot.guilds:
            if not guild.me.guild_permissions.BAN_MEMBERS: continue
            
            if self.db_servers.check_if_guild_synced(str(guild.id), current_sync_hash):
                await ctx.send(f"Blacklist in guild {guild.id} is already up to date.", ephemeral=True)
                sync_details = self.db_servers.get_sync_details(str(guild.id))
                users_synced = sync_details.get("count", 'N/A')
                channel_id = sync_details.get("channel_id", 'N/A')
                synced_details[guild.id] = {"channel_id": channel_id, "count": users_synced}
                continue
            
            guild_synced_count = 0
            
            for user_id in keys_values.keys():
                try:
                    await guild.ban(user_id, reason="Blacklisted by the bot.")
                    users_attempted_sync.add(user_id)
                    guild_synced_count += 1
                except Exception as e:
                    await ctx.send(f"Error banning user {user_id} in guild {guild.id}: {e}", ephemeral=True)
            
            synced_count += guild_synced_count
            
            blacklist_channel = next((channel for channel in guild.channels if self.BLACKLIST_CHANNEL_PATTERN.match(channel.name)), None)
            if not blacklist_channel:
                print(f"Blacklist channel not found in guild {guild.id}.")
                await ctx.send(f"Blacklist channel not found in guild {guild.id}.", ephemeral=True)
                continue
            print(blacklist_channel)
            for user_id, user_info in keys_values.items():
                embed = Embed(
                    title=f"{user_info.get('username', 'N/A')} has been blacklisted!",
                    description=f"Here's some detailed information about the blacklist:",
                    color=Color.random(),
                    fields=[
                        EmbedField(name="User ID", value=f"`{user_id}`", inline=True),
                        EmbedField(name="📜 Reason", value=f"*{user_info.get('reason', 'N/A')}*", inline=False),
                        EmbedField(name="🔗 Proof Link", value=f"[Click Here]({user_info.get('proof_link', 'N/A')})", inline=False),
                        EmbedField(name="Folder ID", value=f"`{user_info.get('folder_id', 'N/A')}`", inline=True),
                    ],
                    footer=f"Blacklist synced by {ctx.author.display_name}",
                    timestamp=datetime.datetime.now().isoformat(),
                )
                view_images_link_button = Button(
                    style=ButtonStyle.LINK,
                    label="View Images",
                    # TODO: Replace it with a f"url/{user_info.get('folder_id', 'N/A')}" link.
                    url=user_info.get('proof_link', 'N/A'),
                )
                view_images_direct_button = Button(
                    style=ButtonStyle.PRIMARY,
                    label="View Images Directly",
                    custom_id="view_images_direct",
                )
                action_row = interactions.ActionRow(view_images_link_button, view_images_direct_button)
                await blacklist_channel.send(embed=embed, components=[action_row])
                
            self.db_servers.set_last_sync_details(str(guild.id), current_sync_hash)
            self.db_servers.record_sync_details(str(guild.id), blacklist_channel.id, str(guild_synced_count))
            synced_details[guild.id] = {"channel_id": blacklist_channel.id, "count": str(guild_synced_count)}
        
        total_unique_users = len(users_attempted_sync)
        summary = "\n".join([
            f"Guild ID: {gid}, Channel ID: {details['channel_id']}, Users Synced: {details['count']}"
            for gid, details in synced_details.items()
        ])
        summary += f"\nTotal unique users synced: {total_unique_users}"
        await ctx.send(f"Sync summary:\n{summary}", ephemeral=True)
        await ctx.edit(content=f"Synced {synced_count}/{total_users} blacklisted users.", message=msg)
    """