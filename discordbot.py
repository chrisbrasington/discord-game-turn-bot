#!/usr/bin/env python3
import asyncio, discord, json, os, random, re, signal, sys, io
from typing import Optional
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
from discord.ext import commands
from datetime import datetime, time
import time as regular_time
from classes.gamestate import GameState, GameStateEncoder, post_results, refresh_game_image_urls
from discord import app_commands

# Configure Discord bot
class bot_client(discord.Client):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(intents=intents)
        self.synced = False

    async def on_ready(self):
        print(f'Logged in as {self.user.name}')

        await self.wait_until_ready()
        if not self.synced:
            guild = self.get_guild(int(os.environ['GUILD_ID']))

            print(f'Syncing commands to {guild.name}...')

            await tree.sync(guild=guild)

        print('Reading usernames...')
        await state.ReadAllUsers(bot, guild)

        if(state.active):
            print(f'Ready. Current player ({state.index}): {state.mapping[state.players[state.index]]} {state.players[state.index]}')
            await state.Status_Listening(bot, state.players[state.index])
        else:
            print('Ready, no game active')
            await state.Status_Watching(bot, "for /begin")

        commands = await tree.fetch_commands(guild=guild)

        for command in commands:
            print(f'Command: {command.name}')

        print('Ready')

async def setup():
    global bot, tree, guild, bot_token, state, admin_id

    bot = bot_client()
    tree = app_commands.CommandTree(bot)

    state = GameState()

    if os.path.exists('gamestate.json'):
        with open('gamestate.json', 'r') as f:
            data = json.load(f)
            state = GameState(**data)
            print('Prior State Loaded from file')
    else:
        print('No prior state')

    # print seralized state
    print(await state.Serialize())

    if state.channel is None:
        print("Not is_listening on any channel")
    else:
        print(f"is_listening on {state.channel}")

    guild_id = int(os.environ['GUILD_ID'])
    admin_id = int(os.environ['ADMIN_ID'])
    bot_token = os.environ['DISCORD_TOKEN']

    guild = discord.Object(id=guild_id)

    # return bot, tree, guild, bot_token, state, admin_id

# bot, tree, guild, token, state, admin_id = setup()
asyncio.run(setup())

@tree.command(guild=guild, description='dance')
async def dance(interaction):
    await interaction.response.send_message("♪┏(・o・)┛♪┗ ( ・o・) ┓♪")

# check if context is the listening channel
def is_listening(ctx):
    global state
    return ctx.channel.id == state.channel

@tree.command(guild=guild, description='Set listening to this channel')
async def listen(interaction):
    global state
    state.channel = interaction.channel.id
    print(f"/listen {state.channel}")
    await interaction.response.send_message(f"Now is_listening on {interaction.channel}")
    await state.Save()

@tree.command(guild=guild, description="Adds player to game. If game is active, goes to end of list")
async def add(interaction, name: str):
    global bot, state, guild
    if(not is_listening(interaction)):
        return

    actual_guild = bot.get_guild(guild.id)
    # print(actual_guild)

    name_check = name.replace('<','').replace('>','').replace('@','')
    if name_check == str(bot.user.id):
        await interaction.response.send_message("No thanks, I run the game. I'm not smart enough to play it... yet.")
    else:
        user_alias = await state.GetAlias(bot, name, actual_guild)  
        print('~~')
        print(user_alias)
        if await state.Add(bot, name, actual_guild):
            await interaction.response.send_message(f"Added {user_alias if user_alias else 'Player'} to the game.")
            # await state.DisplayConfig(interaction, bot, game_images)
        else:
            await interaction.response.send_message(f'{user_alias if user_alias else "Player"} is already in the game.')

@tree.command(guild=guild, description="Removes player from game")
async def remove(interaction, name: str):
    global bot, state, guild
    if(not is_listening(interaction)):
        return
    
    actual_guild = bot.get_guild(guild.id)

    if await state.Remove(name):
        await interaction.response.send_message(f"Removed {name}")
    else:
        await interaction.response.send_message(f"{name} not found")


