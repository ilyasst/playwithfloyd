from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from utils.logging_utils import main_logger as logger, log_agent_interaction
from agents.agent import story_agent

# Define constants for identifying the interaction context
APP_NAME = "text_game_app"
USER_ID = "game_user"
SESSION_ID = "game_session_001"

# Create a session service for the agent
session_service = InMemorySessionService()

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

    return final_response_text 