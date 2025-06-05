import logging
import os
from datetime import datetime
import json

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Set up logging to file only
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='game.log',
    filemode='a'
)

# Create loggers for different components
main_logger = logging.getLogger('main')
main_logger.propagate = False  # Prevent propagation to root logger

frotz_logger = logging.getLogger('frotz')
frotz_logger.propagate = False

def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific component."""
    logger = logging.getLogger(name)
    logger.propagate = False
    return logger

def log_agent_interaction(agent_name: str, system_message: str, prompt: str, response: str):
    """Log agent interactions to a JSON file."""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    
    # Create the log entry
    log_entry = {
        "timestamp": timestamp,
        "system_message": system_message,
        "prompt": prompt,
        "response": response
    }
    
    # Get the log file path
    log_file = f'logs/{agent_name}_interactions.json'
    
    # Read existing entries or create new list
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            entries = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        entries = []
    
    # Append new entry
    entries.append(log_entry)
    
    # Write back to file
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2) 