@tree.command(guild=guild, description="Shuffles and starts new game")
async def begin(interaction):
    if(not is_listening(interaction)):
        return
    global state
    state.game_images = []
    await interaction.response.send_message("Starting new game")
    await state.Begin(interaction, bot)


# @tree.command(guild=guild, description="End game")
# async def end(interaction):
#     if(not is_listening(interaction)):
#         return
#     global state, game_images
#     await interaction.response.send_message("Ending game")
#     await state.End(interaction, bot, game_images)
#     game_images = []

@tree.command(guild=guild, description="Optionally skip over the current player.")
async def skip(interaction):
    if(not is_listening(interaction)):
        return
    global state
    await interaction.response.send_message("Skipping player")
    await state.Next(interaction, bot, state.game_images)

@tree.command(guild=guild, description="Prints current game status", name="print")
async def print_game(interaction):
    global state
    await interaction.response.send_message("Current game:")
    await state.Display(interaction)

@tree.command(guild=guild, description="Toggles if @ messaging is used during turns")
async def silent(interaction):
    global state
    state.silent = not state.silent
    await interaction.response.send_message(f"Silent: {state.silent}")
    await state.Save()

_bother_flip = False

@tree.command(guild=guild, description="Bother the active player")
async def bother(interaction):
    global state, _bother_flip
    if not state.active or not state.players:
        await interaction.response.send_message("No game in progress.", ephemeral=True)
        return
    player = state.players[state.index]
    if _bother_flip:
        msg = f"{player} bother, bother!"
    else:
        msg = f"{player} it's your turn!"
    _bother_flip = not _bother_flip
    await interaction.response.send_message(msg)

@tree.command(guild=guild, description="Shows configuration of bot")
async def config(interaction):
    global state
    await interaction.response.send_message("Current configuration")
    await state.DisplayConfig(interaction, bot, guild, state.game_images)
    await state.Display(interaction, force_silent=True)

async def _send_lines(channel, lines):
    chunk, length = [], 0
    for line in lines:
        if length + len(line) + 1 > 1900:
            await channel.send("\n".join(chunk))
            chunk, length = [], 0
        chunk.append(line)
        length += len(line) + 1
    if chunk:
        await channel.send("\n".join(chunk))

MAX_GIF_BYTES = 8 * 1024 * 1024

# --- shared GIF helpers ---

def _gif_fit(img, size):
    img = img.convert("RGBA")
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    img.thumbnail((size, size), Image.LANCZOS)
    x = (size - img.width) // 2
    y = (size - img.height) // 2
    canvas.paste(img, (x, y), img)
    return canvas

def _gif_label(img, name, size):
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=22)
    except TypeError:
        font = ImageFont.load_default()
    pad = 6
    bbox = draw.textbbox((0, 0), name, font=font)
    text_h = bbox[3] - bbox[1]
    bar_top = size - text_h - pad * 2
    draw.rectangle([(0, bar_top), (size, size)], fill=(0, 0, 0, 180))
    draw.text((pad, bar_top + pad), name, font=font, fill=(255, 255, 255, 255))
    return img

async def _gif_download_all(game_images):
    async def fetch(session, url):
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
            if r.status != 200:
                raise ValueError(f"Image URL returned HTTP {r.status}: {url}")
            return await r.read()
    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(*[fetch(session, entry[1]) for entry in game_images])

def _gif_save(frames, durations):
    buf = io.BytesIO()
    frames[0].save(buf, format="WEBP", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, quality=85)
    buf.seek(0)
    return buf

# --- transition blend functions ---
# Each takes two RGBA PIL images and returns (frames, durations) for the transition only.

def _blend_fade(img_a, img_b, n, size):
    frames, durations = [], []
    for f in range(1, n + 1):
        t = f / (n + 1)
        frames.append(Image.blend(img_a, img_b, t).convert("RGB"))
        durations.append(60)
    return frames, durations

