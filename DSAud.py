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

if not config['sources']:
    exit('sources не должен быть пуст!')

DATA = config['sources'][0]

client = Bot(command_prefix=list(config['prefix']))

def parse_song_name():
    mpdclient = MPDClient()
    mpdclient.connect(DATA['mpd_hostname'], int(DATA['mpd_port']))
    if DATA['mpd_password']:
	    mpdclient.password(DATA['mpd_password'])

    song_data = mpdclient.currentsong()
    if 'title' not in song_data:
        return os.path.splitext(os.path.basename(song_data['file']))[0]
    title = song_data['title']
    mpdclient.disconnect()
    return title

async def status_task():
    while True:
        track = parse_song_name()
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=track+" |   Помощь: "+config['prefix']+'h'))
        await asyncio.sleep(8)

@client.command(aliases=['h'])
async def hlp(ctx):
    help_message = discord.Embed(title='Команды бота:', description=f'Основное:\n'+config['prefix']+'p- включить радио\n'+config['prefix']+'s- остановить\n'+config['prefix']+'c- сменить канал\n______________________\nРадиостанции:\n0) mashup radio - beats to napas\n1) mashup radio - 1.kla$ only\n2) Random rock radio [24/7] || RockCafe Radio', colour=discord.Color.green())
    await ctx.send(embed=help_message)

@client.event
async def on_ready():
    client.loop.create_task(status_task())

@client.command(aliases=['p'])
async def play(ctx, change=False):

    if not change:
        main_message = discord.Embed(title='Привет! Подожди, идет кеширование\nНе забывай писать ``'+config['prefix']+'s`` для остановки, когда выходишь', colour=discord.Color.green())
        await ctx.send(embed=main_message)
    else: 
        main_message = discord.Embed(title='Подожди! Идет смена сервера!\nНе забывай писать ``'+config['prefix']+'s`` для остановки, когда выходишь', colour=discord.Color.green())
        await ctx.send(embed=main_message)

    channel = ctx.message.author.voice.channel
    global player
    try:
        player = await channel.connect()
    except:
        pass
    player.play(FFmpegPCMAudio(DATA['source']))
    track = parse_song_name()
    track_message = discord.Embed(title='Текущий трек:', description=track, colour=discord.Color.green())
    await ctx.send(embed=track_message)

@client.command(aliases=['s'])
async def stop(ctx):
    global player
    player.stop()
    await ctx.guild.voice_client.disconnect()
    await ctx.send('Пока!')
    
    player = None


@client.command(aliases=['c'])
async def change(ctx):
    splited = ctx.message.content.split()
    if(splited[1:]):
        index = int(splited[1]) if splited[1].isdigit() else None

        if index == None:
            await ctx.send('Индекс должен быть числом!')
            return
        global DATA
        DATA = config['sources'][index]
        
        global player
        if player:
            player.stop()
            await ctx.guild.voice_client.disconnect()
            player = None
            await play(ctx, True)

client.run(config['token'])
