from runner.frotz_runner import FrotzRunner
import sys
import traceback
import logging
import os
import argparse
import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from agents.agent import game_agent, story_agent
from datetime import datetime
import select
import time
from google.genai import types
from dotenv import load_dotenv
from collections import deque
import json
from tts_handler import TTSHandler

# Load environment variables from .env file
load_dotenv()

# Get TTS configuration from environment
USE_TTS = os.getenv('USE_TTS', 'false').lower() == 'true'

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
    """Wait for any key press to continue."""
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

async def get_agent_command(log_file: str) -> str:
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
        return "look"

    # Clean the log text
    clean_text = clean_log_text(log_text)

    # Prepare the user's message in ADK format
    query = "Here is the current game log. What should the next command be?\n\n" + clean_text + "\n\nRespond with the next command only."
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

    return final_response_text.strip()

def log_agent_command(log_file: str, command: str):
    """Add the agent's command to the log file with a timestamp."""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
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

    # Extract complete narrations from the story log
    narrations = []
    current_narration = []
    in_narration = False
    
    for line in story_log.split('\n'):
        if '[STORY NARRATION]' in line:
            # Start of a new narration
            if current_narration:
                narrations.append('\n'.join(current_narration))
            current_narration = [line.split('[STORY NARRATION]')[1].strip()]
            in_narration = True
        elif in_narration and line.strip():
            # Continue current narration
            current_narration.append(line.strip())
        elif in_narration and not line.strip():
            # End of current narration
            if current_narration:
                narrations.append('\n'.join(current_narration))
            current_narration = []
            in_narration = False
    
    # Add the last narration if we're still in one
    if current_narration:
        narrations.append('\n'.join(current_narration))
    
    # Get the last 3 complete narrations
    last_narrations = narrations[-3:] if narrations else []
    previous_story = '\n\n'.join(last_narrations)

    # Prepare the user's message in ADK format
    query = (
        "You are narrating an interactive fiction story. Here are the last 3 narrations and the latest game events:\n\n"
        f"Previous narrations:\n{previous_story}\n\n"
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

    return final_response_text.strip()

def log_story_narration(story_log_file: str, narration: str):
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

def log_game_update(json_log_file: str, game_output: str, if_agent_action: str = None):
    """Add a game update to the JSON log file."""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    
    # Create the update object
    update = {
        "timestamp": timestamp,
        "game_output": game_output
    }
    
    # Add optional fields if they exist
    if if_agent_action:
        update["if_agent_action"] = if_agent_action
    
    # Read existing updates or create new list
    try:
        with open(json_log_file, 'r', encoding='utf-8') as f:
            updates = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        updates = []
    
    # Append new update
    updates.append(update)
    
    # Write back to file
    with open(json_log_file, 'w', encoding='utf-8') as f:
        json.dump(updates, f, indent=2)

def update_last_json_entry(json_log_file: str, **kwargs):
    """Update the last entry in the JSON log file with additional fields."""
    try:
        with open(json_log_file, 'r', encoding='utf-8') as f:
            updates = json.load(f)
        
        if updates:
            # Update the last entry with any provided fields
            updates[-1].update(kwargs)
            
            with open(json_log_file, 'w', encoding='utf-8') as f:
                json.dump(updates, f, indent=2)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error updating JSON: {e}")

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

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run a text-based game with Frotz')
    parser.add_argument('game_path', nargs='?', default='games/905.z5',
                      help='Path to the game file (default: games/905.z5)')
    args = parser.parse_args()

    # Initialize TTS if enabled
    tts = None
    if USE_TTS:
        try:
            tts = TTSHandler()
            logger.info("TTS Handler initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TTS: {e}")
            logger.info("Continuing without TTS support")
    else:
        logger.info("TTS is disabled")

    # Create story log file with dynamic name
    story_log_file = get_story_log_filename(args.game_path)
    json_log_file = get_json_log_filename(args.game_path)
    
    # Initialize story log file
    with open(story_log_file, 'w', encoding='utf-8') as f:
        f.write("")  # Create empty file

    # Check if game file exists
    if not os.path.exists(args.game_path):
        print(f"Error: Game file not found at {args.game_path}")
        print("Please make sure the game file exists and update the path in the script.")
        return

    logger.info(f"Starting game: {args.game_path}")
    runner = None
    
    try:
        logger.info("Initializing FrotzRunner")
        runner = FrotzRunner(args.game_path)
        
        # Start the game and get the initial output
        logger.info("Starting game...")
        
        # Create PTY for game
        pid, fd = os.forkpty()
        if pid == 0:
            # Child process: run dfrotz
            os.execv(runner.frotz_path, [runner.frotz_path, args.game_path])
        else:
            # Parent process: handle game interaction
            buffer = ''
            last_output_time = time.time()
            fd_eof = False
            turn_counter = 0  # Counter for game turns
            
            while True:
                try:
                    # Read game output
                    rlist = [fd]
                    ready, _, _ = select.select(rlist, [], [], 0.1)
                    now = time.time()
                    
                    for ready_fd in ready:
                        if ready_fd == fd:
                            try:
                                data = os.read(fd, 1024)
                                if not data:
                                    fd_eof = True
                                    break
                                
                                text = data.decode(errors='replace')
                                for char in text:
                                    if char == '\n':
                                        # Log to file
                                        runner._log_output(buffer)
                                        # Print to console with the newline
                                        print_game_output(buffer + '\n')
                                        buffer = ''
                                    else:
                                        buffer += char
                                        if buffer.endswith('***MORE***'):
                                            # Log to file
                                            runner._log_output(buffer)
                                            # Print to console without extra newline
                                            print_game_output(buffer)
                                            buffer = ''
                            except OSError:
                                fd_eof = True
                                break
                    
                    # If no output for 1 second, get command from agent
                    if not ready and (now - last_output_time) > 1.0:
                        # Log any remaining buffer as a complete update
                        if buffer:
                            runner._log_output(buffer, True)
                            buffer = ''
                        
                        # Get last 3 updates for both agents
                        recent_log = get_last_n_updates(runner.log_file, 3)
                        
                        # Read previous story narration
                        with open(story_log_file, 'r') as f:
                            story_log = f.read()
                        
                        # Get story narration from agent every 3 turns
                        if turn_counter % 3 == 0:
                            # Get the story thus far
                            with open(story_log_file, 'r') as f:
                                story_thus_far = f.read().strip()
                            
                            # Get the last 3 game updates
                            recent_updates = get_last_n_json_updates(json_log_file, 3)
                            
                            # Prepare the prompt
                            prompt = (
                                "The story thus far:\n\n"
                                f"{story_thus_far}\n\n"
                                "Game Log to narrate:\n\n"
                                f"{recent_updates}\n\n"
                                "Create a new narration that:\n"
                                "1. Only describes the new events that haven't been narrated yet\n"
                                "2. Maintains continuity with previous narrations\n"
                                "3. Is concise and engaging\n"
                                "4. Includes any dialogue or important details\n"
                                "5. Does not repeat information already narrated\n\n"
                                "Respond with the new narration only."
                            )
                            
                            narration = asyncio.run(get_story_narration(recent_updates, story_thus_far))
                            print(f"Story agent suggests narration: {narration}")
                            if narration and narration.strip():  # Only log if there's actual narration
                                logger.info(f"Story agent suggests narration: {narration}")
                                log_story_narration(story_log_file, narration)
                                
                                # Speak the narration if TTS is available
                                if tts:
                                    try:
                                        tts.speak(narration)
                                    except Exception as e:
                                        logger.error(f"TTS error: {e}")
                        
                        # Get command from game agent
                        command = asyncio.run(get_agent_command(runner.log_file))
                        logger.info(f"Game agent suggests command: {command}")
                        
                        # Log the agent's command
                        log_agent_command(runner.log_file, command)
                        update_last_json_entry(json_log_file, if_agent_action=command)
                        
                        # Send command to game
                        if command.upper() == 'ENTER':
                            os.write(fd, b'\n')
                        else:
                            os.write(fd, (command + '\n').encode())
                        
                        turn_counter += 1  # Increment turn counter after each command
                        last_output_time = now
                        
                        # Wait for key press before continuing
                        wait_for_key()
                    
                    if fd_eof:
                        if buffer:
                            runner._log_output(buffer, True)
                            print_game_output(buffer)
                        logger.info("Game process completed")
                        break
                        
                except KeyboardInterrupt:
                    logger.info("Received keyboard interrupt")
                    print("\nQuitting game...")
                    break
                except Exception as e:
                    logger.error(f"Error during gameplay: {e}", exc_info=True)
                    print(f"Error during gameplay: {e}")
                    traceback.print_exc()
                    break
                
    except Exception as e:
        logger.error(f"Failed to start game: {e}", exc_info=True)
        print(f"Failed to start game: {e}")
        traceback.print_exc()
    finally:
        # Ensure we clean up the process
        if runner:
            logger.info("Cleaning up runner")
            runner.quit()
        logger.info("Game closed.")
        print("Game closed.")

if __name__ == '__main__':
    main()
