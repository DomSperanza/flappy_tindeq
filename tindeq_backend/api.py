from flask import Flask, jsonify, Response, send_from_directory, render_template, request
import asyncio
import json
import time
from flask_socketio import SocketIO, emit

from tindeq import TindeqProgressor

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('main.html')  # Serve the main page with buttons




# Placeholder for the TindeqProgressor instance
tindeq_progressor = None

class WebSocketLogger:
    def log_force_sample(self, time, weight):
        socketio.emit('weight_data', {'time': time, 'weight': weight})

@app.route('/start_logging')
def start_logging():
    asyncio.run_coroutine_threadsafe(tindeq_progressor.start_logging_weight(), asyncio.get_event_loop())
    return jsonify({"status": "started"})

@app.route('/stop_logging')
def stop_logging():
    asyncio.run_coroutine_threadsafe(tindeq_progressor.stop_logging_weight(), asyncio.get_event_loop())
    return jsonify({"status": "stopped"})

@app.route('/stream')
def stream():
    def generate_data():

        while True:
            data = {"value": "some data from tindeq"}  # Example data structure
            yield f"data:{json.dumps(data)}\n\n"
            time.sleep(1)  # Simulate delay for data fetching
    return Response(generate_data(), mimetype='text/event-stream')

async def init_tindeq():
    global tindeq_progressor
    if not tindeq_progressor:
        tindeq_progressor = TindeqProgressor(WebSocketLogger())
    if not hasattr(tindeq_progressor, 'is_connected') or not tindeq_progressor.is_connected:
        await tindeq_progressor.__aenter__()  # Manually enter the context

def run_app():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_tindeq())
    socketio.run(app, debug=False, port=5000)

if __name__ == "__main__":
    run_app()