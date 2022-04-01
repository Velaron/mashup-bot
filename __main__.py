import json
import os
from typing import Any

import discord
from discord import Intents
from discord.commands import Option
from discord.commands.errors import ApplicationCommandError
from discord.ext import tasks
from mpd.asyncio import MPDClient


class Config:
    def __init__(self):
        with open('config.json', 'r') as f:
            data = json.load(f)

            self.stations: list[dict[str, Any]] = data['sources']
            self.token: str = data['token']
            self.debug_guilds: list[int] = data['debug_guilds']
            self.status = {
                'host': data['status_host'],
                'port': data['status_port']
            }

    def get_station(self, name: str) -> dict[str, Any]:
        for station in self.stations:
            if station['name'] == name:
                return station

    def get_filter(self) -> list[str]:
        return [x['name'] for x in config.stations]


FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10', 'options': '-vn'
}

config: Config = Config()

bot: discord.Bot = discord.Bot(
    debug_guilds=config.debug_guilds,
    intents=Intents.default(),
)

client = MPDClient()


class Player:
    instances: list['Player'] = []

    def __init__(self, guild: discord.Guild):
        self.voice_client: discord.VoiceClient = guild.voice_client
        self.id = guild.id

    async def play(self, audio: discord.FFmpegPCMAudio):
        if self.voice_client.is_playing():
            self.voice_client.stop()

        self.voice_client.play(audio)

    async def stop(self):
        self.voice_client.stop()
        await self.voice_client.disconnect()
        Player.instances.remove(self)

    @staticmethod
    def get(guild: discord.Guild) -> 'Player':
        for p in Player.instances:
            if p.id == guild.id:
                return p

        p = Player(guild)
        Player.instances.append(p)
        return p


@tasks.loop()
async def update_presence():
    song_data = await client.currentsong()

    track = 'Silence...'

    if 'title' not in song_data or 'artist' not in song_data:
        track = os.path.splitext(os.path.basename(song_data['file']))[0]
    else:
        track = f'{song_data["title"]} - {song_data["artist"]}'

    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=track))

    async for _ in client.idle():
        break


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    player = Player.get(member.guild)
    player.voice_client = member.guild.voice_client

    if player.voice_client:
        if len(player.voice_client.channel.voice_states.keys()) == 1:
            # leave if bot is alone
            await player.stop()


@bot.event
async def on_ready():
    # status
    await client.connect(config.status['host'], port=config.status['port'])
    update_presence.start()

    print(f'mashup-bot [{bot.user}] initialization complete.')


@bot.slash_command()
async def play(
    ctx,
    station: Option(str, 'Название станции', choices=config.get_filter())
):
    '''Слушать радио'''
    player = Player.get(ctx.guild)

    audio = discord.FFmpegPCMAudio(
        config.get_station(station)['source'],
        **FFMPEG_OPTIONS
    )
    await player.play(audio)

    embed = discord.Embed(
        title='Воспроизведение',
        description=config.get_station(station)['description'],
        color=discord.Color.teal()
    )
    await ctx.respond(embed=embed)


@bot.slash_command()
async def stop(ctx):
    '''Остановить воспроизведение'''
    await Player.get(ctx.guild).stop()
    embed = discord.Embed(
        title='Воспроизведение остановлено',
        color=discord.Color.teal()
    )
    await ctx.respond(embed=embed)


@play.before_invoke
@stop.before_invoke
async def ensure_voice(ctx):
    if ctx.voice_client is None:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            embed = discord.Embed(
                title='Ошибка',
                description='Вы не в голосовом канале',
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed, ephemeral=True)
            raise ApplicationCommandError(
                'User not connected to a voice channel.')

def main():
    bot.run(config.token)

if __name__ == "__main__":
    main()
