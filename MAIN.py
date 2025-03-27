import ctypes
import sys
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
from dotenv import load_dotenv
import os
import requests
from discord.ui import Button, View, Modal, TextInput

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, __file__, None, 1
    )
    sys.exit()

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.hybrid_command(name="sync", with_app_command=True, description="Sync slash commands.")
@commands.is_owner()
async def sync(ctx):
    await bot.tree.sync()
    await ctx.reply("Slash commands synced!", ephemeral=True)

song_queue = asyncio.Queue()
volume_level = 1.0

def create_embed(title, description):
    embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
    return embed

def create_embed_with_buttons(title, description, buttons):
    embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
    view = View()
    for button in buttons:
        view.add_item(button)
    return embed, view

class VolumeModal(Modal, title="Set Volume"):
    volume_input = TextInput(label="Volume (1-100)", placeholder="Enter a number between 1 and 100", required=True)

    def __init__(self, interaction: discord.Interaction):
        super().__init__()
        self.interaction = interaction

    async def on_submit(self, interaction: discord.Interaction):
        global volume_level
        try:
            volume = int(self.volume_input.value)
            if not (1 <= volume <= 100):
                raise ValueError("Volume must be between 1 and 100.")
            volume_level = volume / 100.0
            if interaction.guild.voice_client and interaction.guild.voice_client.source:
                interaction.guild.voice_client.source.volume = volume_level
            embed = create_embed("Volume", f"Volume set to {volume}%.")
            await interaction.response.send_message(embed=embed)
        except ValueError:
            embed = create_embed("Error", "Invalid input. Please enter a number between 1 and 100.")
            await interaction.response.send_message(embed=embed)

class SkipButton(Button):
    def __init__(self):
        super().__init__(label="Skip", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            embed = create_embed("Music", "Skipped the current song.")
            await interaction.response.send_message(embed=embed)
        else:
            embed = create_embed("Error", "No music is playing.")
            await interaction.response.send_message(embed=embed)

class StopButton(Button):
    def __init__(self):
        super().__init__(label="Stop", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await clear_queue()
            embed = create_embed("Music", "Stopped the music and cleared the queue.")
            await interaction.response.send_message(embed=embed)
        else:
            embed = create_embed("Error", "No music is playing.")
            await interaction.response.send_message(embed=embed)

class VolumeButton(Button):
    def __init__(self):
        super().__init__(label="Set Volume", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(VolumeModal(interaction))

async def clear_queue():
    while not song_queue.empty():
        await song_queue.get()

@bot.tree.command(name="join", description="Join the voice channel.")
async def join(interaction: discord.Interaction):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        await channel.connect()
        embed = create_embed("Voice Channel", f"Joined {channel}!")
        await interaction.response.send_message(embed=embed)
    else:
        embed = create_embed("Error", "You need to be in a voice channel to use this command.")
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leave", description="Leave the voice channel.")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await clear_queue()
        embed = create_embed("Voice Channel", "Disconnected from the voice channel and cleared the queue.")
        await interaction.response.send_message(embed=embed)
    else:
        embed = create_embed("Error", "I'm not in a voice channel.")
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="play", description="Play a song or playlist from YouTube.")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()

    if not interaction.guild.voice_client:
        if interaction.user.voice:
            channel = interaction.user.voice.channel
            await channel.connect()
        else:
            embed = create_embed("Error", "You need to be in a voice channel to use this command.")
            await interaction.followup.send(embed=embed)
            return

    if not query.startswith("http://") and not query.startswith("https://"):
        query = f"ytsearch:{query}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'nocheckcertificate': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(query, download=False)

            if 'entries' in info:
                for entry in info['entries']:
                    song_title = entry.get('title', 'Unknown Title')
                    await song_queue.put((song_title, entry['webpage_url'], interaction))
                embed = create_embed("Queue", f"Added **{song_title}** to the queue.")
                await interaction.followup.send(embed=embed)
            else:
                song_title = info.get('title', 'Unknown Title')
                await song_queue.put((song_title, query, interaction))
                embed = create_embed("Queue", f"Added **{song_title}** to the queue.")
                await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = create_embed("Error", f"An error occurred: {str(e)}")
            await interaction.followup.send(embed=embed)
            return

    if not interaction.guild.voice_client.is_playing():
        await process_queue(interaction.guild.voice_client)

@bot.tree.command(name="volume", description="Adjust the playback volume.")
async def volume(interaction: discord.Interaction):
    await interaction.response.send_modal(VolumeModal(interaction))

async def process_queue(voice_client):
    if not song_queue.empty():
        song_title, query, interaction = await song_queue.get()

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'nocheckcertificate': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                if "http" in query:
                    info = ydl.extract_info(query, download=False)
                else:
                    info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]

                audio_url = None
                for fmt in info['formats']:
                    if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none' and '.m3u8' not in fmt['url']:
                        audio_url = fmt['url']
                        break

                if not audio_url:
                    raise Exception("No valid audio format found (HLS or .m3u8 excluded).")

                print(f"Streaming MP3: {audio_url}")
            except Exception as e:
                embed = create_embed("Error", f"An error occurred: {str(e)}")
                await interaction.followup.send(embed=embed)
                return

        async def after_playing(error):
            if error:
                print(f"Error after playing: {error}")
            else:
                print("Finished playing successfully.")
            await process_queue(voice_client)

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
        }

        try:
            voice_client.stop()
            source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
            source = discord.PCMVolumeTransformer(source, volume=volume_level)
            voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(after_playing(e), bot.loop))
            embed, view = create_embed_with_buttons(
                "Now Playing", f"**{song_title}**", [SkipButton(), StopButton(), VolumeButton()]
            )
            await interaction.followup.send(embed=embed, view=view)
        except Exception as e:
            embed = create_embed("Error", f"An error occurred during playback: {str(e)}")
            await interaction.followup.send(embed=embed)

