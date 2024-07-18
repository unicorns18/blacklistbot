import asyncio
from hashlib import sha256
import os
import re
import tempfile
from aiohttp import ClientSession
import aiohttp
from interactions import Extension, OptionType, SlashContext, Embed, EmbedField, EmbedFooter, Color
from interactions.ext.paginators import Paginator
from database import RedisDB

import datetime, interactions

from drive import Drive


class BlacklistExtension(Extension):
    WHITELIST_KEY = "whitelisted_users"
    FORCE_OVERRIDE_USER_ID = "708812851229229208"
    BLACKLIST_CHANNEL_PATTERN = re.compile(r".*blacklist*.", re.IGNORECASE)
    
    def __init__(self, bot):
        self.bot = bot
        self.drive = Drive()
        self.db_blacklist = RedisDB(db=0)
        self.db_whitelist = RedisDB(db=1)
        self.db_servers = RedisDB(db=2)
        
    async def is_user_whitelisted(self, user_id):
        if str(user_id) == self.FORCE_OVERRIDE_USER_ID: return True
        return self.db_whitelist.redis.sismember(self.WHITELIST_KEY, str(user_id))
        
    @interactions.slash_command(name="whitelist", description="Whitelist a user")
    @interactions.slash_option(
        name="user",
        description="The user to whitelist",
        required=True,
        opt_type=OptionType.USER
    )
    async def whitelist_user(self, ctx: SlashContext, user: OptionType.USER):
        if str(ctx.author.id) != self.FORCE_OVERRIDE_USER_ID:
            await ctx.send("You are not authorized to modify the whitelist.", ephemeral=True)
            return
        self.db_whitelist.redis.sadd(self.WHITELIST_KEY, str(user.id))
        await ctx.send(f"User <@{user.id}> has been added to the whitelist.", ephemeral=True)

    @interactions.slash_command(name="unwhitelist", description="Unwhitelist a user")
    @interactions.slash_option(
        name="user",
        description="The user to unwhitelist",
        required=True,
        opt_type=OptionType.USER
    )
    async def unwhitelist_user(self, ctx: SlashContext, user: OptionType.USER):
        if str(ctx.author.id) != self.FORCE_OVERRIDE_USER_ID:
            await ctx.send("You are not authorized to modify the whitelist.", ephemeral=True)
            return
        
        if not self.db_whitelist.redis.sismember(self.WHITELIST_KEY, str(user.id)):
            await ctx.send(f"User <@{user.id}> is not whitelisted.", ephemeral=True)
        else:
            self.db_whitelist.redis.srem(self.WHITELIST_KEY, str(user.id))
            await ctx.send(f"User <@{user.id}> has been removed from the whitelist.", ephemeral=True)

    @interactions.slash_command(name="search", description="Search for a blacklisted user")
    @interactions.slash_option(
        name="pattern",
        description="Pattern to search for in the blacklist",
        required=True,
        opt_type=OptionType.STRING
    )
    async def search_blacklist(self, ctx: SlashContext, pattern: str):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not whitelisted!", ephemeral=True)
            return
        
        matched_data = self.db_blacklist.search_users(pattern)
        
        if not matched_data:
            await ctx.send(f"No blacklisted user found with the pattern `{pattern}`", ephemeral=True)
            return
        
        embeds = []
        for index, (user_id, user_info) in enumerate(matched_data):
            username = user_info["username"]
            reason = user_info["reason"]
            proof_link = user_info["proof_link"]
            embed = Embed(
                title=username,
                description="Here's some detailed information about the user:",
                color=Color.random(),
                fields=[
                    EmbedField(name="User ID", value=f"`{user_id}`", inline=True),
                    EmbedField(name="📜 Reason", value=reason, inline=False),
                    EmbedField(name="🔗 Proof Link", value=f"[Click Here]({proof_link})", inline=False),
                ],
                footer=EmbedFooter(text=f"Blacklist System | Result {index + 1} of {len(matched_data)}"),
                timestamp=datetime.datetime.now().isoformat()
            )
            embeds.append(embed)
        paginator = Paginator.create_from_embeds(self.bot, *embeds)
        await paginator.send(ctx, ephemeral=True)

    @interactions.slash_command(name="list-whitelist", description="List all whitelisted users")
    async def list_whitelist(self, ctx: SlashContext):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not whitelisted!", ephemeral=True)
            return
        
        whitelisted_ids = self.db_whitelist.redis.smembers(self.WHITELIST_KEY)
        if not whitelisted_ids:
            await ctx.send("There are no whitelisted users.", ephemeral=True)
            return

        # Prepare user mentions
        whitelisted_users = [f"<@{user_id.decode('utf-8')}>" for user_id in whitelisted_ids]

        # Handle potential message length limitations
        MAX_EMBED_FIELD_VALUE_LEN = 1024
        description_chunks = [whitelisted_users[i:i + MAX_EMBED_FIELD_VALUE_LEN] for i in range(0, len(whitelisted_users), MAX_EMBED_FIELD_VALUE_LEN)]
        for chunk in description_chunks:
            embed = Embed(
                title="Whitelisted Users",
                description="Here's a list of all whitelisted users:",
                color=Color.random(),
                fields=[
                    EmbedField(name="Users", value="\n".join(chunk) or "No users to display.", inline=False)
                ],
                footer=EmbedFooter(text="Whitelist System"),
                timestamp=datetime.datetime.now().isoformat()
            )
            await ctx.send(embed=embed)
        
    @interactions.slash_command(name="list", description="List all blacklisted users")
    async def list_blacklist(self, ctx: SlashContext):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not whitelisted!", ephemeral=True)
            return
        
        keys_values = self.db_blacklist.list_all_users_info()
        if not keys_values:
            await ctx.send("There are no blacklisted users.", ephemeral=True)
            return
        
        embeds = []
        for index, (user_id, user_info) in enumerate(keys_values.items()):
            username = user_info.get("username", "N/A")
            reason = user_info.get("reason", "N/A")
            proof_link = user_info.get("proof_link", "N/A")
            folder_id = user_info.get("folder_id", "N/A")

            embed = Embed(
                title=f"{username}",
                description="Here's some detailed information about the user:",
                color=Color.random(),
                fields=[
                    EmbedField(name="User ID", value=f"`{user_id}`", inline=True),
                    EmbedField(name="📜 Reason", value=f"*{reason}*", inline=False),
                    EmbedField(name="🔗 Proof Link", value=f"[Click Here]({proof_link})", inline=False),
                    EmbedField(name="Folder ID", value=f"`{folder_id}`", inline=True),
                ],
                footer=EmbedFooter(text=f"Blacklist System | Page {index + 1} of {len(keys_values)}"),
                timestamp=datetime.datetime.now().isoformat()
            )
            embeds.append(embed)
        
        paginator = Paginator.create_from_embeds(self.bot, *embeds)
        await paginator.send(ctx, ephemeral=True)
    
    @interactions.slash_command(name="blacklist", description="Blacklist a user")
    @interactions.slash_option(
        name="user",
        description="User to blacklist",
        required=True,
        opt_type=OptionType.USER,
    )
    @interactions.slash_option(
        name="reason",
        description="Reason for blacklisting",
        required=True,
        opt_type=OptionType.STRING,
    )
    @interactions.slash_option(
        name="file1",
        description="Image to blacklist",
        required=True,
        opt_type=OptionType.ATTACHMENT,
    )
    @interactions.slash_option(
        name="file2",
        description="Image to blacklist",
        required=False,
        opt_type=OptionType.ATTACHMENT,
    )
    @interactions.slash_option(
        name="file3",
        description="Image to blacklist",
        required=False,
        opt_type=OptionType.ATTACHMENT,
    )
    @interactions.slash_option(
        name="file4",
        description="Image to blacklist",
        required=False,
        opt_type=OptionType.ATTACHMENT,
    )
    @interactions.slash_option(
        name="file5",
        description="Image to blacklist",
        required=False,
        opt_type=OptionType.ATTACHMENT,
    )
    async def blacklist(self, ctx: SlashContext, user: interactions.User, reason: str, file1: interactions.Attachment, file2: interactions.Attachment=None, file3: interactions.Attachment=None, file4: interactions.Attachment=None, file5: interactions.Attachment=None):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not whitelisted!", ephemeral=True)
            return
        
        await ctx.defer(ephemeral=True)
        folder_id = self.drive.create_folder(f"blacklist-{user.username}")

        files = [file1, file2, file3, file4, file5]
        files = [file for file in files if file is not None]

        async with aiohttp.ClientSession() as session:
            for image in files:
                async with session.get(image.url) as resp:
                    if resp.status != 200 or resp.content_type not in ["image/png", "image/jpeg", "image/gif"]:
                        print(f"Failed to download image or invalid content type for {image.url}")
                        continue
                    fd, path = tempfile.mkstemp(suffix=".png")
                    try:
                        with os.fdopen(fd, 'wb') as tmp: tmp.write(await resp.read())
                        self.drive.upload_file(path, folder_id)
                    finally:
                        os.unlink(path)

        folder_link = self.drive.get_folder_link(folder_id)

        embed = Embed(
            title=f"{user.username} has been blacklisted!",
            description=f"Here's some detailed information about the blacklist:",
            color=Color.random(),
            fields=[
                EmbedField(name="User ID", value=f"`{user.id}`", inline=True),
                EmbedField(name="📜 Reason", value=f"*{reason}*", inline=False),
                EmbedField(name="🔗 Proof Link", value=f"[Click Here]({folder_link})", inline=False),
            ],
            footer=EmbedFooter(text="Blacklist System"),
            timestamp=datetime.datetime.now().isoformat()
        )       
 
        view_images_link_button = interactions.Button(
            style=interactions.ButtonStyle.LINK,
            label="View Images",
            url=folder_link
        )
        
        view_images_direct_button = interactions.Button(
            style=interactions.ButtonStyle.SECONDARY,
            label="View Images Direct",
            custom_id="view_images_direct"
        )
        
        action_row = interactions.ActionRow()
        action_row.components.append(view_images_link_button)
        action_row.components.append(view_images_direct_button)
        
        await ctx.send("User has been blacklisted!", ephemeral=True)
        # await ctx.send(embed=embed, components=[action_row], ephemeral=True)
        self.db_blacklist.set_user(str(user.id), user.username, reason, folder_link, folder_id)
        keys_values = self.db_blacklist.list_all_users_info()
        current_sync_hash = sha256(str(keys_values).encode('utf-8')).hexdigest()
        for guild in self.bot.guilds:
            try:
                if not guild.me.guild_permissions.BAN_MEMBERS:
                    print(f"Missing ban permissions in guild: {guild.name}")
                    ctx.send("I don't have permission to ban members in this server.", ephemeral=True)
                    continue
                await guild.ban(user.id, reason=f"Blacklisted: {reason}")
            
                blacklist_channel = next((channel for channel in guild.channels if self.BLACKLIST_CHANNEL_PATTERN.match(channel.name) or channel.name in ["blacklist", "blacklists"]), None)
                if not blacklist_channel:
                    print(f"Blacklist channel not found in guild {guild.name}")
                    continue
                
                await blacklist_channel.send(embed=embed, components=[action_row])
            except Exception as e:
                print(f"Failed to ban or send embed in guild {guild.name}: {e}")
            self.db_servers.set_last_sync_details(str(guild.id), current_sync_hash)
    
    @interactions.component_callback("view_images_direct")
    async def view_images_direct_clicked(self, ctx: interactions.ComponentContext):
        if not ctx.message.embeds[0].fields[3].value:
            await ctx.send("No images found in the folder.", ephemeral=True)
            return
        folder_id = ctx.message.embeds[0].fields[3].value
        await ctx.send("Processing images...", ephemeral=True)
        
        image_files = self.drive.list_files(folder_id, images_only=True)
        if not image_files:
            await ctx.send("No images found in the folder.", ephemeral=True)
            return

        image_files = image_files[:10]
        files = []
        temp_dir = tempfile.TemporaryDirectory()
        
        try:
            for image_file in image_files:
                file_id = image_file['id']
                filename = image_file['name']
                temp_file_path = os.path.join(temp_dir.name, filename)
                self.drive.download_file(file_id, temp_file_path)
                files.append(temp_file_path)
            await ctx.send(files=files, ephemeral=True)
        finally:
            temp_dir.cleanup()
    
    @interactions.slash_command(name="unblacklist", description="Unblacklist a user")
    @interactions.slash_option(
        name="user",
        description="User to unblacklist",
        required=True,
        opt_type=OptionType.USER,
    )
    async def unblacklist(self, ctx: SlashContext, user: interactions.User):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not whitelisted!", ephemeral=True)
            return
        
        if not self.db_blacklist.exists(str(user.id)):
            await ctx.send(f"User <@{user.id}> is not blacklisted.", ephemeral=True)
        else:
            self.db_blacklist.delete_user(str(user.id))
            await ctx.send(f"User <@{user.id}> has been removed from the blacklist.", ephemeral=True)
        for guild in self.bot.guilds:
            try:
                await guild.unban(user)
            except Exception as e:
                print(f"Failed to unban user {user} in guild {guild.name}: {e}")