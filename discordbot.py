import discord, json, os, random, re
from discord.ext import commands

file_name = "names.json"

global name_list 
name_list = None

game_list = []

global index
index = 0

if os.path.exists(file_name):
    # Open the file in read mode
    with open(file_name, "r") as f:
        # Read the JSON string from the file
        json_string = f.read()

    # Convert the JSON string to a list of strings
    name_list = json.loads(json_string)

if name_list is None:
    name_list = []

bot = commands.Bot(command_prefix="/", case_insensitive=True, intents=discord.Intents.all())

@bot.command()
async def hello(ctx):
    await ctx.send("Hello, world!")

@bot.command(name="print")
async def print_command(ctx):
    print(str(name_list))
    await ctx.channel.send(str(name_list))

@bot.command()
async def add(ctx, names: str):

    for name in names.split(","):
        if(name != ''):
            name_list.append(name.strip())
    
    name_list.sort()

    await save()
    await print_command(ctx)

@bot.command()
async def clear(ctx):
    name_list.clear()
    print(name_list)
    os.remove(file_name)
    await ctx.channel.send("Cleared")

@bot.command()
async def begin(ctx):
    global index 
    index = 0

    global game_list 
    game_list = name_list.copy()
    random.shuffle(game_list)

    await(print_game(ctx))

@bot.command()
async def skip(ctx):
    await next(ctx)

@bot.command()
async def next(ctx):
    global index
    if(index+1 != len(game_list)):
        index += 1
        await print_game(ctx)
    else:
        await begin(ctx) 

async def print_game(ctx):
    output = ""

    if(index == 0):
        output = "New Game begin!\n"

    i = 0
    output += f"{game_list[i]} it's your turn!\n\n"

    for name in game_list:

        if i == index:
            output += "--> "
        else:
            output += "    "
        i += 1
        output += f"{name}\n"

    print(output)

    await ctx.channel.send(output)


async def save():
    print("Saving..")
    # Open the file in write mode
    with open(file_name, "w") as f:
        # Write the JSON string to the file      
        f.write(json.dumps(name_list))

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