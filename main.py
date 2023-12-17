# Import libraries
from flask import Flask, render_template, request, Response, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_session import Session
from pymongo import MongoClient
import string
import random
from time import gmtime
from time import strftime
from bson.objectid import ObjectId
import json
import subprocess
import certifi
import os

# Load environment variables
if 'ON_HEROKU_SERVER' not in os.environ:
    config_vars = json.loads(subprocess.check_output(
        'heroku config -a spyfall --json', shell=True).decode())
    for key, value in config_vars.items():
        os.environ[key] = value

# Create Flask app, configure server-side sessions
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config.from_object(__name__)
Session(app)

# Initialize Socket IO
socketio = SocketIO(app)

# Initialize Mongo DB connection
certificate = certifi.where()
mongo_client = MongoClient(os.environ['MONGO_DB_URI'], tlsCAFile=certificate)
db = mongo_client.get_database("spyfall")


# Class for timer
class Timer:
    def __init__(self, curr_time):
        self.curr_time = curr_time

    def decrement(self):
        """
        Decrements the timer by 1 second
        :return: The current time after decrementing
        """
        if self.curr_time > 0:
            self.curr_time -= 1
        return strftime("%M:%S", gmtime(self.curr_time))

    def clear(self):
        """
        Clears the timer (resets time to 0)
        """
        self.curr_time = 0


# UTIL FUNCTIONS
def get_collection(collection_name):
    """
    :param collection_name: The name of collection to retrieve
    :return: The retrieved collection
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
        if db_game_exists(game_code):
            continue
        return game_code.upper()


def validate_route_access(game_code):
    """
    Determines whether the user is eligible to access the route.
    (E.g. has user joined the game, is the game valid, etc.)
    :param game_code: The game code being checked
    :return: True if user is eligible to access route, and False if ineligible
    """
    # Check if game exists
    if not db_game_exists(game_code):
        print("Specified game does not exist. Redirecting back to home...")
        return False

    # Check if player has joined the game
    if 'id' in session:
        if not db_player_joined_game(session['id'], game_code):
            print("Player hasn't joined this game. Redirecting back to home...")
            return False
    else:
        print("User is trying to access invalid route. Redirecting back to home...")
        return False
    return True


def clear_timer_and_location():
    if 'timer' in session:
        print("Deleting timer from session...")
        del session['timer']
    if 'location_image' in session:
        print("Deleting location image from session...")
        del session['location_image']


def leave_game(player_id, game_code):
    """
    Removes the specified player from the specified game (in MongoDB)
    :param player_id: Id (generated from player insertion in MongoDB) of player
    :param game_code: The game code being checked
    """
    players = get_collection("players")
    players.delete_one({'_id': ObjectId(player_id), 'game': game_code})


def end_game(owner, game_code):
    """
    Removes the specified game from MongoDB
    :param owner: The owner of the game
    :param game_code: Game code being checked
    """
    games = get_collection("games")
    games.delete_one({'game_code': game_code, 'owner': owner})


# DB FUNCTIONS
def db_create_game(player_id, game_code):
    """
    Creates a game in the games collection.
    :param player_id: The id of the player that is creating the game
    :param game_code: Code for the game
    """
    db.get_collection("games").insert_one({'game_code': game_code, 'owner': player_id, 'status': 0})
    session['owner'] = True


def db_create_player(player, game_code):
    """
    Creates a player in the player collection.
    :param player: The player's name
    :param game_code: The code of the game they are creating/joining
    """
    # Create a player
    new_player = db.get_collection("players").insert_one({'name': player, 'game': game_code, 'role': "unknown"})
    return str(new_player.inserted_id)


def db_player_joined_game(player_id, game_code):
    """
    Checks if the specified player has joined the specified game
    :param player_id: The id (from player insertion via MongoDB) of the player
    :param game_code: The game code being checked
    :return: True if the player has joined the game, and False otherwise
    """
    players = db.get_collection("players")
    query = {'game': game_code}
    for player in players.find(query):
        if player_id == str(player['_id']):
            return True
    return False


def db_get_all_players(game_code):
    """
    Retrieves all the players that have joined the specified game.
    :param game_code: The game code being checked
    :return: A list containing all the players
    """
    players = get_collection("players")
    query = {"game": game_code}
    return list(players.find(query))


def db_get_all_player_names(game_code, remove_curr_player=False):
    """
    Retrieves all the player names from the specified game
    :param game_code: The game code being checked
    :param remove_curr_player: Exclude the current player from the list
    :return: A list containing all the player names
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


