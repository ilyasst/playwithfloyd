from runner.frotz_runner import FrotzRunner
import sys
import traceback
import logging
import os
import argparse
import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from agents.agent import game_agent
from datetime import datetime
import select
import time
from google.genai import types
from dotenv import load_dotenv

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

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run a text-based game with Frotz')
    parser.add_argument('game_path', nargs='?', default='games/905.z5',
                      help='Path to the game file (default: games/905.z5)')
    args = parser.parse_args()

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
                        # Read current log
                        with open(runner.log_file, 'r') as f:
                            log_text = f.read()
                        
                        # Get command from agent
                        command = asyncio.run(get_agent_command(log_text))
                        logger.info(f"Agent suggests command: {command}")
                        
                        # Log the agent's command
                        log_agent_command(runner.log_file, command)
                        
                        # Send command to game
                        if command.upper() == 'ENTER':
                            os.write(fd, b'\n')
                        else:
                            os.write(fd, (command + '\n').encode())
                        
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
