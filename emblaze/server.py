from flask import request, Flask, send_from_directory, jsonify, send_file
import os
import json
import numpy as np
from . import moving_scatterplot as ms

app = Flask(__name__)

parent_dir = os.path.dirname(__file__)
public_dir = os.path.join(parent_dir, "public")
data_dir = os.path.join(parent_dir, "data")

# Path for our main Svelte page
@app.route("/")
def base():
    return send_from_directory(public_dir, 'index.html')

# Path for all the static files (compiled JS/CSS, etc.)
@app.route("/<path:path>")
def home(path):
    return send_from_directory(public_dir, path)

# Example

@app.route("/datasets")
def list_datasets():
    return jsonify([f for f in sorted(os.listdir(data_dir)) if os.path.isdir(os.path.join(data_dir, f))])

@app.route("/datasets/<dataset_name>/data")
def get_data(dataset_name):
    dataset_base = os.path.join(data_dir, dataset_name)
    if not os.path.exists(dataset_base) or not os.path.isdir(dataset_base):
        return app.response_class(response="The dataset does not exist", status=404)

    with open(os.path.join(dataset_base, "data.json"), "r") as file:
        return app.response_class(
            response=file.read(),
            status=200,
            mimetype='application/json'
        )

@app.route("/datasets/<dataset_name>/thumbnails")
def get_thumbnails(dataset_name):
    dataset_base = os.path.join(data_dir, dataset_name)
    if not os.path.exists(dataset_base) or not os.path.isdir(dataset_base):
        return app.response_class(response="The dataset does not exist", status=404)

    if not os.path.exists(os.path.join(dataset_base, "thumbnails.json")):
        return app.response_class(response="The dataset has no thumbnails", status=404)

    with open(os.path.join(dataset_base, "thumbnails.json"), "r") as file:
        return app.response_class(
            response=file.read(),
            status=200,
            mimetype='application/json'
        )

@app.route("/datasets/<dataset_name>/supplementary/<filename>")
def get_supplementary_file(dataset_name, filename):
    dataset_base = os.path.join(data_dir, dataset_name)
    if not os.path.exists(dataset_base) or not os.path.isdir(dataset_base):
        return app.response_class(response="The dataset does not exist", status=404)

    return send_file(os.path.join(dataset_base, "supplementary", filename))

@app.route("/align/<dataset_name>/<current_frame>", methods=['GET', 'POST'])
def align_frames(dataset_name, current_frame):
    dataset_base = os.path.join(data_dir, dataset_name)
    if not os.path.exists(dataset_base) or not os.path.isdir(dataset_base):
        return app.response_class(response="The dataset does not exist", status=404)

    # Allow client-supplied initial transform as 3x3 nested list
    base_transform = None
    ids = None
    if request.method == 'POST':
        body = request.json
        if body:
            if "initialTransform" in body:
                base_transform = ms.matrix_to_affine(np.array(body["initialTransform"]))
            if "ids" in body:
                ids = body["ids"]

    with open(os.path.join(dataset_base, "data.json"), "r") as file:
        data = json.load(file)
    try:
        data = data["data"]
    except:
        pass

    if not ids:
        return jsonify({"transformations": [
            np.eye(3).tolist()
            for i in range(len(data))
        ]})

    try:
        current_frame = int(current_frame)
    except:
        current_frame = None
    
    if current_frame is None or current_frame < 0 or current_frame >= len(data):
        return app.response_class(response="Invalid frame number", status=400)
    
    frames = [ms.ScatterplotFrame([{
        "id": id_val,
        "x": item["x"],
        "y": item["y"],
    } for id_val, item in frame.items()]) for frame in data]

    transformations = []
    for frame in frames:
        transformations.append(ms.affine_to_matrix(ms.align_projection(
            frames[current_frame], 
            frame, 
            ids=list(set(ids)) if ids else None,
            base_transform=base_transform,
            return_transform=True,
            allow_flips=False)).tolist())

    return jsonify({"transformations": transformations})

if __name__ == "__main__":
    print("Running Flask server with public dir '{}' and data dir '{}'".format(public_dir, data_dir))
    app.run(debug=True)