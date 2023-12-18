# Spyfall with Flask and MongoDB

Spyfall is known as a social deduction board game that was originally designed by Alexandr Ushan, and later published by Cryptozoic Entertainment. The game released back in 2014 and has grown in popularity due to its simple, yet engaging gameplay that combines bluffing and deduction.

The main objective of the game is for the detectives to to identify the spy among them, and conversely, for the spy to determine the location at which the detectives are.

## Project objective

The objective of this project was to recreate the game of Spyfall, but in the form of a web-based game. To achieve this, Python's Flask web-application framework was used, as well as web-sockets for real-time player actions, and MongoDB for cloud-based storage of both game and player information.

## Gameplay

To play Spyfall, between 4-8 players are required. To begin, one player must create a new game, and share the game code with the rest of the players. When players join a game, they will be wait in the game's lobby until the game creator starts the game.

Once the game has started, all players will be redirected to a new page where all the gameplay occurs. If the player is a detective, their role and location will be displayed, along with a list of all players to help with finding the spy. 
If the player is a spy, a list of all possible locations will be displayed. 

A timer will be displayed for all players, and represents how much time is remaining before the game ends. Once the timer expires, players can return back to the lobby where they wait for the game creator to start the game again, or leave the current game and return home.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install foobar.

```bash
pip install foobar
```

## Usage

```python
import foobar

# returns 'words'
foobar.pluralize('word')

# returns 'geese'
foobar.pluralize('goose')

# returns 'phenomenon'
foobar.singularize('phenomena')
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
