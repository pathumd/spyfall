# Import libraries
from flask_pymongo import PyMongo
from flask import Flask, render_template, request, Response, session, redirect, url_for
from flask_socketio import SocketIO, send, emit
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

# Initialize OpenAI
openai.api_key = "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"


def get_collection(collection_name):
    return db.get_collection(collection_name)


# UTIL FUNCTIONS
def generate_game_code():
    game_code = ""
    games = get_collection('games')
    # Retrieve all game codes
    game_codes = []
    for game in games.find():
        game_codes.append(game['game_code'])

    generated = False
    while not generated:
        for i in range(0, 5):
            # Generate 5-letter game code
            game_code += random.choice(string.ascii_letters)
        # Check if game code already exists in DB
        if game_code in game_codes:
            continue
        return game_code.upper()


def verify_game_code(game_code):
    games = get_collection('games')
    query = {"game_code": game_code}
    for item in games.find(query):
        if item['game_code'] == game_code:
            return True
    return False


def generate_image(prompt):
    # Generate image
    response = openai.Image.create(prompt=prompt, n=1, size="800x600")
    # Get image URL
    return response['data'][0]['url']


# DB FUNCTIONS
def db_create_game(player, game_code):
    # Generate 5-letter game code (e.g. ABCDE)
    db.get_collection("games").insert_one({'game_code': game_code, 'status': 0, 'owner': player})


def db_create_player(player, game_code):
    # Create a player
    new_player = db.get_collection("players").insert_one({'name': player, 'game': game_code, 'role': "unknown"})
    session['id'] = str(new_player.inserted_id)


def db_get_all_players(game_code):
    # Retrieve list of all players who've currently joined the game
    players_lst = []
    players = get_collection("players")
    for player in players.find():
        if player['game'] == game_code and session['id'] != str(player['_id']):
            players_lst.append(player['name'])
    return players_lst

# SOCKETIO FUNCTIONS

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
            verified = verify_game_code(game_code)
            if verified:
                print(f"Player '{detective_name}' joining game {game_code}...")
            else:
                print(f"ERROR: Player '{detective_name}' cannot join {game_code} (game does not exist)")
                return Response("404")
        else:
            # User wants to create a game
            game_code = generate_game_code()
            print(f"Player '{detective_name}' creating game {game_code}...")
            db_create_game(detective_name, game_code)
        # Save player info
        db_create_player(detective_name, game_code)
        # Save session info
        session['player_name'] = detective_name
        session['game_code'] = game_code
        return redirect(url_for(".go_to_lobby"))


@app.route("/lobby")
def go_to_lobby():
    joined_players = db_get_all_players(session['game_code'])
    return render_template('lobby.html', detectiveName=session['player_name'], gameCode=session['game_code'], joinedPlayers=joined_players)


@socketio.on("joinedGame")
def handle_join_game(player_name):
    emit("playerJoinLog", {'message': player_name}, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, allow_unsafe_werkzeug=True, debug=True)