def db_get_location_image(location):
    """
    Retrieves a random image from the specified location
    :param location: The location being checked
    :return: A random image of the location
    """
    query = {'name': location}
    locations = get_collection('locations')
    for location in locations.find(query):
        return random.choice(list(location['images']))


def db_get_all_locations():
    """
    Retrieves all the locations in the game
    :return: A dictionary of all the Spyfall locations
    """
    locations_dict = {}
    locations = get_collection("locations")
    for location in locations.find():
        location_name = str(location['name']).title()
        locations_dict[location_name] = location['images'][0]
    return locations_dict


def db_get_random_location():
    """
    Retrieves a random location from all available locations
    :return: A dictionary containing info of the randomly selected location
    """
    locations = get_collection("locations")
    location = list(locations.aggregate([{"$sample": {"size": 1}}]))
    return location[0]


def db_assign_roles(location, players):
    """
    Executed by the game owner to assign roles to all the players in the game
    :param location: Selected location
    :param players: List of players
    """
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


def db_get_assigned_role(player_id, game_code):
    """
    Retrieves the assigned role for the specified player
    :param player_id: Id (generated by player insertion via MongoDB) of the player
    :param game_code: The game code being checked
    :return: The player's role, and None if no role is found
    """
    players = get_collection("players")
    query = {"game": game_code}
    for player in players.find(query):
        if str(player['_id']) == player_id:
            return str(player['role'])
    return None


def db_game_exists(game_code):
    """
    :param game_code: The game code being checked
    :return: True if the specified game exists, and False otherwise
    """
    games = get_collection('games')
    for game in games.find():
        if game['game_code'] == game_code:
            return True
    return False


def db_game_started(game_code):
    """
    :param game_code: The game code being checked
    :return: True if the specified game has started, and False otherwise
    """
    games = get_collection('games')
    query = {'game_code': game_code}
    for game in games.find(query):
        if game['status'] == 1:
            return True
    return False


def db_set_game_status(game_code, status):
    """
    Sets the specified status to the specified game.s
    :param game_code: The game being modified
    :param status: The status to set
    """
    games = get_collection('games')
    query = {'game_code': game_code}
    games.update_one(query, {"$set": {"status": status}})


# ROUTE FUNCTIONS
@app.route('/')
def home():
    """
    Route for the home (main page)
    """
    return render_template('index.html')


@app.route('/rules')
def game_rules():
    """
    Route for the rules page. This page discloses
    how the game of Spyfall is played.
    :return:
    """
    return render_template('rules.html')


@app.route('/play', methods=['POST'])
def handle_play():
    """
    Route to handle form submission from home page.
    If form submission is successful, player is redirected to game's lobby.
    """
    if request.method == 'POST':
        # Clear existing session
        session.clear()
        detective_name = request.form['detectiveName']
        print(f"Detective name: {detective_name}")

        # Check if user wants to create game or join game
        if 'gameCode' in request.form:
            # User wants to join a game
            game_code = request.form['gameCode']

            # Check if game exists
            if not db_game_exists(game_code):
                print(f"ERROR: Player '{detective_name}' cannot join {game_code} (game does not exist)")
                return Response("404")

            # Check if game has less than 8 players joined
            if len(db_get_all_players(game_code)) >= 8:
                print(f"ERROR: Player '{detective_name}' cannot join {game_code} (game is currently full)")
                return Response("404")

            print(f"Player '{detective_name}' joining game {game_code}...")
            # Player is not owner of game
            session['owner'] = False
        else:
            # User wants to create a game
            game_code = generate_game_code()
            print(f"Game code: {game_code}")
            print(f"Player '{detective_name}' creating game {game_code}...")
            db_create_game(detective_name, game_code)

        # Save player name and game code
        session['player_name'] = detective_name
        session['game_code'] = game_code

        # Create player and save player ID
        session['id'] = db_create_player(session['player_name'], session['game_code'])

        # Make other players update their lobby to reflect new player joining
        socketio.emit("playerJoinLog", {'message': session['player_name']}, to=session['game_code'])
        return redirect(url_for(".go_to_lobby", game_code=game_code), code=307)


