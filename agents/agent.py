import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent

# Define a tool for the agent to use (optional, for more advanced actions)
def send_command_to_game(command: str) -> dict:
    """Send a command to the game (placeholder for now)."""
    # You can implement actual game interaction here if needed
    return {"status": "success", "command_sent": command}


# Define the agent
game_agent = Agent(
    name="if_game_agent",
    model="gemini-2.0-flash",  # Or another supported model
    description="An agent that plays interactive fiction games by reading the log and suggesting the next command.",
    instruction=(
        "You are playing an interactive fiction game. "
        "Read the current log and suggest the next command to send to the game. "
        "If you see a prompt like '>', or '***MORE***', respond with the next logical command or 'ENTER' if needed."
    ),
    tools=[send_command_to_game]
)