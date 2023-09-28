import asyncio, discord, json, os, random, signal
from datetime import datetime, time

class GameState:
    game_state_file = 'gamestate.json'
    player_file = 'players.json'
    test_file = 'test.json'
    channel = None
    SECONDS_PER_HOUR = 3600

    # initialize game state with default values
    # read players from file if exists
    # reading game state from file should be done by deserization
    # at constructor of GameState object outside of this class
    def __init__(self, active=False, alarm_hours=0, channel='🤖bot-commands', index=0, 
        is_test=False, names=[], players=[], silent = False):

        self.active = active
        self.silent = silent
        self.names = names
        self.players = players
        self.mapping = {} # not serializable, will recreate
        self.alarm_hours = alarm_hours
        self.is_test = is_test
        self.index = index
        self.channel = channel 
        self.ReadPlayerFile(self.player_file, False)

    # add player to names and game
    async def Add(self, bot, new_name: str, guild):
        print("add command:")

        for single_name in new_name.split(","):
            if(single_name != ''):
                if(single_name in self.names):
                    # await ctx.channel.send(f"{name} already exists")
                    return False
                else:
                    single_name = single_name.strip()
                    self.names.append(single_name)
                    self.players.append(single_name)

                    await self.ReadUser(bot, single_name, guild)

                    await self.Save()
                    return True

    # alert alarm and continue alarm
    async def AlarmAlert(self, ctx, signal):
        print('Alarm sounding!')
        if self.CanMessageDuringDaytime():
            if self.alarm_hours > 0:
                if self.active:
                    output = f"{self.players[self.index]} this is your alarm - it is your turn"  
                    print(output)
                    output += "\n\n"
                    await ctx.channel.send(output)
                else:
                    print("game inactive - ending alarm")
        else:
                print("Ignoring alarm, continuing...")

        if self.active and self.alarm_hours > 0:
            print('Restarting alarm...')
            signal.signal(signal.SIGALRM, lambda signum, frame: 
                asyncio.create_task(self.AlarmAlert(ctx, signal))
            )
            print(f'resetting - alarming in {self.alarm_hours} hour(s)')
            signal.alarm(self.alarm_hours*self.SECONDS_PER_HOUR)

    # begin game by shuffling players and setting index to 0 and active state to True
    async def Begin(self, ctx, bot):
        # safer
        if self.mapping == {}:
            await self.ReadAllUsers(bot)
        self.index = 0

        print('Starting game...')
        await self.Shuffle()
        self.active = True
        await self.Display(ctx)
        await self.Save()
        await self.Status_Listening(bot, self.players[self.index])

    # can message during day - checks if alarm alert should occur or not
    def CanMessageDuringDaytime(self):
        start_time = time(hour=10, minute=0)  # Create a time object for 10:00 AM.
        end_time = time(hour=22, minute=0)  # Create a time object for 10:00 PM.

        current_time = datetime.now().time()  # Get the current time as a time object.

        return start_time < current_time < end_time  

    # display overall state of game
    async def Display(self, ctx):
        print('Printing game...')
        # do not advance to new game here
        if not self.active:
            output = "Game is not active. Start with /begin"
            print(output)
            await ctx.channel.send(output)
            return

        alarm_text = 'Alarm is disabled'
        if self.alarm_hours > 0 :
            # set alarm reminder for active player
            alarm_text = f"setting alarm to {self.alarm_hours} hour(s)"
            print(alarm_text)
            signal.signal(signal.SIGALRM, lambda signum, frame: 
                asyncio.create_task(self.AlarmAlert(ctx, signal))
            )
            print(f'alarming in {self.alarm_hours} hour(s)')
            signal.alarm(self.alarm_hours*self.SECONDS_PER_HOUR)

        # no players to start
        if(len(self.players) == 0):
            await ctx.channel.send("Add players first with /add @\{name\} command")
            return
        
        # account for player removal mid-game
        if(self.index > len(self.players)-1):
            self.index = len(self.players)-1

        output = ""

        # new game
        if(self.index == 0):
            output = "New Game begin!\n"

        avatar = None

        # current turn
        if self.silent:
            output += 'New player turn!\n\n'
        else:
            output += f"{self.players[self.index]} it's your turn!\n\n"

        if '@' in self.players[self.index]:
            user = self.mapping[self.players[self.index]]
            print(f'Current player:{user.nick}')
            avatar = user.avatar
            # print(avatar)

        # all players
        i = 0
        for name in self.players:
            if i == self.index:
                output += "--> "
            else:
                output += "    "
            i += 1

            if '@' in name:
                member = self.mapping[name]
                output += f'{member.nick}\n'

            else: 
                output += f"{name}\n"

        print(output)

        message = discord.Embed(
            title= '',
            description='[Generate image on craiyon](<https://www.craiyon.com/>)\n[Generate image on stable-diffusion](<https://huggingface.co/spaces/stabilityai/stable-diffusion>)'
        )
        # message.set_image(url=avatar)
        message.set_thumbnail(url=avatar)

        await ctx.channel.send(output, embed=message)

    # display configuration of active game state
    async def DisplayConfig(self, ctx, bot):

        print(await self.Serialize())

        if self.channel is None:
            output = 'Not listening to any channel'
        else:
            output = f'Listening on {self.channel}'
        if self.is_test:
            output += '\nTEST MODE ON'
        if self.active:
            output += '\nGame is active'
        else:
            output += '\nGame is not active'
        if self.silent:
            output += '\nGame is silent (no @ s)'
        output += f'\nIndex is {self.index}'
        if self.alarm_hours != 0:
            output += f'\nAlarm is set to  {self.alarm_hours}'

        await ctx.channel.send(output)

        if self.mapping == {}:
            await ctx.channel.send('Reading usernames into cache... one moment please...')
            guild = bot.get_guild(guild_id)
            for name in self.names:
                await self.ReadUser(bot, name, guild)

        await ctx.channel.send("Known players:")
        await ctx.channel.send(await self.PrintSimple(True))
        await ctx.channel.send("Game order:")
        await ctx.channel.send(await self.PrintSimple(False))

    # end current game
    async def End(self, ctx, bot, game_images):
        self.active = False
        print('Ending game...')
        if self.silent:
            await ctx.channel.send(f"Game over!")
        else:
            await ctx.channel.send(f"Game over! Congratulations {self.players[self.index]}!")

        await ctx.channel.send('Here\'s the result of the game:')

        i = 1
        # print all the game progression of images
        for player_name, image_url in game_images:

            hyperlink = f" [- link]({image_url})"
            print(hyperlink)
            await ctx.channel.send(f'{i} - {player_name}{hyperlink}')
            i+=1

        # reset game images in memory
        game_images = []

        await ctx.channel.send('Game over! Start with /begin')

        self.index = 0
        await self.Save()

        if bot is not None:
            await self.Status_Watching(bot, "for /begin")

    # next will manually progress game to next player, may result in end of game
    async def Next(self, ctx, bot):
        if(self.index != len(self.players)-1):
            self.index += 1
            await self.Save()
            await self.Display(ctx)
            await self.Status_Listening(bot, self.players[self.index])
        else:
            if(self.active):
                await self.End(ctx)
                await self.Status_Watching(bot, "for /begin")
            else:
                await self.Begin(ctx, bot) 
                # set status in begin

    # print simple names known
    async def PrintSimple(self, game = False):
        output_list = []
        if game:
            for name in self.names:
                user = self.mapping[name]
                if name == user:
                    output_list.append(name)
                else:
                    output_list.append(f'{user.name}#{user.discriminator}')
        else:
            for name in self.players:
                user = self.mapping[name]
                if name == user:
                    output_list.append(name)
                else:
                    output_list.append(f'{user.name}#{user.discriminator}')
        print(output_list)
        return output_list

    # read game state from file if exists
    # only copy players if not loading prior game state from disk
    # such as a restart or test-mode commands
    def ReadPlayerFile(self, file, copy_players = True):
        print(f'Reading Players File: {file}')
        # read from file
        if os.path.exists(file):
        # Open the file in read mode
            with open(file, 'r') as f:
                # Read the JSON string from the file
                json_string = f.read()

            print(json_string)

            # Convert the JSON string to a list of strings
            self.names = json.loads(json_string)

            if copy_players:
                self.players = self.names.copy()

    # read all names (discord IDs) as discord usernames
    # slow, so done once and cached
    async def ReadAllUsers(self, bot, guild):
        for name in self.names:
            await self.ReadUser(bot, name, guild)

    # read individual name (discord ID) as discord username
    async def ReadUser(self, bot, name: str, guild):

        print('user: ' + name + ' in guild ' + str(guild.name))

        if '@' in name:
            id = int(name.replace('<', '').replace('@', '').replace('>', ''))
            user = await bot.fetch_user(id)
            member = await guild.fetch_member(id)

            if member is None:
                print(user.name + ' no alias')
                self.mapping[name] = user.name
            else:
                print(user.name + ' as ' + member.nick)
                self.mapping[name] = member

        else:
            self.mapping[name] = name

        print(f"read: {self.mapping[name]}")
        return self.mapping[name]

    # remove player from names and game list
    async def Remove(self, name: str):
        print(f'Removing {name}')
        removed = False
        if name in self.names:
            self.names.remove(name)
            removed = True
        if name in self.players:
            self.players.remove(name)
            removed = True
        
        await self.Save()
        return removed

    # restart will bring out of test mode and freshly load player list for game setup
    async def Restart(self, bot):
        await self.TestMode(False, bot)

    # save both players and gamestate to file
    async def Save(self):
        if self.is_test:
            print('Save, skipping in test mode')
            return
        print('Saving...')

        with open(self.player_file, "w") as f:
            # Write the JSON string to the file      
            f.write(json.dumps(self.names))
        
        with open(self.game_state_file, "w") as f:
            # Write the JSON string to the file      
            f.write(json.dumps(self, cls=GameStateEncoder, indent=4, sort_keys=True))

    # serialize game state
    async def Serialize(self):
        return json.dumps(self, cls=GameStateEncoder, indent=4, sort_keys=True)

    # shuffle game list generaed from known names list. mapping used in display
    async def Shuffle(self):
        self.players = self.names.copy()
        random.shuffle(self.players)
        print('Shuffling...')
        await self.Save()

    async def Status_Listening(self, bot, status: str):
        if self.active:
            user = self.mapping[self.players[self.index]]
            username = user
            if hasattr(user, "name"):
                username = user.name
            activity = discord.Activity(type=discord.ActivityType.listening, name=username)
            await bot.change_presence(status=discord.Status.online, activity=activity)
        else:
            await state.Status_Watching(bot, "for /begin")

    async def Status_Watching(self, bot, status: str):
        activity = discord.Activity(type=discord.ActivityType.watching, name=status)
        await bot.change_presence(status=discord.Status.online, activity=activity)

    async def Status_None(self, bot):
        await bot.change_presence(status=discord.Status.online, activity=None)

    # test mode / goblin mode (word of the year 2022) - swaps players for goblin names useful for testing
    async def TestMode(self, is_test: bool, bot):
        self.names = []
        self.players = []
        self.is_test = is_test
        self.index = 0
        print(f'TEST MODE: {is_test}')
        if self.is_test:
            self.ReadPlayerFile(self.test_file)    
        else:
            self.ReadPlayerFile(self.player_file)

        await self.ReadAllUsers(bot)

# game state encorder used to save to file
class GameStateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, GameState):

            # Here, you would define the encoding for your GameState object.
            # You can return the encoded object as a dictionary, or as a JSON
            # string, depending on your needs.
            return {
                'names': obj.names, 
                'players': obj.players, 
            # 'mapping': obj.mapping,   # NOT SERIALIZABLE!!    
                'alarm_hours': obj.alarm_hours,
                'channel': obj.channel,
                'is_test': obj.is_test,
                'index': obj.index,
                'active': obj.active,
                'silent': obj.silent
            }
        # This is important: call the superclass method to raise an exception
        # for unsupported types
        return super().default(obj)
