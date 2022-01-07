import eventlet
eventlet.monkey_patch()

from flask import request, Flask, send_from_directory, jsonify, send_file
from flask_socketio import SocketIO, send, emit
from engineio.payload import Payload
import os
import sys

from .viewer import Viewer

EXCLUDE_TRAITLETS = set([
    'comm', 'count', 'keys', 'layout', 'log',
    'message', 'json', 'connect', 'disconnect'
])

Payload.max_decode_packets = 200

app = Flask(__name__)
socketio = SocketIO(app,
                    async_mode='eventlet',
                    message_queue=os.environ.get('REDIS_URL', 'redis://'))

parent_dir = os.path.dirname(__file__)
public_dir = os.path.join(parent_dir, "public")
data_dir = os.environ.get("EMBLAZE_DATA_DIR", os.path.join(parent_dir, "data"))

allow_save_selections = os.environ.get("EMBLAZE_ALLOW_SAVE_SELECTIONS", True)

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

def _get_all_datasets():
    return [os.path.join(data_dir, f)
                    for f in sorted(os.listdir(data_dir))
                    if not f.startswith('.') and f.endswith('.json')]

@app.route("/datasets")
def list_datasets():
    return jsonify(_get_all_datasets())

@socketio.on('connect')
def connect():
    print('connected', request.sid)
    widget = Viewer(file=_get_all_datasets()[0],
                    thread_starter=socketio_thread_starter,
                    allowsSavingSelections=allow_save_selections)
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

def run_server(start_redis=False, data_directory=None, debug=False):
    """
    Starts the Flask server. If start_redis is True, automatically starts a
    Redis instance (on port 6379). If not, the server expects a Redis instance
    at the URL in the environment variable REDIS_URL.
    """
    global data_dir
    if data_directory: data_dir = data_directory
    assert len(_get_all_datasets()) > 0, "No datasets (.json files) found in data directory"
    
    redis_pid = None
    
    if start_redis:
        import redis_server
        import subprocess
        import tempfile
        
        temp_dir = tempfile.mkdtemp()
        pid_path = os.path.join(temp_dir, 'redis.pid')
        
        server_path = redis_server.REDIS_SERVER_PATH
        subprocess.check_call(
            '{} --daemonize yes --pidfile {} --logfile {}'.format(
                server_path,
                pid_path,
                os.path.join(temp_dir, 'redis.log')),
            shell=True)

        # If there is a pid file, read it to know what to shut down when the server stops
        if os.path.exists(pid_path):
            with open(pid_path, 'r') as file:
                redis_pid = file.read().strip()
            print("Started redis server (pid {})".format(redis_pid))
    
    print("Running Flask server with public dir '{}' and data dir '{}'".format(public_dir, data_dir))
    try:
        socketio.run(app, debug=debug)
    except KeyboardInterrupt as e:
        if redis_pid is not None:
            print("Shutting down redis server")
            subprocess.check_call('kill {}'.format(redis_pid))
        raise e
    
if __name__ == "__main__":
    run_server(start_redis=True, data_directory=sys.argv[1] if len(sys.argv) > 1 else None, debug=True)