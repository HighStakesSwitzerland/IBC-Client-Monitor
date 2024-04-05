from syslog import syslog, LOG_ERR
from discord import SyncWebhook, Embed
from config import discord_webhook

def discord_message(title, description, color, tag=None):
    try:
        webhook = SyncWebhook.from_url(discord_webhook)
        # discord messages can't exceed 4096 characters, need to truncate in case it's longer.
        embed = Embed(title=title, description=description[:(4095 - len(title))], color=color)
        webhook.send(tag, embed=embed)
    except Exception as e:
        syslog(LOG_ERR, f"IBC: Couldn't send a discord alert, please check configuration.\n{description}\n{e}")