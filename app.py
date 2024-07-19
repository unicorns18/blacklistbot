import json
from interactions import Client
from utils import logutils
import interactions
import os

from utils.configstuff import ConfigHandler

logger = logutils.CustomLogger(__name__)

DEBUG = True

client = Client(
    token="MTI2MjYyOTcyNDgwNzc2MTk1NA.G_sV1b.lZwZZEnM2Wd7c3MYFKjfHs1QA3T6ujFBCb2JhI" if not DEBUG else "MTI2MzY1NjA2NzQ1NjMwMzExNA.Gw_J_x.SHynfkOECNhZVcwbZGCoTiJs02kDwCAU4lYkTE",
    intents=interactions.Intents.ALL,
    activity=interactions.Activity(
        name="Peekaboo", type=interactions.ActivityType.PLAYING
    ),
)

@client.listen()
async def on_ready():
    logger.info(f"We have logged in as {client.app.name}")
    logger.info(f"User ID: {client.app.id}")
    logger.info(f"Connected to {len(client.guilds)} guilds")
    logger.info(f"Connected to {client.guilds}")
    guilds_data = []
    for guild in client.guilds:
        guild_data = {
            'id': str(guild.id),
            'name': guild.name,
            'icon': str(guild.icon.as_url()) if guild.icon else None
        }
        guilds_data.append(guild_data)
    with open('guilds.json', 'w') as f:
        json.dump(guilds_data, f)
    for guild in client.guilds:
        config_handler = ConfigHandler(str(guild.id))
        if not config_handler.get_config():
            config_handler.update_config({})


if __name__ == '__main__':
    extensions = [
        f"extensions.{f[:-3]}"
        for f in os.listdir("extensions")
        if f.endswith(".py") and not f.startswith("_")
    ]
    for extension in extensions:
        try:
            client.load_extension(extension)
            logger.info(f"Loaded extension {extension}")
        except interactions.errors.ExtensionLoadException as e:
            logger.error(f"Failed to load extension {extension}.", exc_info=e)

    client.start()
