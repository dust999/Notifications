import json
import os

def load_json(file_path, default_value):
    """Load JSON data from a file, returning default_value if the file doesn't exist or is invalid."""
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return default_value
    return default_value

def save_json(file_path, data):
    """Save data to a JSON file with pretty printing."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)