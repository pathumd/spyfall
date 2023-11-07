# Import libraries
from flask_pymongo import PyMongo
from flask import Flask, render_template, request, Response, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from flask_session import Session
from pymongo import MongoClient
import string
import random
from time import gmtime
from time import strftime

# TODO: Fix bug where opening /lobby in two tabs causes player to join 'twice' for other users

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'some_secret_key'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config.from_object(__name__)
Session(app)

# Initialize Socket IO
socketio = SocketIO(app)

# Initialize Mongo DB
uri = "mongodb+srv://pathumd:OiYvywaJruot0KEn@cluster0.4lv1uqa.mongodb.net/?retryWrites=true&w=majority"
mongo_client = MongoClient(uri)
db = mongo_client.get_database("spyfall")


# CLASS FOR TIMER
class Timer:
    def __init__(self, curr_time):
        self.curr_time = curr_time

    def decrement(self):
        if self.curr_time > 0:
            self.curr_time -= 1
        return strftime("%M:%S", gmtime(self.curr_time))


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


# DB FUNCTIONS
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
    Creates a player in the player collection.
    :param player: The player's name
    :param game_code: The code of the game they are creating/joining
    """
    # Create a player
    new_player = db.get_collection("players").insert_one({'name': player, 'game': game_code, 'role': "unknown", 'state': 'idle'})
    return str(new_player.inserted_id)


def db_player_joined_game(player_id, game_code):
    players = db.get_collection("players")
    query = {'game': game_code}
    for player in players.find(query):
        if player_id == str(player['_id']):
            return True
    return False


def db_update_player_state(player_id, game_code, state):
    players = db.get_collection("players")

    # Update player's status
    query = {"_id": player_id, "game": game_code}
    players.update_one(query, {"$set": {"state": state}})


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


def db_get_location_image(location):
    query = {'name': location}
    locations = get_collection('locations')
    for location in locations.find(query):
        return random.choice(list(location['images']))


def db_get_all_locations():
    locations_dict = {}
    locations = get_collection("locations")
    for location in locations.find():
        location_name = str(location['name']).title()
        locations_dict[location_name] = location['images'][0]
    return locations_dict


def db_get_random_location():
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


def db_get_assigned_role(player_id, game_code):
    players = get_collection("players")
    query = {"game": game_code}
    for player in players.find(query):
        if str(player['_id']) == player_id:
            return str(player['role'])
    return None


# ROUTE FUNCTIONS
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/play', methods=['POST'])
def handle_play():
    if request.method == 'POST':
        # Clear existing session
        session.clear()
        detective_name = request.form['detectiveName']
        print(f"Detective name: {detective_name}")
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
            print(f"Game code: {game_code}")
            print(f"Player '{detective_name}' creating game {game_code}...")
            db_create_game(detective_name, game_code)
        # Save player name and game code
        session['player_name'] = detective_name
        session['game_code'] = game_code
        # Create player and save player ID
        session['id'] = db_create_player(session['player_name'], session['game_code'])
        socketio.emit("playerJoinLog", {'message': session['player_name']}, to=session['game_code'])

        return redirect(url_for(".go_to_lobby", game_code=game_code))


@app.route("/<game_code>/lobby")
def go_to_lobby(game_code):
    #TODO: Move the following part into a function (account for case where user navigates back to this route from /play page
    if 'timer' in session:
        print("Deleting timer from session...")
        del session['timer']
    if 'location_image' in session:
        print("Deleting location image from session...")
        del session['location_image']

    joined_players = db_get_all_player_names(session['game_code'])
    return render_template('lobby.html',
                           detectiveName=session['player_name'],
                           gameCode=session['game_code'],
                           joinedPlayers=joined_players,
                           gameOwner=session['owner'])


@app.route("/get_game_info", methods=['POST'])
def retrieve_role_and_location():
    """
    Executed by all players to retrieve the location
    and role they will have for the game.
    :param message:
    :return:
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


# SOCKETIO FUNCTIONS
@socketio.on("disconnect")
def handle_disconnect():
    print("USER DISCONNECTED")
    if 'game_code' in session:
        print(f"Leaving room for {session['game_code']}")
        leave_room(session['game_code'])
    # session.clear()


@socketio.on("connect")
def handle_connect():
    print("USER CONNECTED")
    # if 'game_code' in session:
        # leave_room(session['game_code'])
    # session.clear()


@socketio.on("join")
def handle_join_game(message):
    if 'joinedSocketRoom' not in session:
        print(f"{message['playerName']} joining socket room {message['channel']}")
        join_room(message['channel'])
        session['joinedSocketRoom'] = True

@socketio.on("organizeGame")
def choose_location_and_assign_roles(message):
    """
    Executed only by game owner, acts as dealer in the game
    :param message:
    :return:
    """
    # Get list of all players
    players = db_get_all_players(message['channel'])
    # Choose random location
    location = db_get_random_location()
    # Assign roles to all players (including yourself)
    db_assign_roles(location, players)
    # Notify all other players that game is starting
    emit("gameStarting", {'location': location['name'], 'gameCode': message['channel']}, to=message['channel'],
         include_self=True)


@app.route("/<code>/play")
def start_playing(code):
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
                               image="https://i.imgur.com/oLxKqoZ.png",
                               role=str(session['role']).title(),
                               locations=locations,
                               players=players)
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
                                image=session['location_image'])


@app.route("/_get_time", methods=['GET', 'POST'])
def get_remaining_time():
    timer = session['timer']
    new_time = timer.decrement()
    return jsonify({"result": new_time})


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port="5000", allow_unsafe_werkzeug=True, debug=True)
