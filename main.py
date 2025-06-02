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

# Load environment variables from .env file
load_dotenv()

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
    print(f"\n{text}", end='', flush=True)

def print_agent_response(command: str):
    """Print agent response in a clean format."""
    print(f"\n[AGENT] {command}")

async def get_agent_command(log_text: str) -> str:
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

    # Prepare the user's message in ADK format
    query = "Here is the current game log. What should the next command be?\n\n" + log_text + "\n\nRespond with the next command only."
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

    # Prepare the user's message in ADK format
    query = f"Here is the current game log and previous story narration.\n\n The story narration you created until now:\n\nPrevious Story:\n{story_log}\n\n Create a narrative for the latest events only if new information is available:\n\nGame Log to narrate:\n{log_text}\n\nRespond with the story narration only of the Game Log to narrate."
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

def log_story_narration(story_log_file: str, narration: str, prompt: str):
    """Add the story narration and prompt to the log file with a timestamp."""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    log_entry = f"[{timestamp}] [STORY PROMPT]\n{prompt}\n\n[{timestamp}] [STORY NARRATION]\n{narration}\n\n"
    
    with open(story_log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    
    # Print story narration in clean format
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

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run a text-based game with Frotz')
    parser.add_argument('game_path', nargs='?', default='games/905.z5',
                      help='Path to the game file (default: games/905.z5)')
    args = parser.parse_args()

    # Create story log file with dynamic name
    story_log_file = get_story_log_filename(args.game_path)
    with open(story_log_file, 'w', encoding='utf-8') as f:
        f.write(f"Story Narration Log for {os.path.basename(args.game_path)}\n")
        f.write("=" * 50 + "\n\n")

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
                                        # Print to console
                                        print_game_output(buffer)
                                        buffer = ''
                                    else:
                                        buffer += char
                                        if buffer.endswith('***MORE***'):
                                            # Log to file
                                            runner._log_output(buffer)
                                            # Print to console
                                            print_game_output(buffer)
                                            buffer = ''
                            except OSError:
                                fd_eof = True
                                break
                    
                    # If no output for 1 second, get command from agent
                    if not ready and (now - last_output_time) > 1.0:
                        # Get last 3 updates for both agents
                        recent_log = get_last_n_updates(runner.log_file, 3)
                        
                        # Read previous story narration
                        with open(story_log_file, 'r') as f:
                            story_log = f.read()
                        
                        # Get story narration from agent every 3 turns
                        if turn_counter % 3 == 0:
                            # Prepare the prompt
                            prompt = f"Here is the current game log and previous story narration.\n\n The story narration you created until now:\n\nPrevious Story:\n{story_log}\n\n Create a narrative for the latest events only if new information is available:\n\nGame Log to narrate:\n{recent_log}\n\nRespond with the story narration only of the Game Log to narrate."
                            
                            narration = asyncio.run(get_story_narration(recent_log, story_log))
                            print(f"Story agent suggests narration: {narration}")
                            if narration and narration.strip():  # Only log if there's actual narration
                                logger.info(f"Story agent suggests narration: {narration}")
                                log_story_narration(story_log_file, narration, prompt)
                        
                        # Get command from game agent
                        command = asyncio.run(get_agent_command(recent_log))
                        logger.info(f"Game agent suggests command: {command}")
                        
                        # Log the agent's command
                        log_agent_command(runner.log_file, command)
                        
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
                            runner._log_output(buffer)
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
