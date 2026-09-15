import json
import os





def load_json(file_path):
    """Load data from a JSON file."""
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(file_path, data):
    """Save data to a JSON file."""
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def update_json(file_path, callback):
    """
    Load JSON, modify it using callback, then save it.
    """
    data = load_json(file_path)

    if data is None:
        data = {}

    callback(data)
    save_json(file_path, data)