# Import libraries
from pymongo.mongo_client import MongoClient
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'some_secret_key'
socketio = SocketIO(app)


@app.route('/')
def home():
    return render_template('index.html')


def connect_to_db():
    # MongoDB connection
    uri = "mongodb+srv://pathumd:OiYvywaJruot0KEn@cluster0.4lv1uqa.mongodb.net/?retryWrites=true&w=majority"
    # Create a new client and connect to the server
    client = MongoClient(uri)
    # Send a ping to confirm a successful connection
    try:
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    socketio.run(app, allow_unsafe_werkzeug=True, debug=True)