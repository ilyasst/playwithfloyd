import json
from datetime import datetime
from utils.text_utils import clean_log_text

def log_agent_command(log_file: str, command_data: dict):
    """Add the agent's command and explanation to the log file with a timestamp."""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    command = command_data['command']
    explanation = command_data['explanation']
    log_entry = f"[{timestamp}] [AGENT] {command}\n"
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)

def log_story_narration(story_log_file: str, narration: str, update_decision: dict = None):
    """Add the story narration to the log file with a timestamp."""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    log_entry = f"[{timestamp}] [STORY] {narration}\n"
    
    with open(story_log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)

def log_game_update(json_log_file: str, game_output: str, if_agent_action: dict = None, story_updated: bool = False):
    """Log a game update to the JSON log file."""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    
    # Create the update entry
    update = {
        "timestamp": timestamp,
        "game_output": clean_log_text(game_output),
        "story_updated": story_updated
    }
    
    if if_agent_action:
        update["agent_action"] = if_agent_action
    
    # Read existing entries or create new list
    try:
        with open(json_log_file, 'r', encoding='utf-8') as f:
            entries = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        entries = []
    
    # Append new entry
    entries.append(update)
    
    # Write back to file
    with open(json_log_file, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2)

def update_last_json_entry(json_log_file: str, **kwargs):
    """Update the last entry in the JSON log file with additional fields."""
    try:
        with open(json_log_file, 'r', encoding='utf-8') as f:
            entries = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return
    
    if entries:
        # Update the last entry with the provided fields
        entries[-1].update(kwargs)
        
        # Write back to file
        with open(json_log_file, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2) 