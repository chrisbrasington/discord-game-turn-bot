#!/usr/bin/env python3
import asyncio, discord, json, os, random, re, signal, sys
from discord.ext import commands
from datetime import datetime, time
import time as regular_time
from classes.gamestate import GameState, GameStateEncoder
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
            with open("config.json") as config_file:
                config = json.load(config_file)

            guild = self.get_guild(config['guild_id'])

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

    guild_id = 0
    admin_id = 0
    bot_token = ""

    if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                data = json.load(f)
                guild_id = data['guild_id']
                admin_id = data['admin_id']
                bot_token = data['bot_token']

    guild = discord.Object(id=guild_id)

    # return bot, tree, guild, bot_token, state, admin_id

game_images = []
# bot, tree, guild, token, state, admin_id = setup()
asyncio.run(setup())

@tree.command(guild=guild, description='dance')
async def dance(interaction):
    await interaction.response.send_message("♪┏(・o・)┛♪┗ ( ・o・) ┓♪")

# check if context is the listening channel
def is_listening(ctx):
    global state
    return str(ctx.channel) == state.channel

@tree.command(guild=guild, description='Set listening to this channel')
async def listen(interaction):
    global state
    state.channel = str(interaction.channel)
    print(f"/listen {state.channel}")
    await interaction.response.send_message(f"Now is_listening on {interaction.channel}")
    await state.Save()

@tree.command(guild=guild, description="Adds player to game. If game is active, goes to end of list")
async def add(interaction, name: str):
    global bot, state, game_images, guild
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
    global bot, state, game_images, guild
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
    global state, game_images
    # reset game images in memory
    game_images = []
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
    global state, game_images
    await interaction.response.send_message("Skipping player")
    await state.Next(interaction, bot, game_images)

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

@tree.command(guild=guild, description="Shows configuration of bot")
async def config(interaction):
    global state, game_images
    await interaction.response.send_message("Current configuration")
    await state.DisplayConfig(interaction, bot, guild, game_images)

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

# on message sent to channel
@bot.event
async def on_message(ctx):
    global state, game_images

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
    
    image_responding_channel = str(ctx.channel) == state.channel

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
                await state.DisplayConfig(ctx, bot, game_images)
            else:
                await ctx.channel.send(f"{message_text}, you too {ctx.author.mention}.")

    # if active player responding
    if len(state.players) > 0:
        if(image_responding_channel and str(ctx.author.id) in state.players[state.index]):
            # print("Active player is responding")
            containsImage = False

            # image detection
            if ctx.attachments:

                attachment_url = ctx.attachments[0].url

                name = ctx.author.name

                if ctx.author.nick is not None and ctx.author.nick != 'None':
                    name = ctx.author.nick

                game_images.append((name, attachment_url))

                print('recorded progress: ')
                print(game_images)
     
                for attachment in ctx.attachments:
                    # if attachment.is_image:
                    if attachment.filename.endswith((".png", ".jpg", ".gif", ".webp")):
                        print("Progressing game")
                        containsImage = True

                        # progress
                        if(state.index == len(state.players)-1):
                            await state.End(ctx, bot, game_images)
                            game_images = []
                            break
                        else:
                            await state.Next(ctx, bot, game_images)
                            break
            # do not progress
            if not containsImage:
                print("Active player is chatting")

    if ctx.content.startswith('/'):
        if not ctx.content.startswith('/secret'):
            print(f"{ctx.author} sent {message_text}")
        await bot.process_commands(ctx)

bot.run(bot_token)