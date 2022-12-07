import asyncio, json, os, random, signal
from datetime import datetime, time

class GameState:
    game_state_file = 'gamestate.json'
    player_file = 'players.json'
    test_file = 'test.json'
    channel = None
    SECONDS_PER_HOUR = 3600

    def __init__(self, active=False, alarm_hours=2, channel="", index=0, is_test=False, names=[], players=[], silent = False):
        self.active = active
        self.is_alarm_active = False
        self.silent = silent
        self.silent = True

        self.names = names
        self.players = players
        self.mapping = {} # not serialize
        self.alarm_hours = alarm_hours
        self.is_test = is_test
        self.index = index
        self.channel = channel #'🤖bot-commands'
        self.Read(self.player_file)

    def Read(self, file):
        self.names = []
        self.players = []
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
            self.players = self.names.copy()
    
    async def Restart(self, bot):
        self.TestMode(False, bot)

    async def TestMode(self, is_test: bool, bot):
        self.names = []
        self.players = []
        self.is_test = is_test
        print(f'TEST MODE: {is_test}')
        if self.is_test:
            self.ReadTestPlayers()
        else:
            self.ReadPlayers()

        await state.ReadAllUsers(bot)

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
        output += f'\nIndex is {self.index}'
        if self.alarm_hours != 0:
            output += f'\nAlarm is set to  {self.alarm_hours}'
        else:
            output += '\nAlarm is disabled'

        await ctx.channel.send(output)

        if self.mapping == {}:
            await ctx.channel.send('Reading usernames first time... one moment please...')
            for name in self.names:
                await self.ReadUser(bot, name)

        await ctx.channel.send(await self.PrintSimple())

    async def PrintSimple(self):
        output_list = []
        for name in self.names:
            user = self.mapping[name]
            if name == user:
                output_list.append(name)
            else:
                output_list.append(f'{user.name}#{user.discriminator}')
        print(output_list)
        return output_list

    async def ReadAllUsers(self, bot):
        for name in self.names:
            await self.ReadUser(bot, name)

    async def ReadUser(self, bot, name: str):
        if '@' in name:
            id = int(name.replace('<', '').replace('@', '').replace('>', ''))
            user = await bot.fetch_user(id)
            self.mapping[name] = user
        else:
            self.mapping[name] = name

        print(f"read: {self.mapping[name]}")
        return self.mapping[name]

    async def Shuffle(self):
        self.players = self.names.copy()
        random.shuffle(self.players)
        print(f'Shuffled: {self.players}')

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

    async def Serialize(self):
        return json.dumps(self, cls=GameStateEncoder, indent=4, sort_keys=True)

    async def Add(self, bot, new_name: str):
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

                    await self.ReadUser(bot, single_name)

                    await self.Save()
                    return True

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

    async def Begin(self, ctx, bot):
        # safer
        if self.mapping == {}:
            await self.ReadAllUsers(bot)
        self.index = 0

        print('Starting game...')
        self.players = self.names.copy()
        random.shuffle(self.players)
        print(f'shuffled: {self.players}')
        self.active = True
        await self.Display(ctx)
        await self.Save()

    async def End(self, ctx):
        self.active = False
        print('Ending game...')
        await ctx.channel.send(f"Game over! Congratulations {self.players[self.index]}! Start new with /begin")
        self.index = 0
        await self.Save()

    async def Display(self, ctx):
        print('Printing game...')
        # do not advance to new game here
        if not self.active:
            output = "Game is not active. Start with /begin"
            print(output)
            await ctx.channel.send(output)
            return

        alarm_text = 'Alarm is disabled'
        if self.alarm_hours > 0 and not self.is_alarm_active:
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
            output = "New Game begin! - "
            output += f"{alarm_text}\n\n"

        # current turn
        if self.silent:
            output += 'New player turn!\n\n'
        else:
            output += f"{self.players[self.index]} it's your turn!\n\n"

        # all players
        i = 0
        for name in self.players:
            if i == self.index:
                output += "--> "
            else:
                output += "    "
            i += 1

            if '@' in name:
                # id = int(name.replace("<", "").replace("@", "").replace(">", ""))
                # user = await bot.fetch_user(id)
                # m = ctx.guild.get_member(id)

                user = self.mapping[name]

                output += f'{user.name}\n'

            else: 
                output += f"{name}\n"

        print(output)

        await ctx.channel.send(output)

    async def Next(self, ctx, bot):
        self.is_alarm_active = False
        if(self.index != len(self.players)-1):
            self.index += 1
            await self.Save()
            await self.Display(ctx)
        else:
            if(self.active):
                await self.End(ctx)
            else:
                await self.Begin(ctx, bot) 
  
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

    def CanMessageDuringDaytime(self):
        start_time = time(hour=10, minute=0)  # Create a time object for 10:00 AM.
        end_time = time(hour=22, minute=0)  # Create a time object for 10:00 PM.

        current_time = datetime.now().time()  # Get the current time as a time object.

        return start_time < current_time < end_time    

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

class GameStateDecoder(json.JSONDecoder):
    def decode(self, json_str):
        # Parse the JSON string into a dictionary
        print()
        print()
        print(json_str)
        print()
        print()
        data = json.loads(json_str)
        print()
        print()
        print(data)
        print('~~~~~~~~~~')

        # Extract the values from the dictionary and use them to
        # initialize a new GameState object
        names = data['names']
        players = data['players']
        alarm_hours = data['alarm_hours']
        channel = data['channel']
        is_test = data['is_test']
        index = data['index']
        obj.active = data['active']
        obj.silent = data['silent']
        game_state = GameState(names, players, alarm_hours, channel, is_test, index)

        return game_state