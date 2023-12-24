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

## Development Tools

### Flask
To develop the web-application, Python's Flask framework was chosen. 

### MongoDB
To store all player and game-related data, a MongoDB cluster was created with three collections:
- Games: Each document models a game created in Spyfall. Fields include the game code, the game creator name, and game status
- Locations: Each document models a possible location. Fields include the location name, a list of all possible roles, and a list of image URLs for location images
- Players: Each document models a player. Fields include the player's name, the game code of the game they've joined, and their role in the gamw

### SocketIO
To implement real-time actions by players, SocketIO was used. E.g. when a player joins/leaves/ends a game, a SocketIO event is emitted by the player. To ensure these events are only emitted and caught by players in the respective game, SocketIO rooms were used.

### Amazon AWS S3
To host the images for each location, Amazon AWS S3 was used.

## Gallery
![Imgur Image](https://i.imgur.com/uUtxHcz.png)
![Imgur Image](https://i.imgur.com/fhEoRJ9.png)
![Imgur Image](https://i.imgur.com/FCgXRlf.png)
![Imgur Image](https://i.imgur.com/nedk33Z.png)
![Imgur Image](https://i.imgur.com/b1sLI7o.png)
![Imgur Image](https://i.imgur.com/GQ8lrCI.png)
![Imgur Image](https://i.imgur.com/kXipxbt.png)

## Deployment
The Spyfall app has currently been deployed on Heroku:
https://spyfall-7ac4e79bd496.herokuapp.com/

## License
[MIT](https://choosealicense.com/licenses/mit/)
