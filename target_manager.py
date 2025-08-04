import json
import os
from pathlib import Path

# Use absolute path for Render compatibility
FILE_PATH = Path(__file__).parent / "allowed_targets.json"

def load_targets():
    try:
        if not FILE_PATH.exists():
            with open(FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump([], f)
            return []
        
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading targets: {e}")
        return []

def save_targets(targets):
    try:
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(targets, f)
        return True
    except Exception as e:
        print(f"Error saving targets: {e}")
        return False

def add_target(chat_id):
    try:
        targets = load_targets()
        if str(chat_id) not in [str(t) for t in targets]:
            targets.append(int(chat_id))
            return save_targets(targets)
        return False
    except Exception as e:
        print(f"Error adding target: {e}")
        return False

def get_all_targets():
    return load_targets()
