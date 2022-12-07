import json, os, random

class GameState:
    game_state_file = 'gamestate.json'
    player_file = 'players.json'
    test_file = 'test.json'
    channel = None
    SECONDS_PER_HOUR = 3600

    def __init__(self):
        self.active = False

        self.names = []
        self.players = []
        self.mapping = {}
        self.alarm_hours = 2
        self.is_test = False
        self.index = 0
        self.channel = '🤖bot-commands'
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
        print('Saving..')

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
        await self.ReadAllUsers(bot)

        print('Starting game...')
        self.players = self.names.copy()
        random.shuffle(self.players)
        print(f'shuffled: {self.players}')
        self.active = True
        await self.Display(ctx)

    async def End(self, ctx):
        self.active = False
        print('Ending game...')
        await ctx.channel.send(f"Game over! Congratulations {self.players[self.index]}! Start new with /begin")
        self.index = 0

    async def Display(self, ctx):
        print('Printing game...')
        # do not advance to new game here
        if not self.active:
            output = "Game is not active. Start with /begin"
            print(output)
            await ctx.channel.send(output)
            return

        alarm_text = 'Alarm is disabled'
        # if self.alarm_hours > 0:
        #     # set alarm reminder for active player
        #     interval_text = format(self.alarm_hours/self.SECONDS_PER_HOUR, ".0f")
        #     alarm_text = f"setting alarm to {interval_text} hour(s)"
        #     print(alarm_text)
        #     signal.signal(signal.SIGALRM, lambda signum, frame: 
        #         # await alarm(ctx)
        #         asyncio.create_task(message_alarm(ctx, signal))
        #     )
        #     signal.alarm(alarm_interval)

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
        output += f"{self.players[self.index]} it's your turn!\n\n"
        # output += 'New player turn\n\n'

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
        if(self.index != len(self.players)-1):
            self.index += 1
            await self.Display(ctx)
        else:
            if(self.active):
                await self.End(ctx)
            else:
                await self.Begin(ctx, bot) 

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
                'index': obj.index
            }
        # This is important: call the superclass method to raise an exception
        # for unsupported types
        return super().default(obj)