@app.route("/<game_code>/lobby", methods=['GET', 'POST'])
def go_to_lobby(game_code):
    """
    Route to access the game lobby.
    :param game_code: The game code of the lobby
    """
    # Validate route access
    if not validate_route_access(game_code):
        return redirect(url_for(".home"))

    # Set game status back to 0 if game owner returned here
    if session['owner']:
        if db_game_started(game_code):
            db_set_game_status(game_code, 0)

    # Clear player's timer and location
    clear_timer_and_location()
    joined_players = db_get_all_player_names(session['game_code'])
    return render_template('lobby.html',
                           detectiveName=session['player_name'],
                           owner=session['owner'],
                           gameCode=session['game_code'],
                           joinedPlayers=joined_players,
                           gameOwner=session['owner'])


@app.route("/get_game_info", methods=['POST'])
def retrieve_role_and_location():
    """
    Route for all players to retrieve their assigned role (by game owner)
    and proceed to the play page.
    """
    if request.method == 'POST':
        data = request.get_json()
        if session['game_code'] != data['channel']:
            print(
                f"ERROR: Channel does not match game code (received channel: {data['channel']}, game code: {session['game_code']}")
            return Response(status=400)

        print(f"{data['playerName']} is retrieving their role and starting...")
        # Get assigned role
        print(f"Player id: {session['id']}, game code: {data['channel']}")
        assigned_role = db_get_assigned_role(session['id'], data['channel'])
        print(f"Assigned role from db: {assigned_role}")
        session['role'] = assigned_role
        # Get assigned location
        session['location'] = data['location']
        print(f"Assigned role for {session['player_name']}: {session['role']} at the {session['location']}")
        return jsonify(dict(redirect=url_for('.start_playing', code=data['channel'])))


@app.route("/<code>/play")
def start_playing(code):
    """
    Route for accessing the play page.
    :param code: The code of the game being played
    """
    # Validate route access
    if not validate_route_access(code):
        return redirect(url_for(".home"))

    # Get list of all players (excluding current player)
    players = db_get_all_player_names(code, remove_curr_player=True)
    # Get list of all possible locations
    locations = db_get_all_locations()

    # Set timer for 8 minutes (prevent user from getting new timer upon page refresh)
    if 'timer' not in session:
        session['timer'] = Timer(curr_time=480)
    print(f"{session['player_name']} is starting to play as a {session['role']} at the {session['location']}")

    if session['role'] == 'spy':
        return render_template('play.html',
                               detectiveName=session['player_name'],
                               selectedLocation=None,
                               image="https://spyfall.s3.amazonaws.com/spy_profile+(1).png",
                               role=str(session['role']).title(),
                               locations=locations,
                               players=players,
                               owner=session['owner'],
                               game_code=session['game_code'])
    else:
        # Get random image for selected location (prevent user from getting new image upon page refresh)
        if 'location_image' not in session:
            session['location_image'] = db_get_location_image(session['location'])
        return render_template('play.html',
                               detectiveName=session['player_name'],
                               selectedLocation=str(session['location']).title(),
                               role=str(session['role']).title(),
                               locations=locations,
                               players=players,
                               image=session['location_image'],
                               owner=session['owner'],
                               game_code=session['game_code'])


@app.route("/_get_time", methods=['GET', 'POST'])
def get_remaining_time():
    """
    Route for players to get remaining time of the game.
    :return: The time left in the game
    """
    # Get timer object
    timer = session['timer']
    # Decrement time by 1s
    new_time = timer.decrement()
    return jsonify({"result": new_time})


@app.route("/_stop_timer", methods=['GET', 'POST'])
def stop_timer():
    """
    Route for players to stop the timer (i.e. when game owner has ended the game)
    :return: A boolean indicating whether stopping the timer was successful or not
    """
    print(f"Setting {session['player_name']}'s timer to 0:00...")
    session['timer'].clear()
    if session['owner']:
        # Set the game status to 'not started'
        db_set_game_status(session['game_code'], 0)
    return jsonify({"cleared": True})


