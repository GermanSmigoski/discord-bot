import os
import sys
import re
import html
import json
import random
import asyncio
import requests
import discord
from discord.ext import commands
import yt_dlp
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print("ERROR: No se encontro DISCORD_TOKEN en el archivo .env")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

queues = {}
history = {}
current_tracks = {}
guild_volumes = {}
now_playing_messages = {}
loop_modes = {}
autoplay_modes = {}

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extract_flat': 'in_playlist',
    'noplaylist': False,
    'skip_download': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

def format_duration(seconds):
    if not seconds:
        return "N/A"
    try:
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h {m}m {s}s"
        return f"{m}m {s:02d}s"
    except Exception:
        return str(seconds)

def parse_spotify(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    embed_url = url
    if '/playlist/' in url and '/embed/' not in url:
        playlist_id = url.split('/playlist/')[1].split('?')[0]
        embed_url = f"https://open.spotify.com/embed/playlist/{playlist_id}"
    elif '/album/' in url and '/embed/' not in url:
        album_id = url.split('/album/')[1].split('?')[0]
        embed_url = f"https://open.spotify.com/embed/album/{album_id}"
    elif '/track/' in url and '/embed/' not in url:
        track_id = url.split('/track/')[1].split('?')[0]
        embed_url = f"https://open.spotify.com/embed/track/{track_id}"

    try:
        res = requests.get(embed_url, headers=headers, timeout=10)
        if res.status_code != 200:
            res = requests.get(url, headers=headers, timeout=10)

        page_text = res.text
        tracks = []

        next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page_text)
        if next_data_match:
            try:
                data = json.loads(next_data_match.group(1))
                state_data = data.get('props', {}).get('pageProps', {}).get('state', {}).get('data', {})
                entity = state_data.get('entity', {})
                track_list = entity.get('trackList', []) or entity.get('tracks', [])
                
                for t in track_list:
                    t_title = t.get('title') or t.get('name')
                    t_artist = t.get('subtitle') or t.get('artist') or ''
                    if isinstance(t_artist, list):
                        t_artist = ', '.join([a.get('name', '') for a in t_artist if isinstance(a, dict)])
                    if t_title:
                        item = f"{t_artist} - {t_title}" if t_artist else t_title
                        tracks.append(html.unescape(item))

                if tracks:
                    return tracks
            except Exception as json_err:
                print(f"Error parseando JSON Spotify: {json_err}")

        matches = re.findall(r'"name":"([^"]+)","artists":\[\{"name":"([^"]+)"', page_text)
        if matches:
            seen = set()
            for title, artist in matches:
                clean_t = html.unescape(title)
                clean_a = html.unescape(artist)
                item = f"{clean_a} - {clean_t}"
                if item not in seen and "Spotify" not in clean_t:
                    seen.add(item)
                    tracks.append(item)
            if tracks:
                return tracks

        title_match = re.search(r'<meta property="og:title" content="(.*?)"', page_text)
        desc_match = re.search(r'<meta property="og:description" content="(.*?)"', page_text)
        if title_match:
            title = html.unescape(title_match.group(1))
            artist = html.unescape(desc_match.group(1).split('·')[0].strip()) if desc_match else ""
            return [f"{artist} - {title}" if artist else title]

    except Exception as e:
        print(f"Error en parse_spotify: {e}")

    return []

