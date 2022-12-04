import discord, json, re
from discord.ext import commands

# bot = discord.Client(intents=discord.Intents.all())

bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())

@bot.command()
async def hello(ctx):
    await ctx.send("Hello, world!")

@bot.event
async def on_message(message):
    
    if message.author == bot.user:
        return

    # Use a regular expression to remove any Discord ID from message.content.
    message_text = re.sub(r"<@\d+>\s*", "", message.content)
    
    print(f"{message.author.mention} sent {message_text}")

    if bot.user in message.mentions:
        print("Message inteded for bot")

    if bot.user in message.mentions:
        if ("hello" in message_text or "hi" in message_text):
            # Construct the response message.
            response = f"Hello {message.author.mention}! How are you doing?"
            await message.channel.send(response)
        else:
            await message.channel.send(f"Pardon? {message.author.mention}")
    else:
        await bot.process_commands(message)

# Open the file in read-only mode.
with open("bot_token.txt", "r") as f:

    # Read the contents of the file.
    bot_token = f.read().strip()

    # bot.run(bot_token)
    bot.run(bot_token)