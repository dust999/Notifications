import json
import os

def load_json(file_path, default=None):
    """Load data from a JSON file with UTF-8 encoding."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []

def save_json(file_path, data):
    """Save data to a JSON file with pretty printing and UTF-8 encoding."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)