def _blend_zoom(img_a, img_b, n, size):
    # Zoom into A until fully zoomed, then zoom out from B to normal
    frames, durations = [], []
    a_rgb, b_rgb = img_a.convert("RGB"), img_b.convert("RGB")
    for f in range(1, n + 1):
        t = f / (n + 1)
        if t <= 0.5:
            zoom = 1 + (t / 0.5) * 0.4
            src = a_rgb
        else:
            zoom = 1 + ((1 - t) / 0.5) * 0.4
            src = b_rgb
        w = h = int(size * zoom)
        scaled = src.resize((w, h), Image.LANCZOS)
        x, y = (w - size) // 2, (h - size) // 2
        frames.append(scaled.crop((x, y, x + size, y + size)))
        durations.append(60)
    return frames, durations

def _blend_wipe(img_a, img_b, n, size):
    frames, durations = [], []
    a_rgb, b_rgb = img_a.convert("RGB"), img_b.convert("RGB")
    for f in range(1, n + 1):
        t = f / (n + 1)
        cut = int(t * size)
        frame = a_rgb.copy()
        if cut > 0:
            frame.paste(b_rgb.crop((0, 0, cut, size)), (0, 0))
        frames.append(frame)
        durations.append(60)
    return frames, durations

def _blend_pixel(img_a, img_b, n, size):
    MAX_BLOCK = 16
    def pixelate(img, block):
        s = max(1, size // block)
        return img.resize((s, s), Image.NEAREST).resize((size, size), Image.NEAREST)
    frames, durations = [], []
    a_rgb, b_rgb = img_a.convert("RGB"), img_b.convert("RGB")
    for f in range(1, n + 1):
        t = f / (n + 1)
        if t <= 0.5:
            block = max(2, int(MAX_BLOCK * (t / 0.5)))
            frames.append(pixelate(a_rgb, block))
        else:
            block = max(2, int(MAX_BLOCK * ((1 - t) / 0.5)))
            frames.append(pixelate(b_rgb, block))
        durations.append(60)
    return frames, durations

def _blend_zoom_fade(img_a, img_b, n, size):
    # Gentle zoom on A while crossfading to B
    frames, durations = [], []
    a_rgb = img_a.convert("RGB")
    for f in range(1, n + 1):
        t = f / (n + 1)
        zoom = 1 + t * 0.15
        w = h = int(size * zoom)
        scaled = a_rgb.resize((w, h), Image.LANCZOS)
        x, y = (w - size) // 2, (h - size) // 2
        cropped = scaled.crop((x, y, x + size, y + size)).convert("RGBA")
        frames.append(Image.blend(cropped, img_b, t).convert("RGB"))
        durations.append(60)
    return frames, durations

_TRANSITIONS = {
    'fade':      _blend_fade,
    'zoom':      _blend_zoom,
    'wipe':      _blend_wipe,
    'pixel':     _blend_pixel,
    'zoom+fade': _blend_zoom_fade,
}

# --- GIF generation ---

async def _make_gif(game_images, style='fade'):
    if style == 'morph':
        return await _make_morph_gif(game_images)
    buf = await _generate_gif(game_images, style=style)
    if buf.getbuffer().nbytes > MAX_GIF_BYTES:
        print(f"{style} GIF too large, retrying at 320px")
        buf = await _generate_gif(game_images, style=style, size=320)
    return buf

async def _generate_gif(game_images, style='fade', size=480):
    HOLD_FRAMES, HOLD_MS = 5, 150
    BLEND_N = 10

    raw = await _gif_download_all(game_images)
    images = [_gif_label(_gif_fit(Image.open(io.BytesIO(d)), size), e[0], size)
              for e, d in zip(game_images, raw)]

    blend_fn = _TRANSITIONS.get(style, _blend_fade)
    frames, durations = [], []
    for i, img in enumerate(images):
        for _ in range(HOLD_FRAMES):
            frames.append(img.convert("RGB"))
            durations.append(HOLD_MS)
        if i < len(images) - 1:
            bf, bd = blend_fn(img, images[i + 1], BLEND_N, size)
            frames.extend(bf)
            durations.extend(bd)

    buf = _gif_save(frames, durations)
    print(f"GIF ({style}): {buf.getbuffer().nbytes / 1024 / 1024:.2f} MB")
    return buf

# --- morph GIF (optical flow) ---

async def _make_morph_gif(game_images):
    buf = await _generate_morph_gif(game_images)
    if buf.getbuffer().nbytes > MAX_GIF_BYTES:
        print("Morph GIF too large, retrying at 320px")
        buf = await _generate_morph_gif(game_images, size=320)
    return buf

async def _generate_morph_gif(game_images, size=480):
    HOLD_FRAMES, HOLD_MS = 5, 150
    BLEND_FRAMES, BLEND_MS = 12, 50

    raw = await _gif_download_all(game_images)
    pil_images = [_gif_label(_gif_fit(Image.open(io.BytesIO(d)), size), e[0], size)
                  for e, d in zip(game_images, raw)]
    cv_images = [np.array(img.convert("RGB")) for img in pil_images]

    frames, durations = [], []
    h, w = size, size
    grid_x, grid_y = np.meshgrid(np.arange(w, dtype=np.float32),
                                  np.arange(h, dtype=np.float32))

    for i, (pil_a, cv_a) in enumerate(zip(pil_images, cv_images)):
        for _ in range(HOLD_FRAMES):
            frames.append(pil_a.convert("RGB"))
            durations.append(HOLD_MS)

        if i < len(pil_images) - 1:
            cv_b = cv_images[i + 1]
            pil_b = pil_images[i + 1]

            gray_a = cv2.cvtColor(cv_a, cv2.COLOR_RGB2GRAY)
            gray_b = cv2.cvtColor(cv_b, cv2.COLOR_RGB2GRAY)
            flow = cv2.calcOpticalFlowFarneback(
                gray_a, gray_b, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0
            )

            for f in range(1, BLEND_FRAMES + 1):
                t = f / (BLEND_FRAMES + 1)
                map_xa = (grid_x + t * flow[:, :, 0]).astype(np.float32)
                map_ya = (grid_y + t * flow[:, :, 1]).astype(np.float32)
                map_xb = (grid_x - (1 - t) * flow[:, :, 0]).astype(np.float32)
                map_yb = (grid_y - (1 - t) * flow[:, :, 1]).astype(np.float32)
                warped_a = cv2.remap(cv_a, map_xa, map_ya, cv2.INTER_LINEAR)
                warped_b = cv2.remap(cv_b, map_xb, map_yb, cv2.INTER_LINEAR)
                blended = cv2.addWeighted(warped_a, 1 - t, warped_b, t, 0)
                frames.append(Image.fromarray(blended))
                durations.append(BLEND_MS)

    for _ in range(HOLD_FRAMES):
        frames.append(pil_images[-1].convert("RGB"))
        durations.append(HOLD_MS)

    buf = _gif_save(frames, durations)
    print(f"Morph GIF: {buf.getbuffer().nbytes / 1024 / 1024:.2f} MB")
    return buf

@tree.command(guild=guild, description="Show game progress so far: guesses and GIF")
async def test(interaction):
    global state
    if not state.game_images:
        await interaction.response.send_message("No images recorded yet.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)

    state.game_images = await refresh_game_image_urls(bot, state.game_images)
    await state.Save()
    gif_task = asyncio.create_task(_make_gif(state.game_images))
    await post_results(interaction.channel, state.game_images, gif_task)
    await interaction.followup.send("done", ephemeral=True)

@tree.command(guild=guild, description="Generate an animated GIF of all recorded game images")
@app_commands.choices(style=[
    app_commands.Choice(name='Fade',         value='fade'),
    app_commands.Choice(name='Zoom',         value='zoom'),
    app_commands.Choice(name='Wipe',         value='wipe'),
    app_commands.Choice(name='Pixel Dissolve', value='pixel'),
    app_commands.Choice(name='Zoom + Fade',  value='zoom+fade'),
    app_commands.Choice(name='Morph (optical flow)', value='morph'),
])
async def gif(interaction, style: Optional[app_commands.Choice[str]] = None):
    global state
    if not state.game_images:
        await interaction.response.send_message("No images recorded yet.", ephemeral=True)
        return
    style_val = style.value if style else 'fade'
    await interaction.response.defer(ephemeral=True)
    try:
        gif_buf = await _make_gif(state.game_images, style=style_val)
    except (ValueError, Exception) as e:
        await interaction.followup.send(f"GIF failed: {e}", ephemeral=True)
        return
    gif_buf.seek(0)
    await interaction.channel.send(file=discord.File(gif_buf, filename="telephone.webp"))
    await interaction.followup.send("done", ephemeral=True)

@tree.command(guild=guild, description="No you can't run this")
async def talk(interaction, channel: str, message: str):
    global admin_id, bot, guild, state

    actual_guild = bot.get_guild(guild.id)

    if interaction.user.id == admin_id:
        print('Neurons firing..')

        channel_id = int(channel.replace('<#','').replace('>',''))

        print(channel_id)
    
        channel = actual_guild.get_channel(channel_id)

        if channel is not None:
            sending_message_text = message
            print(f'{channel.name}: {sending_message_text}')

            await channel.send(sending_message_text)

            # if interaction.message.attachments:
            #     print('sending attachments')
            #     for attachment in interaction.message.attachments:
            #         await channel.send(attachment.url)
        else:
            print('channel not found')

    else:
        print('Non admin is using secret command, ignoring')

@tree.command(guild=guild, description="No you can't run this")
async def delete(interaction, message_id: str):
    global admin_id, bot
    if interaction.user.id != admin_id:
        await interaction.response.send_message("no", ephemeral=True)
        return
    try:
        message = await interaction.channel.fetch_message(int(message_id))
        if message.author == bot.user:
            await message.delete()
            await interaction.response.send_message("Deleted", ephemeral=True)
        else:
            await interaction.response.send_message("That's not my message", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("Message not found", ephemeral=True)

@tree.command(guild=guild, description="No you can't run this")
async def accept(interaction, url: str, guess: str = ""):
    global admin_id, bot, state
    if interaction.user.id != admin_id:
        await interaction.response.send_message("no", ephemeral=True)
        return
    if not re.search(r'https?://\S+\.(?:png|jpg|webp)(?:\?\S*)?', url, re.IGNORECASE):
        await interaction.response.send_message("Not a valid image URL (.png/.jpg/.webp)", ephemeral=True)
        return

    current = state.players[state.index]
    member = state.mapping.get(current)
    if member and hasattr(member, 'nick') and member.nick and member.nick != 'None':
        name = member.nick
    elif member and hasattr(member, 'name'):
        name = member.name
    else:
        name = current

    await interaction.response.send_message(f"Image found for {name}: {url}")
    if 'cdn.discordapp.com' not in url:
        await interaction.channel.send(url)

    state.game_images.append((name, url, guess))
    await state.Save()

    if state.index == len(state.players) - 1:
        gif_task = asyncio.create_task(_make_gif(state.game_images))
        await state.End(interaction, bot, state.game_images, gif_task=gif_task)
        state.game_images = []
        await state.Save()
    else:
        await state.Next(interaction, bot, state.game_images)

# on message sent to channel
@bot.event
async def on_message(ctx):
    global state

    if ctx.author == bot.user:
        return

    if(ctx.channel.type == discord.ChannelType.private):
        await ctx.channel.send(f"Why are you DM-ing me {ctx.author.mention}? ya weirdo.")
        await ctx.channel.send("Play games with me in your discord channel, check out the readme at https://github.com/chrisbrasington/discord-game-turn-bot")
        print(f"{ctx.author.mention} send a dm, replying and ignoring")
        return

    # might be missing due to game state loading
    if(state.mapping == {}):
        print('Reading all users first time')
        await ctx.channel.send('Reading usernames first time... one moment please...')

        await state.ReadAllUsers(bot, ctx.guild)
    
    image_responding_channel = ctx.channel.id == state.channel

    # Use a regular expression to remove any Discord ID from ctx.content.
    message_text = re.sub(r"<@\d+>\s*", "", ctx.content)
    message_text = message_text.lower()
    
    # print(f"{ctx.author.mention} sent {message_text}")
    # print(image_responding_channel)
    # await print_simple(message)

    # message intended for bot
    try:
        if bot.user in ctx.mentions:
            print("Message intended for bot")
            if '/secret/' not in message_text:
                print(f"Mentioned: {state.mapping[ctx.author.mention]} sent {message_text}")
    except Exception as e:
        print(f"An error occurred: {e}")

    # bot was mentioned
    if bot.user in ctx.mentions:
        # ignore commands
        if not message_text.startswith('/'):
            # respond to hello
            if ("hello" in message_text or "hi" in message_text):
                # Construct the response ctx.
                response = f"Hello {ctx.author.mention}! How are you doing?"
                await ctx.channel.send(response)
            elif("thank" in message_text):
                await ctx.channel.send(f"You're welcome {ctx.author.mention}.")
            elif("right" in message_text):
                await ctx.channel.send(f"Fuck yeah {ctx.author.mention}")
            elif("why" in message_text or "what" in message_text):
                await ctx.channel.send("Sorry.. go ask chat.openai")
            elif("nice moves" in message_text or "dance" in message_text):
                await ctx.channel.send("♪┏(・o・)┛♪┗ ( ・o・) ┓♪")
            elif("config" in message_text):
                await state.DisplayConfig(ctx, bot, state.game_images)
            else:
                await ctx.channel.send(f"{message_text}, you too {ctx.author.mention}.")

    # if active player responding
    if len(state.players) > 0:
        if(image_responding_channel and str(ctx.author.id) in state.players[state.index]):
            # print("Active player is responding")
            containsImage = False

            name = ctx.author.name
            if ctx.author.nick is not None and ctx.author.nick != 'None':
                name = ctx.author.nick

            image_url = None

            # check file attachments
            if ctx.attachments:
                for attachment in ctx.attachments:
                    if attachment.filename.endswith((".png", ".jpg", ".webp")):
                        image_url = attachment.url
                        break

            # check for a raw image url posted as text
            if not image_url:
                url_match = re.search(r'https?://\S+\.(?:png|jpg|webp)(?:\?\S*)?', ctx.content, re.IGNORECASE)
                if url_match:
                    image_url = url_match.group(0)

            if image_url:
                # Extract guess text: unwrap spoilers, strip URL and mentions
                guess = re.sub(r"<@\d+>\s*", "", ctx.content)
                guess = re.sub(r'\|\|(.+?)\|\|', r'\1', guess, flags=re.DOTALL)
                if not ctx.attachments:
                    guess = guess.replace(image_url, "")
                guess = guess.strip(" -–—\n\t")

                # If no text in this message, check the previous message from this player
                if not guess:
                    async for prev in ctx.channel.history(limit=10, before=ctx):
                        if prev.author.id == ctx.author.id:
                            prev_text = re.sub(r"<@\d+>\s*", "", prev.content)
                            prev_text = re.sub(r'\|\|(.+?)\|\|', r'\1', prev_text, flags=re.DOTALL)
                            prev_text = prev_text.strip()
                            if prev_text:
                                guess = prev_text
                                break

                state.game_images.append((name, image_url, guess))
                await state.Save()
                print('recorded progress: ')
                print(state.game_images)
                print("Progressing game")
                containsImage = True

                if(state.index == len(state.players)-1):
                    gif_task = asyncio.create_task(_make_gif(state.game_images))
                    await state.End(ctx, bot, state.game_images, gif_task=gif_task)
                    state.game_images = []
                    await state.Save()
                else:
                    await state.Next(ctx, bot, state.game_images)

            # do not progress
            if not containsImage:
                print("Active player is chatting")

    if ctx.content.startswith('/'):
        if not ctx.content.startswith('/secret'):
            print(f"{ctx.author} sent {message_text}")
        await bot.process_commands(ctx)

bot.run(bot_token)