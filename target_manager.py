import json
import os

FILE_PATH = "allowed_targets.json"

def load_targets():
    if not os.path.exists(FILE_PATH):
        with open(FILE_PATH, 'w') as f:
            json.dump([], f)
    with open(FILE_PATH, 'r') as f:
        return json.load(f)

def save_targets(targets):
    with open(FILE_PATH, 'w') as f:
        json.dump(targets, f)

def add_target(chat_id):
    targets = load_targets()
    if chat_id not in targets:
        targets.append(chat_id)
        save_targets(targets)
        return True
    return False

def get_all_targets():
    return load_targets()
