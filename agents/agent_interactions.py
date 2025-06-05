import json
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from utils.logging_utils import main_logger as logger, log_agent_interaction
from utils.text_utils import clean_log_text, extract_json
from agents.agent import game_agent, update_decidor_agent

# Define constants for identifying the interaction context
APP_NAME = "text_game_app"
USER_ID = "game_user"
SESSION_ID = "game_session_001"

# Create a session service for the agent
session_service = InMemorySessionService()

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

async def get_update_decision(json_log_file: str) -> dict:
    """Get a decision from the update decider agent about whether to update the story."""
    # Create the specific session where the conversation will happen
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=f"{SESSION_ID}_update"
    )
    logger.info(f"Update session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}_update'")

    runner = Runner(
        agent=update_decidor_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    logger.info(f"Runner created for update decider agent '{runner.agent.name}'")

    # Read the last few updates
    try:
        with open(json_log_file, 'r', encoding='utf-8') as f:
            entries = json.load(f)
            last_updates = entries[-3:]  # Get last 3 updates
    except (FileNotFoundError, json.JSONDecodeError):
        last_updates = []

    # Prepare the user's message in ADK format
    query = (
        "Here are the last few game updates. Should the story be updated?\n\n" +
        json.dumps(last_updates, indent=2) + "\n\n" +
        "Respond with ONLY a JSON object containing a 'should_update' boolean and a 'reason' string."
    )
    content = types.Content(role='user', parts=[types.Part(text=query)])

    final_response_text = "Update decider did not produce a final response."  # Default

    # Run the agent and process events
    async for event in runner.run_async(user_id=USER_ID, session_id=f"{SESSION_ID}_update", new_message=content):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate:
                final_response_text = f"Update decider escalated: {event.error_message or 'No specific message.'}"
            break

    # Log the agent interaction
    log_agent_interaction(
        "update_decider",
        update_decidor_agent.instruction,
        query,
        final_response_text
    )

    try:
        # Parse the JSON response, cleaning up markdown if needed
        raw_json = extract_json(final_response_text)
        response = json.loads(raw_json)
        if not isinstance(response, dict) or 'should_update' not in response or 'reason' not in response:
            raise ValueError("Invalid response format")
        return response
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error parsing update decider response: {e}")
        return {"should_update": False, "reason": "Default decision due to invalid response format"} 