class PlaylistModalView(discord.ui.View):
    """Vista efímera para la ventana de Playlist con botón directo de Vaciar Lista"""
    def __init__(self, guild_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id

    @discord.ui.button(label="Vaciar Lista", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def clear_queue_modal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        count = len(queues.get(self.guild_id, []))
        queues[self.guild_id] = []
        
        embed = discord.Embed(
            title="🗑️ Cola Vaciada",
            description=f"Se han eliminado **{count}** canciones de la cola de reproducción.",
            color=discord.Color.red()
        )
        button.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

class MusicPanelControlView(discord.ui.View):
    def __init__(self, ctx, guild_id):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.guild_id = guild_id

    # FILA 0
    @discord.ui.button(label="Down", style=discord.ButtonStyle.secondary, emoji="🔉", row=0)
    async def down_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        curr_vol = guild_volumes.get(self.guild_id, 0.7)
        new_vol = max(0.1, round(curr_vol - 0.15, 2))
        guild_volumes[self.guild_id] = new_vol
        vc = interaction.guild.voice_client
        if vc and vc.source and isinstance(vc.source, discord.PCMVolumeTransformer):
            vc.source.volume = new_vol
        await interaction.response.send_message(f"🔉 Volumen: **{int(new_vol * 100)}%**", ephemeral=True, delete_after=3)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, emoji="⏮️", row=0)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        hist = history.get(self.guild_id, [])
        vc = interaction.guild.voice_client
        if not hist:
            return await interaction.response.send_message("❌ No hay canciones anteriores en el historial.", ephemeral=True, delete_after=3)
        
        prev_track = hist.pop()
        curr_track = current_tracks.get(self.guild_id)
        if curr_track:
            queues[self.guild_id].insert(0, curr_track)
        queues[self.guild_id].insert(0, prev_track)
        
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
        else:
            await play_next(self.ctx, self.guild_id)

        await interaction.response.send_message("⏮️ Volviendo a la canción anterior...", ephemeral=True, delete_after=3)

    @discord.ui.button(label="Resume", style=discord.ButtonStyle.secondary, emoji="⏯️", row=0)
    async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            if vc.is_playing():
                vc.pause()
                await interaction.response.send_message("⏸️ Pausado.", ephemeral=True, delete_after=3)
            elif vc.is_paused():
                vc.resume()
                await interaction.response.send_message("▶️ Reanudado.", ephemeral=True, delete_after=3)
            else:
                await interaction.response.send_message("❌ No hay nada reproduciéndose.", ephemeral=True, delete_after=3)
        else:
            await interaction.response.send_message("❌ No estoy en un canal de voz.", ephemeral=True, delete_after=3)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️", row=0)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏭️ Saltando canción...", ephemeral=True, delete_after=3)
        else:
            await interaction.response.send_message("❌ No hay más canciones en la cola.", ephemeral=True, delete_after=3)

    @discord.ui.button(label="Up", style=discord.ButtonStyle.secondary, emoji="🔊", row=0)
    async def up_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        curr_vol = guild_volumes.get(self.guild_id, 0.7)
        new_vol = min(2.0, round(curr_vol + 0.15, 2))
        guild_volumes[self.guild_id] = new_vol
        vc = interaction.guild.voice_client
        if vc and vc.source and isinstance(vc.source, discord.PCMVolumeTransformer):
            vc.source.volume = new_vol
        await interaction.response.send_message(f"🔊 Volumen: **{int(new_vol * 100)}%**", ephemeral=True, delete_after=3)

    # FILA 1
    @discord.ui.button(label="Shuffle", style=discord.ButtonStyle.secondary, emoji="🔀", row=1)
    async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        q = queues.get(self.guild_id, [])
        if len(q) > 1:
            random.shuffle(q)
            await interaction.response.send_message(f"🔀 Cola mezclada ({len(q)} canciones).", ephemeral=True, delete_after=3)
        else:
            await interaction.response.send_message("❌ No hay suficientes canciones en la cola para mezclar.", ephemeral=True, delete_after=3)

    @discord.ui.button(label="Loop", style=discord.ButtonStyle.secondary, emoji="🔁", row=1)
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        curr_loop = loop_modes.get(self.guild_id, False)
        loop_modes[self.guild_id] = not curr_loop
        status = "Activado 🔁" if loop_modes[self.guild_id] else "Desactivado ➡️"
        await interaction.response.send_message(f"Modo Bucle: **{status}**", ephemeral=True, delete_after=3)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.secondary, emoji="⏹️", row=1)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        queues[self.guild_id] = []
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
        await interaction.response.send_message("⏹️ Reproducción detenida y bot desconectado.", ephemeral=True, delete_after=3)

    @discord.ui.button(label="AutoPlay", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def autoplay_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        curr_auto = autoplay_modes.get(self.guild_id, False)
        autoplay_modes[self.guild_id] = not curr_auto
        status = "Activado 🔄" if autoplay_modes[self.guild_id] else "Desactivado ⏹️"
        await interaction.response.send_message(f"Modo AutoPlay: **{status}**", ephemeral=True, delete_after=3)

    @discord.ui.button(label="Playlist", style=discord.ButtonStyle.secondary, emoji="📑", row=1)
    async def playlist_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        q = queues.get(self.guild_id, [])
        if not q:
            return await interaction.response.send_message("📑 La cola de reproducción está vacía.", ephemeral=True, delete_after=5)

        upcoming = "\n".join([f"**{i+1}.** `{t.get('title', 'Canción')}`" for i, t in enumerate(q[:10])])
        total = len(q)
        more = f"\n\n*... y {total - 10} canciones más en la cola.*" if total > 10 else ""
        
        embed = discord.Embed(
            title="📑 Cola de Reproducción Próxima",
            description=f"{upcoming}{more}",
            color=discord.Color.from_rgb(43, 45, 49)
        )
        view = PlaylistModalView(self.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=20)

    # FILA 2
    @discord.ui.button(label="Vaciar Lista", style=discord.ButtonStyle.danger, emoji="🗑️", row=2)
    async def clear_queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        count = len(queues.get(self.guild_id, []))
        queues[self.guild_id] = []
        await interaction.response.send_message(f"🗑️ Se eliminaron **{count}** canciones de la cola de reproducción.", ephemeral=True, delete_after=5)

async def play_next(ctx, guild_id):
    if loop_modes.get(guild_id) and current_tracks.get(guild_id):
        queues[guild_id].insert(0, current_tracks[guild_id])

    if queues.get(guild_id) and len(queues[guild_id]) > 0:
        track = queues[guild_id].pop(0)
        voice_client = ctx.guild.voice_client

        if not voice_client or not voice_client.is_connected():
            return

        if current_tracks.get(guild_id) and not loop_modes.get(guild_id):
            if guild_id not in history:
                history[guild_id] = []
            history[guild_id].append(current_tracks[guild_id])

        current_tracks[guild_id] = track

        if guild_id in now_playing_messages:
            try:
                await now_playing_messages[guild_id].delete()
            except Exception:
                pass
            now_playing_messages.pop(guild_id, None)

        try:
            loop = asyncio.get_event_loop()
            
            def fetch_yt_info():
                with yt_dlp.YoutubeDL({'format': 'bestaudio', 'quiet': True, 'default_search': 'ytsearch'}) as ytdl:
                    info = ytdl.extract_info(track['query'], download=False)
                    if 'entries' in info and len(info['entries']) > 0:
                        return info['entries'][0]
                    return info

            info = await loop.run_in_executor(None, fetch_yt_info)
            audio_url = info.get('url')
            title = info.get('title', track.get('title', 'Canción'))
            duration = format_duration(info.get('duration'))
            author = info.get('uploader') or info.get('artist') or 'Desconocido'
            requested_by = track.get('requested_by', ctx.author.mention)
            webpage_url = info.get('webpage_url', 'https://youtube.com')

            embed = discord.Embed(color=discord.Color.from_rgb(43, 45, 49))
            avatar_url = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else (bot.user.avatar.url if bot.user.avatar else None)
            embed.set_author(name="MUSIC PANEL", icon_url=avatar_url)
            embed.description = f"💿 [`{title}`]({webpage_url})"
            
            embed.add_field(name="👤 Requested By", value=f"`{requested_by}`", inline=True)
            embed.add_field(name="⏱️ Music Duration", value=f"`{duration}`", inline=True)
            embed.add_field(name="🎧 Music Author", value=f"`{author}`", inline=True)

            view = MusicPanelControlView(ctx, guild_id)
            msg = await ctx.send(embed=embed, view=view)
            now_playing_messages[guild_id] = msg

            def after_playing(error):
                if error:
                    print(f"Error en reproducción: {error}")
                bot.loop.create_task(play_next(ctx, guild_id))

            ffmpeg_source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
            curr_vol = guild_volumes.get(guild_id, 0.7)
            volume_source = discord.PCMVolumeTransformer(ffmpeg_source, volume=curr_vol)

            voice_client.play(volume_source, after=after_playing)

        except Exception as e:
            print(f"Error al reproducir pista: {e}")
            await play_next(ctx, guild_id)
    else:
        if guild_id in now_playing_messages:
            try:
                await now_playing_messages[guild_id].delete()
            except Exception:
                pass
            now_playing_messages.pop(guild_id, None)
        current_tracks.pop(guild_id, None)

@bot.event
async def on_ready():
    print(f"\n========================================")
    print(f"Bot listo y conectado en Python como: {bot.user}")
    print(f"========================================\n")

@bot.command(name='play')
async def play(ctx, *, url_or_name: str):
    if not ctx.author.voice:
        return await ctx.send("❌ ¡Debes estar en un canal de voz!")

    voice_channel = ctx.author.voice.channel
    voice_client = ctx.guild.voice_client

    if not voice_client:
        voice_client = await voice_channel.connect(self_deaf=True)

    guild_id = ctx.guild.id
    if guild_id not in queues:
        queues[guild_id] = []
    if guild_id not in guild_volumes:
        guild_volumes[guild_id] = 0.7

    msg = await ctx.send("🔍 Procesando canción / playlist...")
    loop = asyncio.get_event_loop()

    if 'spotify.com' in url_or_name.lower():
        spotify_tracks = await loop.run_in_executor(None, lambda: parse_spotify(url_or_name))
        await msg.delete()

        if not spotify_tracks:
            return await ctx.send("❌ No se pudieron extraer canciones de ese enlace de Spotify.")

        for track_name in spotify_tracks:
            queues[guild_id].append({
                'title': track_name,
                'query': f"ytsearch:{track_name}",
                'requested_by': ctx.author.mention
            })

        confirm_msg = await ctx.send(f"🎶 **Spotify cargado:** {len(spotify_tracks)} canciones agregadas a la cola.")
        asyncio.create_task(delete_after(confirm_msg, 8))

    else:
        target_url = url_or_name
        opts = YTDL_OPTIONS.copy()
        if 'list=' in url_or_name:
            opts['noplaylist'] = False

        try:
            info = await loop.run_in_executor(
                None, lambda: yt_dlp.YoutubeDL(opts).extract_info(target_url, download=False)
            )
        except Exception as e:
            await msg.delete()
            return await ctx.send(f"❌ Error al procesar el enlace: {e}")

        await msg.delete()

        if 'entries' in info and info['entries']:
            entries = list(info['entries'])
            added_count = 0
            for entry in entries:
                if not entry:
                    continue
                title = entry.get('title', 'Canción')
                query = entry.get('url') or entry.get('webpage_url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                queues[guild_id].append({
                    'title': title,
                    'query': query,
                    'requested_by': ctx.author.mention
                })
                added_count += 1

            confirm_msg = await ctx.send(f"🎶 **Playlist / Mix de YouTube cargado:** {added_count} canciones agregadas a la cola.")
            asyncio.create_task(delete_after(confirm_msg, 8))
        else:
            title = info.get('title', url_or_name)
            query = info.get('webpage_url') or url_or_name
            queues[guild_id].append({
                'title': title,
                'query': query,
                'requested_by': ctx.author.mention
            })

            confirm_msg = await ctx.send(f"🎶 **Agregada a la cola:** {title}")
            asyncio.create_task(delete_after(confirm_msg, 8))

    if not voice_client.is_playing() and not voice_client.is_paused():
        await play_next(ctx, guild_id)

@bot.command(name='skip')
async def skip(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
        voice_client.stop()
        msg = await ctx.send("⏭️ Canción saltada.")
        asyncio.create_task(delete_after(msg, 5))
    else:
        await ctx.send("❌ No hay nada reproduciéndose.")

@bot.command(name='pause')
async def pause(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client:
        if voice_client.is_playing():
            voice_client.pause()
            msg = await ctx.send("⏸️ Reproducción pausada.")
            asyncio.create_task(delete_after(msg, 5))
        elif voice_client.is_paused():
            voice_client.resume()
            msg = await ctx.send("▶️ Reproducción reanudada.")
            asyncio.create_task(delete_after(msg, 5))

@bot.command(name='stop')
async def stop(ctx):
    guild_id = ctx.guild.id
    if guild_id in queues:
        queues[guild_id] = []
    
    voice_client = ctx.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        msg = await ctx.send("🛑 Bot desconectado del canal.")
        asyncio.create_task(delete_after(msg, 5))

async def delete_after(msg, seconds):
    await asyncio.sleep(seconds)
    try:
        await msg.delete()
    except Exception:
        pass

bot.run(TOKEN)