@bot.tree.command(name="skip", description="Skip the current song.")
async def skip(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
        embed = create_embed("Music", "Skipped the current song.")
        await interaction.response.send_message(embed=embed)
    else:
        embed = create_embed("Error", "No music is playing.")
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="queue_remove", description="Remove a song from the queue.")
async def queue_remove(interaction: discord.Interaction, position: int):
    if song_queue.empty():
        embed = create_embed("Error", "The queue is empty.")
        await interaction.response.send_message(embed=embed)
        return

    queue_list = []
    while not song_queue.empty():
        queue_list.append(await song_queue.get())

    if position < 1 or position > len(queue_list):
        embed = create_embed("Error", f"Invalid position. The queue has {len(queue_list)} songs.")
        await interaction.response.send_message(embed=embed)
        for item in queue_list:
            await song_queue.put(item)
        return

    removed_song = queue_list.pop(position - 1)
    embed = create_embed("Queue", f"Removed song at position {position}: **{removed_song[0]}**")
    await interaction.response.send_message(embed=embed)

    for item in queue_list:
        await song_queue.put(item)

@bot.tree.command(name="stop", description="Stop the current song and clear the queue.")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
        await clear_queue()
        embed, view = create_embed_with_buttons(
            "Music", "Stopped the music and cleared the queue.", [SkipButton(), StopButton()]
        )
        await interaction.response.send_message(embed=embed, view=view)
    else:
        embed = create_embed("Error", "No music is playing.")
        await interaction.response.send_message(embed=embed)

