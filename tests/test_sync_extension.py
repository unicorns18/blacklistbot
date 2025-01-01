import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from interactions import SlashContext, Guild, Member
from extensions.sync_extension import SyncBlacklistsExtension

@pytest.fixture
def mock_bot():
    return MagicMock()

@pytest.fixture
def mock_redis_db():
    with patch('database.RedisDB') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def sync_extension(mock_bot, mock_redis_db):
    extension = SyncBlacklistsExtension(mock_bot)
    extension.db = mock_redis_db
    extension.db_whitelist = mock_redis_db
    extension.db_servers = mock_redis_db
    return extension

@pytest.fixture
def mock_ctx():
    ctx = AsyncMock(spec=SlashContext)
    ctx.author = MagicMock()
    ctx.author.id = "123456789"
    ctx.guild = AsyncMock(spec=Guild)
    ctx.guild.id = "987654321"
    ctx.guild.me = MagicMock(spec=Member)
    ctx.guild.me.guild_permissions.BAN_MEMBERS = True
    ctx.defer = AsyncMock()
    ctx.send = AsyncMock()
    return ctx

@pytest.mark.asyncio
async def test_try_ban_success(sync_extension):
    guild = AsyncMock()
    user_id = "123456"
    
    # Mock successful ban and verification
    guild.ban = AsyncMock()
    guild.fetch_ban = AsyncMock(return_value=True)
    
    success, error = await sync_extension.try_ban(guild, user_id)
    assert success is True
    assert error is None
    guild.ban.assert_called_once_with(user_id, reason="Blacklisted by the bot.")
    guild.fetch_ban.assert_called_once_with(user_id)

@pytest.mark.asyncio
async def test_try_ban_failure(sync_extension):
    guild = AsyncMock()
    user_id = "123456"
    
    # Mock ban failure
    guild.ban = AsyncMock(side_effect=Exception("Ban failed"))
    
    success, error = await sync_extension.try_ban(guild, user_id)
    assert success is False
    assert "Ban failed" in error
    guild.ban.assert_called_once_with(user_id, reason="Blacklisted by the bot.")

@pytest.mark.asyncio
async def test_syncbans_no_permission(sync_extension, mock_ctx):
    mock_ctx.guild.me.guild_permissions.BAN_MEMBERS = False
    
    await sync_extension.syncbans(mock_ctx)
    
    mock_ctx.send.assert_called_once_with(
        "I do not have permission to ban members in this server.",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_syncbans_empty_blacklist(sync_extension, mock_ctx):
    sync_extension.db.list_all_users_info = MagicMock(return_value={})
    sync_extension.db_servers.check_if_guild_synced = MagicMock(return_value=False)
    sync_extension.db_servers.get_sync_details = MagicMock(return_value={})
    sync_extension.is_user_whitelisted = AsyncMock(return_value=False)
    
    await sync_extension.syncbans(mock_ctx)
    
    mock_ctx.send.assert_called_once_with(
        "There are no blacklisted users.",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_syncbans_already_synced(sync_extension, mock_ctx):
    # Mock data
    sync_extension.db.list_all_users_info = MagicMock(return_value={"123": {}})
    sync_extension.db_servers.check_if_guild_synced = MagicMock(return_value=True)
    sync_extension.db_servers.get_sync_details = MagicMock(return_value={
        "channel_id": "456",
        "count": "1"
    })
    sync_extension.is_user_whitelisted = AsyncMock(return_value=False)
    
    await sync_extension.syncbans(mock_ctx)
    
    mock_ctx.send.assert_called_once_with(
        "✅ Blacklist in this guild is already up to date.\n"
        "Channel ID: 456\n"
        "Users Synced: 1",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_syncbans_full_sync(sync_extension, mock_ctx):
    # Mock data
    test_users = {
        "123": {"username": "test1"},
        "456": {"username": "test2"}
    }
    sync_extension.db.list_all_users_info = MagicMock(return_value=test_users)
    sync_extension.db_servers.check_if_guild_synced = MagicMock(return_value=False)
    sync_extension.db_servers.get_sync_details = MagicMock(return_value={})
    sync_extension.is_user_whitelisted = AsyncMock(return_value=False)
    sync_extension.try_ban = AsyncMock(return_value=(True, None))
    
    # Mock message for progress updates
    mock_msg = AsyncMock()
    mock_ctx.send = AsyncMock(return_value=mock_msg)
    mock_ctx.defer = AsyncMock()
    
    # Mock sleep to speed up test
    with patch('asyncio.sleep', new_callable=AsyncMock):
        await sync_extension.syncbans(mock_ctx)
    
    # Verify progress updates were made
    assert mock_msg.edit.call_count >= 4  # Initial, start, progress, and completion messages
    assert sync_extension.try_ban.call_count == len(test_users)  # Ban attempts for each user
    
    # Verify message updates
    mock_msg.edit.assert_any_call(content="🔄 Initializing sync process...")
    mock_msg.edit.assert_any_call(content=f"🔄 Starting sync process for {len(test_users)} users...")
    mock_msg.edit.assert_any_call(content=(
        f"🔄 Syncing bans... Progress: 1/{len(test_users)}\n"
        f"✅ Successful: 0\n"
        f"❌ Failed: 0"
    ))
    mock_msg.edit.assert_any_call(content="✅ Sync process completed!")
    
    # Verify final status message
    expected_status = (
        "Sync complete!\n"
        "✅ Successfully banned in 2/2 attempts\n"
        "❌ Failed in 0 attempts\n"
    )
    mock_ctx.send.assert_called_with(expected_status, ephemeral=True)
