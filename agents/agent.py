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

# Define the story narration agent
story_agent = Agent(
    name="story_narration_agent",
    model="gemini-2.0-flash",
    description="An agent that narrates the story based on the game's output and previous narration.",
    instruction=(
        "You are a story narrator for an interactive fiction game. "
        "Based on the latest game output and the previous story narration, "
        "create a compelling narrative that describes what just happened in the game. "
        "Your narration should be engaging, short, and maintain continuity with previous story elements. "
        "Focus on describing the current scene, actions, and any significant changes in the story. "
        "Keep your style concise, short and direct. Focus on the changes and actions. "
        "Your answers need to be concise. "
        "Do not mention that this is a game, don't break character. "
        "Don't invent any backstory. "
        "Always include all dialogues in the narration. "
        "Error messages from the game engine should be ignored. "
        "Ensure that there are no repetitions in the narration. "
    ),
    tools=[]
)