class QueueRemoveModal(Modal, title="Remove Song from Queue"):
    position_input = TextInput(label="Song Position", placeholder="Enter the position of the song to remove", required=True)

    def __init__(self, interaction: discord.Interaction, queue_list):
        super().__init__()
        self.interaction = interaction
        self.queue_list = queue_list

    async def on_submit(self, interaction: discord.Interaction):
        try:
            position = int(self.position_input.value)
            if position < 1 or position > len(self.queue_list):
                raise ValueError(f"Invalid position. The queue has {len(self.queue_list)} songs.")
            
            removed_song = self.queue_list.pop(position - 1)
            embed = create_embed("Queue", f"Removed song at position {position}: **{removed_song[0]}**")
            await interaction.response.send_message(embed=embed)

            for item in self.queue_list:
                await song_queue.put(item)
        except ValueError as e:
            embed = create_embed("Error", str(e))
            await interaction.response.send_message(embed=embed)

class QueueRemoveButton(Button):
    def __init__(self):
        super().__init__(label="Remove from Queue", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        if song_queue.empty():
            embed = create_embed("Error", "The queue is empty.")
            await interaction.response.send_message(embed=embed)
            return

        queue_list = []
        while not song_queue.empty():
            queue_list.append(await song_queue.get())

        queue_display = "\n".join([f"{i + 1}. {item[1]}" for i, item in enumerate(queue_list)])
        modal = QueueRemoveModal(interaction, queue_list)
        modal.position_input.placeholder = f"Queue:\n{queue_display}\nEnter position to remove"
        await interaction.response.send_modal(modal)

@bot.tree.command(name="queue", description="View the current song queue.")
async def queue(interaction: discord.Interaction):
    if song_queue.empty():
        embed = create_embed("Queue", "The queue is currently empty.")
        await interaction.response.send_message(embed=embed)
        return

    queue_list = []
    while not song_queue.empty():
        queue_list.append(await song_queue.get())

    for item in queue_list:
        await song_queue.put(item)

    queue_display = "\n".join([f"{i + 1}. {item[0]}" for i, item in enumerate(queue_list)])
    embed, view = create_embed_with_buttons(
        "Current Queue",
        f"**Total Songs:** {len(queue_list)}\n\n{queue_display}",
        [QueueRemoveButton()]
    )
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="help", description="Show all available commands.")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="Help - Music Bot Commands", color=discord.Color.green())
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/727/727245.png")

    embed.add_field(
        name=":information_source: General Commands",
        value=(
            "`/help` - Show this help message.\n"
            "`/sync` - Sync slash commands (owner only).\n"
        ),
        inline=False
    )

    embed.add_field(
        name=":musical_note: Music Commands",
        value=(
            "`/play <query>` - Play a song or add it to the queue.\n"
            "`/skip` - Skip the current song.\n"
            "`/stop` - Stop the music and clear the queue.\n"
            "`/queue` - View the current song queue.\n"
            "`/queue_remove <position>` - Remove a song from the queue.\n"
            "`/volume` - Adjust the playback volume.\n"
        ),
        inline=False
    )

    embed.add_field(
        name=":loud_sound: Voice Commands",
        value=(
            "`/join` - Join the voice channel.\n"
            "`/leave` - Leave the voice channel.\n"
        ),
        inline=False
    )

    embed.set_footer(text="Music Bot - Made by Indestinate")
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    bot.loop.create_task(disconnect_if_alone())

async def disconnect_if_alone():
    while True:
        await asyncio.sleep(60)
        for guild in bot.guilds:
            voice_client = guild.voice_client
            if voice_client and len(voice_client.channel.members) == 1:
                print(f"Disconnecting from {voice_client.channel} because I'm alone.")
                await voice_client.disconnect()

if not TOKEN:
    print("Error: DISCORD_TOKEN is missing or invalid in the .env file.")
    print("The program will close in 30 seconds...")
    asyncio.run(asyncio.sleep(30))
    sys.exit(1)

try:
    bot.run(TOKEN)
except discord.LoginFailure:
    print("Error: Failed to log in. Please check your DISCORD_TOKEN in the .env file.")
    print("The program will close in 30 seconds...")
    asyncio.run(asyncio.sleep(30))
    sys.exit(1)