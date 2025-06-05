import sys
import select
import os

# Get wait for key configuration from environment
WAIT_FOR_KEY = os.getenv('WAIT_FOR_KEY', 'true').lower() == 'true'

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