@app.route("/leave_game", methods=['GET', 'POST'])
def handle_leave_game():
    """
    Route to leave the game. Once player has left the game,
    the player will be redirected back to the home page.
    """
    if request.method == 'POST':
        print(f"{session['player_name']} is leaving the game {session['game_code']}")
        leave_game(session['id'], session['game_code'])
        # Make players (who are in lobby) to update their lobby
        socketio.emit("playerLeft", {'message': session['player_name']}, to=session['game_code'])
        session.clear()
        return redirect(url_for(".home"))


@app.route("/end_game", methods=['GET', 'POST'])
def handle_end_game():
    """
    Route to end the game, which is only accessed by the
    game owner. Once the game has been ended, the player will
    be redirected to the home page.
    """
    if request.method == 'POST':
        end_game(session['player_name'], session['game_code'])
        leave_game(session['id'], session['game_code'])
        # Notify all players to leave game
        socketio.emit("game_ended", to=session['game_code'])
        # Make players (who are in lobby) to update their lobby
        socketio.emit("playerLeft", {'message': session['player_name']}, to=session['game_code'])
        print(f"The following player is ending the game: {session['player_name']}")
        return redirect(url_for(".home"))


@app.route("/leave_lobby", methods=['GET', 'POST'])
def handle_leave_lobby():
    """
    Route to handle players leaving the lobby.
    If the game owner is leaving the lobby, the game will automatically
    be ended. Once the player leaves the lobby, they will be redirected
    to the home page.
    """
    if request.method == 'POST':
        # Check if player is game owner
        if session['owner']:
            # End the game and then leave
            end_game(session['player_name'], session['game_code'])
            leave_game(session['id'], session['game_code'])
            # Notify all players to leave game
            socketio.emit("game_ended", to=session['game_code'])
            print(f"The following player is ending the game: {session['player_name']}")
        else:
            print(f"{session['player_name']} is leaving the game {session['game_code']}")
            leave_game(session['id'], session['game_code'])
        # Make players (who are in lobby) to update their lobby
        socketio.emit("playerLeft", {'message': session['player_name']}, to=session['game_code'])
        # Clear session
        session.clear()
        return redirect(url_for(".home"))


# SOCKETIO FUNCTIONS
@socketio.on("disconnect")
def handle_disconnect():
    """
    Handles the disconnect event that is fired by SocketIO
    """
    print("USER DISCONNECTED")
    if 'game_code' in session:
        # Leave the socket room
        leave_room(session['game_code'])
        # Make all other players update their lobby to reflect player leaving
        emit("playerLeftGame", {'player_name': session['player_name'], 'game_code': session['game_code']},
             to=session['game_code'])


@socketio.on("connect")
def handle_connect():
    """
    Handles the connect event that is fired by SocketIO
    """
    print("USER CONNECTED")
    if 'game_code' in session:
        # Join the socket room
        join_room(session['game_code'])


@socketio.on("join")
def handle_join_game(message):
    """
    Handles the join event fired by a user immediately after
    joining the game lobby
    """
    if 'joinedSocketRoom' not in session:
        print(f"{message['playerName']} joining socket room {message['channel']}")
        # Join the socket room (if not already joined)
        join_room(message['channel'])
        session['joinedSocketRoom'] = True


@socketio.on("organizeGame")
def choose_location_and_assign_roles(message):
    """
    Handles the organizeGame event that is fired by the game owner.
    This function is only executed by the game owner, who takes on
    the responsibility of being the dealer of the game (i.e. assigns
    roles to all players, starts/ends the game, etc.)
    """
    # Get list of all players
    players = db_get_all_players(message['channel'])
    # Choose random location
    location = db_get_random_location()
    # Assign roles to all players (including yourself)
    db_assign_roles(location, players)
    # Set game status to started
    db_set_game_status(message['channel'], 1)
    # Notify all other players that game is starting
    emit("gameStarting", {'location': location['name'], 'gameCode': message['channel']}, to=message['channel'],
         include_self=True)


# Main script
if __name__ == "__main__":
    app.run()
