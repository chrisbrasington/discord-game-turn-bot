#!/usr/bin/env python3
import asyncio, discord, json, os, random, re, signal
from discord.ext import commands
from datetime import datetime, time
import time as regular_time
from classes.gamestate import GameState, GameStateEncoder

# game state
state = None

# create bot with / commands
bot = commands.Bot(
    command_prefix="/", 
    case_insensitive=True, 
    intents=discord.Intents.all())

# initialize players file read
async def init():
    global bot, state
    state = GameState()

    if state.channel is None:
        print("Not is_listening on any channel")
    else:
        print(f"is_listening on {state.channel}")

    # shuffle game list (silent begin)
    await state.Shuffle()
    print("Silent Ready")

    for name in state.names:
        await state.ReadUser(bot, name)

    print(await state.Serialize())

# command hello
@bot.command(description="Display simple hello")
async def hello(ctx):
    await ctx.send("Hello, world!")

def is_listening(ctx):
    global state
    return str(ctx.channel) == state.channel

# command listen - sets game channel
@bot.command()
async def listen(ctx):
    global state
    state.channel = str(ctx.channel)
    print(f"/listen {state.channel}")
    await ctx.channel.send(f"Now is_listening on {ctx.channel}")
    await state.Save()

# command add player
@bot.command(description="Adds player to game")
async def add(ctx, names: str):
    global bot, state 
    if(not is_listening(ctx)):
        return

    if await state.Add(bot, names):
        await ctx.channel.send("Added Player")
        await state.DisplayConfig(ctx, bot)
    else:
        await ctx.channel.send(f"{name} already exists")

# command removes a player from the game
@bot.command()
async def remove(ctx, name: str):
    global state
    if(not is_listening(ctx)):
        return

    if await state.Remove(name):
        await ctx.channel.send(f"Removed {name}")
        await state.DisplayConfig(ctx, bot)
    else:
        await ctx.channel.send(f"{name} not found")

# command being
@bot.command(aliases=["go", "start", "random", "randomize"])
async def begin(ctx):
    global state
    await state.Begin(ctx)

# command next/skip
@bot.command(aliases=["skip"])
async def next(ctx):
    if(not is_listening(ctx)):
        return
    global state
    await state.Next(ctx)

# message alarm reminder for active player
# do not message at night-time
async def message_alarm(ctx, signal):

    if can_message_during_daytime():

        if alarm_interval != 0:
            if game_active:
                output = f"{game_list[index]} this is your alarm - it is your turn"  
                print(output)
                output += "\n\n"
                await ctx.channel.send(output)
                
                # reoccuring
                signal.alarm(alarm_interval)
            else:
                print("game inactive - ending alarm")
    else:
        print("Ignoring alarm, continuing...")

        if game_active:
            signal.alarm(alarm_interval)

# check if alarm can message because it is daytime?
def can_message_during_daytime():
    start_time = time(hour=10, minute=0)  # Create a time object for 10:00 AM.
    end_time = time(hour=22, minute=0)  # Create a time object for 10:00 PM.

    current_time = datetime.now().time()  # Get the current time as a time object.

    return start_time < current_time < end_time

# command end
@bot.command()
async def end(ctx):
    if(not is_listening(ctx)):
        return
    await end_game(ctx)

# set alarm
@bot.command()
async def alarm(ctx, new_alarm: str):
    global game_active
    global alarm_interval
    number = int(new_alarm)

    if number > 8:
        await ctx.channel.send("Yeah let's not go bigger than 8 hours. You can send 0 to disable")
        return

    if number == 0:
        await ctx.channel.send("Disabling alarm")
        alarm_interval = 0
    else:
        await ctx.channel.send(f"Setting alarm to {number} hour(s)")
        alarm_interval = 3600*number

        if game_active: 
            await ctx.channel.send(f"Congrats {ctx.author.mention}, you hit an edge case of changing the alarm mid-game. I will not start a new alarm until the next player in the game..")

# command print, status
@bot.command(name="print", aliases=["status", "who"])
async def print_game(ctx):
    global state
    await state.Display(ctx)
 
# end game without starting again
async def end_game(ctx):
    global state
    await state.End(ctx)

# command test
@bot.command()
async def config(ctx):
    global state
    await state.DisplayConfig(ctx, bot)

# command test - sets players to test players
@bot.command(name="gametest", aliases=["testmode", "goblinmode"])
async def gametest(ctx):
    global state
    await state.TestMode(True, bot)
    await state.ReadAllUsers(bot)
    await state.DisplayConfig(ctx, bot)

# command restart - can unload test to real players
@bot.command()
async def restart (ctx):
    global state
    state.ReadPlayers()

    await ctx.channel.send("Restarted")
    await state.ReadAllUsers(bot)
    await state.DisplayConfig(ctx, bot)

# bot on message to channel
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
    
    image_responding_channel = str(ctx.channel) == state.channel

    # Use a regular expression to remove any Discord ID from ctx.content.
    message_text = re.sub(r"<@\d+>\s*", "", ctx.content)
    
    # print(f"{ctx.author.mention} sent {message_text}")
    # print(image_responding_channel)
    # await print_simple(message)

    # message intended for bot
    if bot.user in ctx.mentions:
        print("Message intended for bot")

    # bot was mentioned
    if bot.user in ctx.mentions:
        # respond to hello
        if ("hello" in message_text or "hi" in message_text):
            # Construct the response ctx.
            response = f"Hello {ctx.author.mention}! How are you doing?"
            await ctx.channel.send(response)
        # not understood
        elif("right" in message_text):
            await ctx.channel.send("Fuck yeah {ctx.author.mention}")
        elif("why" in message_text or "what" in message_text):
            await ctx.channel.send("Sorry.. go ask chat.openai")
        elif("config" in message_text):
            await state.DisplayConfig(ctx, bot)
        else:
            await ctx.channel.send(f"{message_text}, you too {ctx.author.mention}.")

    # if active player responding
    if len(state.players) > 0:
        if(image_responding_channel and str(ctx.author.id) in state.players[state.index]):
            # print("Active player is responding")
            containsImage = False

            # image detection
            if ctx.attachments:
                for attachment in ctx.attachments:
                    # if attachment.is_image:
                    if attachment.filename.endswith((".png", ".jpg", ".gif")):
                        print("Progressing game")
                        containsImage = True

                        # progress
                        if(index == len(game_list)-1):
                            await state.End(ctx)
                            break
                        else:
                            await state.Next(ctx)
                            break
            # do not progress
            if not containsImage:
                print("Active player is chatting")

    if ctx.content.startswith('/'):
        print(f"{ctx.author} sent {message_text}")
        await bot.process_commands(message)

# Open the file in read-only mode.
with open("bot_token.txt", "r") as f:

    asyncio.run(init())

    # Read the contents of the file.
    bot_token = f.read().strip()

    # bot.run(bot_token)
    bot.run(bot_token)

