from discord import FFmpegPCMAudio
from discord.ext.commands import Bot
import discord
import subprocess
import asyncio
import json
import os
from mpd import MPDClient

config = {}
with open('config.json', 'r') as f:
	config = json.load(f)

client = Bot(command_prefix=list(config['prefix']))

def parse_song_name():
    mpdclient = MPDClient()
    mpdclient.connect(config['mpd_hostname'], int(config['mpd_port']))
    if len(config['mpd_password']) > 0:
	    mpdclient.password(config['mpd_password'])

    song_data = mpdclient.currentsong()
    if 'title' not in song_data:
        return os.path.splitext(os.path.basename(song_data['file']))[0]
    title = song_data['title']
    mpdclient.disconnect()
    return title

async def status_task():
    while True:
        track = parse_song_name()
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=track+" |   Запуск: "+config['prefix']+'p'))
        await asyncio.sleep(8)

@client.event
async def on_ready():
    client.loop.create_task(status_task())


@client.command(aliases=['p'])
async def play(ctx):
    main_message = discord.Embed(title='Привет! Подожди, идет кеширование\nНе забывай писать ``-s`` для остановки, когда выходишь', colour=discord.Color.green())
    await ctx.send(embed=main_message)
    channel = ctx.message.author.voice.channel
    global player
    try:
        player = await channel.connect()
    except:
        pass
    player.play(FFmpegPCMAudio(config['source']))
    track = parse_song_name()
    track_message = discord.Embed(title='Текущий трек:', description=track, colour=discord.Color.green())
    await ctx.send(embed=track_message)

@client.command(aliases=['s'])
async def stop(ctx):
    player.stop()
    await ctx.guild.voice_client.disconnect()
    await ctx.send('Пока!')


client.run(config['token'])
