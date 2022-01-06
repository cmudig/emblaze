import eventlet
eventlet.monkey_patch()

from flask import request, Flask, send_from_directory, jsonify, send_file
from flask_socketio import SocketIO, send, emit
from engineio.payload import Payload
import os

from .viewer import Viewer

EXCLUDE_TRAITLETS = set([
    'comm', 'count', 'keys', 'layout', 'log',
    'message', 'json', 'connect', 'disconnect'
])

Payload.max_decode_packets = 200

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet', message_queue='redis://')

parent_dir = os.path.dirname(__file__)
public_dir = os.path.join(parent_dir, "public")
data_dir = os.path.join(parent_dir, "data")

user_data = {}

def socketio_thread_starter(fn, args=[], kwargs={}):
    socketio.start_background_task(fn, *args, **kwargs)

# Path for our main Svelte page
@app.route("/")
def base():
    return send_from_directory(public_dir, 'index.html')

# Path for all the static files (compiled JS/CSS, etc.)
@app.route("/<path:path>")
def home(path):
    return send_from_directory(public_dir, path)

@app.route("/datasets")
def list_datasets():
    return jsonify([os.path.join(data_dir, f, "data.json")
                    for f in sorted(os.listdir(data_dir))
                    if os.path.isdir(os.path.join(data_dir, f))])

@socketio.on('connect')
def connect():
    print('connected', request.sid)
    widget = Viewer(file=os.path.join(data_dir, "mnist-tsne", "data.json"), thread_starter=socketio_thread_starter)
    user_data[request.sid] = widget
    for trait_name in widget.trait_names(sync=lambda x: x):
        if trait_name in EXCLUDE_TRAITLETS: continue
        
        # Register callbacks for getting and setting from frontend
        socketio.on_event('get:' + trait_name, _read_value_handler(trait_name))
        socketio.on_event('set:' + trait_name, _write_value_handler(trait_name))
        
        # Emit responses when backend state changes
        widget.observe(_emit_value_handler(trait_name, request.sid), trait_name)
    
@socketio.on('disconnect')
def disconnect():
    print('disconnected', request.sid)
    del user_data[request.sid]
    
def _read_value_handler(name):
    def handle_msg():
        if request.sid not in user_data:
            print("Missing request SID:", request.sid)
            return None
        return getattr(user_data[request.sid], name)
    return handle_msg

def _write_value_handler(name):
    def handle_msg(data):
        if request.sid not in user_data:
            print("Missing request SID:", request.sid)
            return
        setattr(user_data[request.sid], name, data)
    return handle_msg

def _emit_value_handler(name, sid):
    def handle_msg(change):
        with app.app_context():
            emit('change:' + name, change.new, room=sid, namespace='/')
    return handle_msg

if __name__ == "__main__":
    print("Running Flask server with public dir '{}' and data dir '{}'".format(public_dir, data_dir))
    socketio.run(app, debug=True)