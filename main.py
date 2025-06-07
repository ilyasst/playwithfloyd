from runner.frotz_runner import FrotzRunner
import sys
import traceback
import logging
import os
import argparse
import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from agents.agent import game_agent, story_agent, update_decidor_agent
from datetime import datetime
import select
import time
from google.genai import types
from dotenv import load_dotenv
from collections import deque
import json
from tts_handler import TTSHandler
import re

# Import from new modules
from utils.logging_utils import main_logger as logger, log_agent_interaction
from utils.file_utils import get_story_log_filename, get_json_log_filename, get_last_n_updates, get_last_n_json_updates
from utils.text_utils import clean_log_text
from game.game_io import wait_for_key, print_game_output, print_agent_response
from game.game_logger import log_agent_command, log_story_narration, log_game_update, update_last_json_entry
from agents.agent_interactions import get_agent_command, get_update_decision
from agents.story_handler import get_story_narration

# Debug: Print environment variables before loading .env
print("Environment variables before load_dotenv:")
print(f"GOOGLE_GENAI_USE_VERTEXAI: {os.getenv('GOOGLE_GENAI_USE_VERTEXAI')}")
print(f"GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
print(f"GOOGLE_CLOUD_LOCATION: {os.getenv('GOOGLE_CLOUD_LOCATION')}")

# Load environment variables from .env file
load_dotenv()

# Debug: Print environment variables after loading .env
print("\nEnvironment variables after load_dotenv:")
print(f"GOOGLE_GENAI_USE_VERTEXAI: {os.getenv('GOOGLE_GENAI_USE_VERTEXAI')}")
print(f"GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
print(f"GOOGLE_CLOUD_LOCATION: {os.getenv('GOOGLE_CLOUD_LOCATION')}")

# Get TTS configuration from environment
USE_TTS = os.getenv('USE_TTS', 'false').lower() == 'true'
# Get wait for key configuration from environment
WAIT_FOR_KEY = os.getenv('WAIT_FOR_KEY', 'true').lower() == 'true'

# Set up logging to file only
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='game.log',
    filemode='a'
)

# Create a logger that only writes to file
logger = logging.getLogger('main')
logger.propagate = False  # Prevent propagation to root logger

# Define constants for identifying the interaction context
APP_NAME = "text_game_app"
USER_ID = "game_user"
SESSION_ID = "game_session_001"

# Create a session service for the agent
session_service = InMemorySessionService()

def wait_for_key():
    """Wait for any key press to continue if enabled in environment."""
    if not WAIT_FOR_KEY:
        return
    print("\nPress any key to continue...", end='', flush=True)
    # Use select to wait for input without blocking
    select.select([sys.stdin], [], [], None)
    sys.stdin.readline()
    print("\r" + " " * 40 + "\r", end='', flush=True)  # Clear the prompt line

def print_game_output(text: str):
    """Print game output in a clean format."""
    # Print exactly as received, preserving all formatting
    print(text, end='', flush=True)

def print_agent_response(command: str):
    """Print agent response in a clean format."""
    # Remove any leading/trailing whitespace
    command = command.strip()
    # Print with a single newline prefix and [AGENT] tag
    print(f"\n[AGENT] {command}")

def clean_log_text(log_text: str) -> str:
    """Remove timestamps and clean up the log text."""
    # Split into lines and remove timestamps
    lines = []
    for line in log_text.split('\n'):
        # Remove timestamp pattern [HH:MM:SS.mmm]
        if line.strip():
            # Find the first ']' after a timestamp
            if ']' in line:
                timestamp_end = line.find(']') + 1
                line = line[timestamp_end:].strip()
            lines.append(line)
    
    return '\n'.join(lines)

def log_agent_interaction(agent_name: str, system_message: str, prompt: str, response: str):
    """Log agent interactions to a JSON file."""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
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

async def get_agent_command(log_file: str) -> dict:
    """Get the next command from the agent based on the game log."""
    # Create the specific session where the conversation will happen
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    logger.info(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")

    runner = Runner(
        agent=game_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    logger.info(f"Runner created for agent '{runner.agent.name}'")

    # Read the entire log file
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            log_text = f.read()
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return {"command": "look", "explanation": "Default command due to error reading log file"}

    # Clean the log text
    clean_text = clean_log_text(log_text)

    # Prepare the user's message in ADK format
    query = (
        "Here is the current game log. What should the next command be?\n\n" + clean_text + "\n\nRespond with ONLY the raw JSON object, nothing else. Do not use markdown or any extra text."
    )
    content = types.Content(role='user', parts=[types.Part(text=query)])

    final_response_text = "Agent did not produce a final response."  # Default

    # Run the agent and process events
    async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate:
                final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
            break

    # Log the agent interaction
    log_agent_interaction(
        "game_agent",
        game_agent.instruction,
        query,
        final_response_text
    )

    def extract_json(text):
        text = text.strip()
        # Remove triple backticks and optional 'json'
        text = re.sub(r'^```json\s*|^```|```$', '', text, flags=re.MULTILINE).strip()
        # Extract the first {...} block if extra text is present
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return match.group(0)
        return text

    try:
        # Parse the JSON response, cleaning up markdown if needed
        raw_json = extract_json(final_response_text)
        response = json.loads(raw_json)
        if not isinstance(response, dict) or 'command' not in response or 'explanation' not in response:
            raise ValueError("Invalid response format")
        return response
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error parsing agent response: {e}")
        return {"command": "look", "explanation": "Default command due to invalid response format"}

def log_agent_command(log_file: str, command_data: dict):
    """Add the agent's command and explanation to the log file with a timestamp."""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    command = command_data['command']
    explanation = command_data['explanation']
    log_entry = f"[{timestamp}] [AGENT] {command}\n"
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    
    # Print agent response in clean format
    print_agent_response(command)

async def get_story_narration(log_text: str, story_log: str) -> str:
    """Get story narration from the agent based on the game log and previous story."""
    # Create the specific session where the conversation will happen
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=f"{SESSION_ID}_story"
    )
    logger.info(f"Story session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}_story'")

    runner = Runner(
        agent=story_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    logger.info(f"Runner created for story agent '{runner.agent.name}'")

    # Prepare the user's message in ADK format
    query = (
        "You are narrating an interactive fiction story. Here are the last 3 narrations and the latest game events:\n\n"
        f"Previous narrations:\n{story_log}\n\n"
        f"Latest game events to narrate:\n{log_text}\n\n"
        "Create a new narration that:\n"
        "1. Only describes the new events that haven't been narrated yet\n"
        "2. Maintains continuity with previous narrations\n"
        "3. Is concise and engaging\n"
        "4. Includes any dialogue or important details\n"
        "5. Does not repeat information already narrated\n\n"
        "Respond with the new narration only."
    )
    content = types.Content(role='user', parts=[types.Part(text=query)])

    final_response_text = "Story agent did not produce a final response."  # Default

    # Run the agent and process events
    async for event in runner.run_async(user_id=USER_ID, session_id=f"{SESSION_ID}_story", new_message=content):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate:
                final_response_text = f"Story agent escalated: {event.error_message or 'No specific message.'}"
            break

    # Log the agent interaction
    log_agent_interaction(
        "story_narration",
        story_agent.instruction,
        query,
        final_response_text
    )

    return final_response_text.strip()

def log_story_narration(story_log_file: str, narration: str, update_decision: dict = None):
    """Add the story narration to the log file."""
    # Remove any leading/trailing whitespace
    narration = narration.strip()
    
    # Write to log file with double newline for readability
    with open(story_log_file, 'a', encoding='utf-8') as f:
        f.write(f"{narration}\n\n")
    
    # Print story narration with a single newline prefix and [STORY] tag
    print(f"\n[STORY] {narration}")

def get_story_log_filename(game_path: str) -> str:
    """Generate a story log filename based on game name and current timestamp."""
    # Extract game name from path (remove extension and path)
    game_name = os.path.splitext(os.path.basename(game_path))[0]
    
    # Create timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Return the full path
    return f'logs/{game_name}_{timestamp}_story.log'

def get_json_log_filename(game_path: str) -> str:
    """Generate a JSON log filename based on game name and current timestamp."""
    # Extract game name from path (remove extension and path)
    game_name = os.path.splitext(os.path.basename(game_path))[0]
    
    # Create timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Return the full path
    return f'logs/{game_name}_{timestamp}.json'

def log_game_update(json_log_file: str, game_output: str, if_agent_action: dict = None, story_updated: bool = False):
    """Log game updates to a JSON file."""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Create the log entry
    log_entry = {
        "timestamp": timestamp,
        "game_output": game_output,
        "if_agent_action": if_agent_action,
        "story_updated": story_updated
    }
    
    # Read existing entries or create new list
    try:
        with open(json_log_file, 'r', encoding='utf-8') as f:
            entries = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        entries = []
    
    # Append new entry
    entries.append(log_entry)
    
    # Write back to file
    with open(json_log_file, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2)

def update_last_json_entry(json_log_file: str, **kwargs):
    """Update the last entry in the JSON log file with additional information."""
    try:
        with open(json_log_file, 'r', encoding='utf-8') as f:
            entries = json.load(f)
        
        if entries:
            # Update the last entry with any provided fields
            entries[-1].update(kwargs)
            
            # Write back to file
            with open(json_log_file, 'w', encoding='utf-8') as f:
                json.dump(entries, f, indent=2)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error updating last JSON entry: {e}")

def get_last_n_updates(log_file: str, n: int = 3) -> str:
    """Get the last N dfrotz updates from the log file."""
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            # Read all lines
            lines = f.readlines()
            
            # Find the last N updates (each update starts with a timestamp)
            updates = []
            current_update = []
            update_count = 0
            
            # Process lines in reverse to find the last N updates
            for line in reversed(lines):
                if line.strip() and line[0] == '[':  # New update starts with timestamp
                    if current_update:
                        updates.append(''.join(reversed(current_update)))
                        current_update = []
                        update_count += 1
                        if update_count >= n:
                            break
                current_update.append(line)
            
            # Add the last update if we haven't reached N yet
            if current_update and update_count < n:
                updates.append(''.join(reversed(current_update)))
            
            # Return the updates in chronological order
            return ''.join(reversed(updates))
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return ""

def get_last_n_json_updates(json_log_file: str, n: int = 3) -> str:
    """Get the last N updates from the JSON log file."""
    try:
        with open(json_log_file, 'r', encoding='utf-8') as f:
            updates = json.load(f)
        
        # Get the last N updates
        last_updates = updates[-n:] if updates else []
        
        # Format each update
        formatted_updates = []
        for update in last_updates:
            formatted_update = f"[{update['timestamp']}] {update['game_output']}"
            if 'if_agent_action' in update:
                formatted_update += f"\n[AGENT] {update['if_agent_action']}"
            formatted_updates.append(formatted_update)
        
        return '\n\n'.join(formatted_updates)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error reading JSON log file: {e}")
        return ""

async def get_update_decision(json_log_file: str) -> dict:
    """Get decision from update_decidor_agent about whether to update the story."""
    # Create the specific session where the conversation will happen
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=f"{SESSION_ID}_update_decider"
    )
    logger.info(f"Update decider session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}_update_decider'")

    runner = Runner(
        agent=update_decidor_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    logger.info(f"Runner created for update decider agent '{runner.agent.name}'")

    # Get the last story update timestamp
    try:
        with open(json_log_file, 'r', encoding='utf-8') as f:
            updates = json.load(f)
        
        # Find the last story update
        last_story_update = None
        for update in reversed(updates):
            if update.get('story_updated', False):
                last_story_update = update
                break
        
        # Get all updates since the last story update
        if last_story_update:
            updates_since_last_story = [
                update for update in updates 
                if update['timestamp'] > last_story_update['timestamp']
            ]
        else:
            updates_since_last_story = updates
        
        # Format the updates for the agent
        formatted_updates = []
        for update in updates_since_last_story:
            formatted_update = f"[{update['timestamp']}] {update['game_output']}"
            if 'if_agent_action' in update:
                formatted_update += f"\n[AGENT] {update['if_agent_action']}"
            formatted_updates.append(formatted_update)
        
        updates_text = '\n\n'.join(formatted_updates)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error reading JSON log file: {e}")
        updates_text = ""

    # Prepare the user's message in ADK format
    query = (
        "Evaluate if there has been significant story progression since the last narration update.\n\n"
        f"Game events since last story update:\n{updates_text}\n\n"
        "Respond with a JSON object indicating if a story update is needed and why."
    )
    content = types.Content(role='user', parts=[types.Part(text=query)])

    final_response_text = "Update decider agent did not produce a final response."  # Default

    # Run the agent and process events
    async for event in runner.run_async(user_id=USER_ID, session_id=f"{SESSION_ID}_update_decider", new_message=content):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate:
                final_response_text = f"Update decider agent escalated: {event.error_message or 'No specific message.'}"
            break

    try:
        # Parse the JSON response
        decision = json.loads(final_response_text)
        
        # Log the agent interaction
        log_agent_interaction(
            "update_decidor",
            update_decidor_agent.instruction,
            query,
            final_response_text
        )
        
        return decision
    except json.JSONDecodeError:
        logger.error(f"Failed to parse update decider response as JSON: {final_response_text}")
        return {"should_update": False, "reason": "Failed to parse agent response"}

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run a text-based game with AI agents')
    parser.add_argument('game_path', nargs='?', default='games/905.z5',
                      help='Path to the game file (default: games/905.z5)')
    parser.add_argument('--tts', action='store_true', help='Enable text-to-speech')
    args = parser.parse_args()

    # Override TTS setting if specified in arguments
    if args.tts:
        global USE_TTS
        USE_TTS = True

    # Initialize TTS handler if enabled
    tts_handler = TTSHandler() if USE_TTS else None

    # Get log file paths
    story_log_file = get_story_log_filename(args.game_path)
    json_log_file = get_json_log_filename(args.game_path)

    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    # Initialize story log file
    with open(story_log_file, 'w', encoding='utf-8') as f:
        pass

    # Initialize JSON log file
    with open(json_log_file, 'w', encoding='utf-8') as f:
        json.dump([], f)

    # Initialize the game runner
    runner = FrotzRunner(args.game_path)
    
    try:
        # Start the game
        runner.start()
        
        # Main game loop
        while True:
            # Get game output (non-blocking)
            game_output = runner.get_output()
            if game_output:
                # Print game output
                print_game_output(game_output)
                
                # Log the game update
                log_game_update(json_log_file, game_output)
                
                # Get update decision
                update_decision = asyncio.run(get_update_decision(json_log_file))
                
                if update_decision.get('should_update', False):
                    # Get the last few updates for context
                    last_updates = get_last_n_json_updates(json_log_file)
                    last_story = get_last_n_updates(story_log_file)
                    
                    # Get story narration
                    narration = asyncio.run(get_story_narration(last_updates, last_story))
                    
                    # Log the narration
                    log_story_narration(story_log_file, narration, update_decision)
                    
                    # Update the last JSON entry with story info
                    update_last_json_entry(json_log_file, story_updated=True, story_narration=narration)
                    
                    # Use TTS if enabled
                    if tts_handler:
                        tts_handler.speak(narration)
                
                # Get agent command
                command_data = asyncio.run(get_agent_command(runner.log_file))
                
                # Log and execute the command
                log_agent_command(runner.log_file, command_data)
                runner.send_command(command_data['command'])
                
                # Wait for key press if enabled
                wait_for_key()
            else:
                # Sleep briefly to avoid busy-waiting
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nGame terminated by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        traceback.print_exc()
    finally:
        # Clean up
        runner.quit()
        if tts_handler:
            tts_handler.stop()

if __name__ == "__main__":
    main()
