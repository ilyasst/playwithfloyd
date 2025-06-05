import os
import json
from datetime import datetime

def get_story_log_filename(game_path: str) -> str:
    """Get the story log filename for a given game path."""
    game_name = os.path.basename(game_path)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f'logs/{game_name}_{timestamp}_story.log'

def get_json_log_filename(game_path: str) -> str:
    """Get the JSON log filename for a given game path."""
    game_name = os.path.basename(game_path)
    return f'logs/{game_name}_updates.json'

def get_last_n_updates(log_file: str, n: int = 3) -> str:
    """Get the last n updates from a log file."""
    try:
        # Create the logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Create the file if it doesn't exist
        if not os.path.exists(log_file):
            with open(log_file, 'w', encoding='utf-8') as f:
                pass
            return ""
            
        # Read the file
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Get the last n non-empty lines
            last_lines = [line for line in lines if line.strip()][-n:]
            return ''.join(last_lines)
    except (FileNotFoundError, PermissionError, OSError) as e:
        # Log the error but don't raise it
        print(f"Warning: Could not read log file {log_file}: {e}")
        return ""

def get_last_n_json_updates(json_log_file: str, n: int = 3) -> str:
    """Get the last n updates from a JSON log file."""
    try:
        with open(json_log_file, 'r', encoding='utf-8') as f:
            entries = json.load(f)
            # Get the last n entries
            last_entries = entries[-n:]
            return json.dumps(last_entries, indent=2)
    except (FileNotFoundError, json.JSONDecodeError):
        return "[]" 