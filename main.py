# Import libraries
from flask_pymongo import PyMongo
from flask import Flask, render_template, request, Response, session, redirect, url_for
from flask_socketio import SocketIO, send, emit, join_room
from pymongo import MongoClient
import string
import random
import openai

# TODO: Fix bug where opening /lobby in two tabs causes player to join 'twice' for other users

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'some_secret_key'

# Initialize Socket IO
socketio = SocketIO(app)

# Initialize Mongo DB
uri = "mongodb+srv://pathumd:OiYvywaJruot0KEn@cluster0.4lv1uqa.mongodb.net/?retryWrites=true&w=majority"
mongo_client = MongoClient(uri)
db = mongo_client.get_database("spyfall")


# UTIL FUNCTIONS
def get_collection(collection_name):
    """
    :param collection_name: The name of collection
    :return: The collection specified by collection_name
    """
    return db.get_collection(collection_name)


def generate_game_code():
    """
    Generates a unique game code (4 letters).
    To avoid duplication, the games collection is first
    check if the generated game code exists.
    :return: The generated game code
    """
    game_code = ""

    generated = False
    while not generated:
        for i in range(0, 5):
            # Generate 5-letter game code
            game_code += random.choice(string.ascii_letters)
        # Check if game code already exists in DB
        if game_exists(game_code):
            continue
        return game_code.upper()


def game_exists(game_code):
    """
    Checks whether the specified game exists.
    :param game_code: The game code of the game
    :return: True if the game exists, and False otherwise
    """
    games = get_collection('games')
    query = {"game_code": game_code}
    for item in games.find(query):
        if item['game_code'] == game_code:
            return True
    return False


# DB FUNCTIONS
def db_create_game(player_id, game_code):
    """
    Creates a game in the games collection.
    :param player_id: The id of the player that is creating the game
    :param game_code: Code for the game
    """
    db.get_collection("games").insert_one({'game_code': game_code, 'status': 0, 'owner': player_id})
    session['owner'] = True


def db_create_player(player, game_code):
    """
    Creates a player in the players collection.
    :param player: The player's name
    :param game_code: The code of the game they are creating/joining
    """
    # Create a player
    new_player = db.get_collection("players").insert_one({'name': player, 'game': game_code, 'role': "unknown"})
    session['id'] = str(new_player.inserted_id)


def db_get_all_players(game_code):
    players = get_collection("players")
    query = {"game": game_code}
    return list(players.find(query))


def db_get_all_player_names(game_code, remove_curr_player=False):
    """
    :param game_code: The code of the game
    :param remove_curr_player: Exclude the current player from the list
    :return: A list containing all the player names that have joined the specified game
    """
    # Retrieve list of all players who've currently joined the game
    players_lst = []
    players = get_collection("players")
    query = {"game": game_code}
    for player in players.find(query):
        if session['id'] == str(player['_id']) and remove_curr_player:
            continue
        players_lst.append(player['name'])
    return players_lst

def db_get_location():
    locations = get_collection("locations")
    location = list(locations.aggregate([{"$sample": {"size": 1}}]))
    return location[0]

def db_assign_roles(location, players):
    roles = location['roles']
    random.shuffle(roles)
    players_col = get_collection("players")

    # Select spy
    spy = players.pop(random.randrange(len(players)))
    query = {"_id": spy['_id'], "name": spy['name']}
    players_col.update_one(query, {"$set": {"role": "spy"}})

    # Assign roles for remaining players
    for player in players:
        role = roles.pop()
        query = {"_id": player['_id'], "name": player['name']}
        players_col.update_one(query, {"$set": {"role": role}})


# ROUTE FUNCTIONS
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/play', methods=['POST'])
def handle_play():
    if request.method == 'POST':
        detective_name = request.form['detectiveName']
        # Check if user wants to create game or join game
        if 'gameCode' in request.form:
            # User wants to join a game
            game_code = request.form['gameCode']
            if game_exists(game_code):
                print(f"Player '{detective_name}' joining game {game_code}...")
            else:
                print(f"ERROR: Player '{detective_name}' cannot join {game_code} (game does not exist)")
                return Response("404")
            # Player is not owner of game
            session['owner'] = False
        else:
            # User wants to create a game
            game_code = generate_game_code()
            print(f"Player '{detective_name}' creating game {game_code}...")
            db_create_game(detective_name, game_code)

        # Save player's info
        db_create_player(detective_name, game_code)
        # Save session info
        session['player_name'] = detective_name
        session['game_code'] = game_code
        return redirect(url_for(".go_to_lobby"))


@app.route("/lobby")
def go_to_lobby():
    joined_players = db_get_all_player_names(session['game_code'], remove_curr_player=True)
    return render_template('lobby.html',
                           detectiveName=session['player_name'],
                           gameCode=session['game_code'],
                           joinedPlayers=joined_players,
                           gameOwner=session['owner'])


# SOCKETIO FUNCTIONS
@socketio.on("join")
def handle_join_game(message):
    join_room(message['channel'])
    emit("playerJoinLog", {'message': message['playerName']}, room=message['channel'])

@socketio.on("organizeGame")
def get_location_and_assign_roles(message):
    """
    Executed only by game owner, acts as dealer in the game
    :param message:
    :return:
    """
    # Get list of all players
    players = db_get_all_players(message['channel'])
    location = db_get_location()
    db_assign_roles(location, players)
    # Notify all other players that game is starting
    emit("start", {'gameCode': message['channel']}, room=message['channel'])

@socketio.on("start")
def handle_start(message):
    """
    Executed by all players to retrieve the location
    and role they will have for the game.
    :param message:
    :return:
    """
    pass


if __name__ == "__main__":
    socketio.run(app, allow_unsafe_werkzeug=True, debug=True)
