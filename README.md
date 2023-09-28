# discord-game-turn-bot

This code represents a simple game that can be played in a Discord channel. The game involves adding players to a list and then shuffling the list to randomly select a player. The selected player can then be skipped to the next player in the list. The game ends when the last player in the list is reached. The list of players and the current game state are saved to a file, allowing the game to be resumed at a later time.

# game progression

The game progresses as follows:

1. Players are added to the game using the `/add` command, followed by a list of player names separated by commas. The player list is saved to a file, and the updated list is printed.

2. The game is started using the `/begin`, `/go`, `/start`, `/random`, or `/randomize` command, which shuffles the player list and prints the first player.

```
@ai-telephone-game-bot
BOT
New Game begin! - setting alarm to 2 hour(s)

Grawgith it's your turn!

--> Grawgith
    @Christopher (yoetrian)
    Grubblin
    Gribble
```

3. The current player can be skipped to the next player in the list using the `/next` or `/skip` command. If the current player is the last player in the list, a message is sent indicating that the game has ended. Additionally, if the active player posts an image in a channel that the bot is listening to, the game will automatically progress to the next player.

```
@Christopher (yoetrian)
/next
ai-telephone-game-bot
BOT

@Christopher (yoetrian) it's your turn!

    Grawgith
--> @Christopher (yoetrian)
    Grubblin
    Gribble
```

```
@Christopher (yoetrian)
![](nia.jpg)
ai-telephone-game-bot
BOT
Grubblin it's your turn!

    Grawgith
    @Christopher (yoetrian)
--> Grubblin
    Gribble
```

4. The game can be ended at any time using the `/end` command, which displays the final player.

```
@Christopher (yoetrian)
/end
@ai-telephone-game-bot
BOT
Game over! Congratulations Grubblin! Start new with /begin
```

5. The game can be resumed at a later time by running the script again and using the `/begin` command to start the game from the last saved state.

# configuration

`/config` will show the current configuration of the game

```
Listening on 🤖bot-commands
Game is not active
Game is silent (no @ s)
Index is 0
Alarm is set to  2
['Grawgith', 'Gribble', 'Grubblin', '@Christopher (yoetrian)']
```

`/alarm 4` will set alarm to 4 hours (default is 2)
`/alarm 0` will disable the alarm

Changing the alarm mid-game will take effect with next player or after prior set alarm goes off

## Discord Bot

This is a Discord bot written in Python. It uses the `discord.py` library to interact with the Discord API. The bot is initialized with the `commands.Bot` class, which allows it to respond to `/` commands. 

The bot also responds to certain direct messages and simple commands outside the listening channel of the game.

## Commands

`/help`
```
​No Category:
  add      Adds player to game. If game is active, goes to end of list
  alarm    Set player alarm in hours
  begin    Shuffles and starts new game
  config   Shows configuration of bot
  end      End game
  gametest aka /goblinmode - swaps players for test goblins
  hello    Hello, World
  help     Shows this message
  listen   Set listening to this channel
  next     Optionally progress to next player.
  print    Prints current game status
  remove   Removes player from game
  restart  Resets players (used for swapping out of test mode)
  silent   Toggles if @ messaging is used during turns

Type /help command for more info on a command.
You can also type /help category for more info on a category.
```

## Usage

1. Install the required dependencies: `discord.py`, `asyncio`, `json`, and `random`.
2. Replace the `TOKEN` variable with your bot's token.
3. Run the script: `python bot.py`

## File Structure

- `discordbot.py` - main script, defines commands
- `classes/gamestate.py` seralizable game state object, game actions, and print outs (including to discord)
- `players.json` - file containing a list of players in the game
- `gamestate.json` - file containing prior game state, saved on change
- `test.json` - test goblins

## Docker

docker build -t ai-telephone-bot .

docker run -d --name ai-telephone-bot ai-telephone-bot

docker logs -f ai-telephone-bot
