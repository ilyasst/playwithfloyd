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
        """
        You are playing an interactive fiction game. 
        Read the current log and suggest the next command to send to the game. 
        If you see a prompt like '>', or '***MORE***', respond with the next logical command or 'ENTER' if needed. 
        You can rely on the following guide to learn how to play the game: 
        =========================================
Communicating with Interactive Fiction ||
=========================================

With Interactive Fiction, you type your commands in plain English each
time you see the prompt which looks like this:

>

Most of the sentences that the stories understand are imperative
sentences.  See the examples below.

When you have finished typing your input, press the ENTER (or RETURN) key.
The story will then respond, telling you whether your request is possible
at this point in the story, and what happened as a result.

The story recognizes your words by their first six letters, and all
subsequent letters are ignored.  Therefore, CANDLE, CANDLEs, and
CANDLEstick would all be treated as the same word.  Most stories don't
care about capitalization, so you can just type in all-lowercase if you
like.

To move around, just type the direction you want to go.  Directions can be
abbreviated:  NORTH to N, SOUTH to S, EAST to E, WEST to W, NORTHEAST to
NE, NORTHWEST to NW, SOUTHEAST to SE, SOUTHWEST to SW, UP to U, and DOWN
to D.  IN and OUT will also work in certain places.

There are many differnet kinds of sentences used in Interactive Fiction.
Here are some examples:

> WALK TO THE NORTH
> WEST
> NE
> DOWN
> TAKE THE BIRDCAGE
> READ ABOUT DIMWIT FLATHEAD
> LOOK UP MEGABOZ IN THE ENCYCLOPEDIA
> LIE DOWN IN THE PINK SOFA
> EXAMINE THE SHINY COIN
> PUT THE RUSTY KEY IN THE CARDBOARD BOX
> SHOW MY BOW TIE TO THE BOUNCER
> HIT THE CRAWLING CRAB WITH THE GIANT NUTCRACKER
> ASK THE COWARDLY KING ABOUT THE CROWN JEWELS

You can use multiple objects with certain verbs if you separate them by
the word "AND" or by a comma.  Here are some examples:

> TAKE THE BOOK AND THE FROG
> DROP THE JAR OF PEANUT BUTTER, THE SPOON, AND THE LEMMING FOOD
> PUT THE EGG AND THE PENCIL IN THE CABINET

You can include several inputs on one line if you separate them by the
word "THEN" or by a period.  Each input will be handled in order, as
though you had typed them individually at seperate prompts.  For example,
you could type all of the following at once, before pressing the ENTER (or
RETURN) key:

> TURN ON THE LIGHT. TAKE THE BOOK THEN READ ABOUT THE JESTER IN THE BOOK

If the story doesn't understand one of the sentences on your input line,
or if an unusual event occurs, it will ignore the rest of your input line.

The words "IT" and "ALL" can be very useful.  For example:

> EXAMINE THE APPLE.  TAKE IT.  EAT IT
> CLOSE THE HEAVY METAL DOOR.  LOCK IT
> PICK UP THE GREEN BOOT.  SMELL IT.  PUT IT ON.
> TAKE ALL
> TAKE ALL THE TOOLS
> DROP ALL THE TOOLS EXCEPT THE WRENCH AND MINIATURE HAMMER
> TAKE ALL FROM THE CARTON
> GIVE ALL BUT THE RUBY SLIPPERS TO THE WICKED WITCH

The word "ALL" refers to every visible object except those inside
something else.  If there were an apple on the ground and an orange inside
a cabinet, "TAKE ALL" would take the apple but not the orange.

There are three kinds of questions you can ask:  "WHERE IS (something)",
"WHAT IS (something)", and "WHO IS (someone)".  For example:

> WHO IS LORD DIMWIT?
> WHAT IS A GRUE?
> WHERE IS EVERYBODY?

When you meet intelligent creatures, you can talk to them by typing their
name, then a comma, then whatever you want to say to them.  Here are some
examples:

> JESTER, HELLO
> GUSTAR WOOMAX, TELL ME ABOUT THE COCONUT
> UNCLE OTTO, GIVE ME YOUR WALLET
> HORSE, WHERE IS YOUR SADDLE?
> BOY, RUN HOME THEN CALL THE POLICE
> MIGHTY WIZARD, TAKE THIS POISONED APPLE.  EAT IT

Notice that in the last two examples, you are giving the characters more
than one command on the same input line.  Keep in mind, however, that many
creatures don't care for idle chatter; your actions will speak louder than
your words.
"""
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
        "Your task is to create engaging, concise narrations based on the latest game events. "
        "Important guidelines:\n"
        "1. Only narrate new events that haven't been described in the story so far\n"
        "2. Maintain continuity with previous narrations\n"
        "3. Keep your style concise and direct\n"
        "4. Include all dialogue and important details\n"
        "5. Never repeat information that was already narrated\n"
        "6. Ignore error messages from the game enging\n"
        "7. Don't mention that this is a game or break character\n"
        "8. Don't invent details not present in the game output\n"
        "9. Focus on describing actions, changes, and important discoveries"
    ),
    tools=[]
)

# Define the update decider agent
update_decidor_agent = Agent(
    name="update_decidor_agent",
    model="gemini-2.0-flash",
    description="An agent that evaluates story progression in an interactive fiction game.",
    instruction=(
        "You are an agent that evaluates story progression in an interactive fiction game. "
        "Your task is to determine if there has been significant story advancement since the last narration update. "
        "You must respond with ONLY a JSON object in the following exact format (no markdown, no code blocks, just the raw JSON):\n"
        '{"should_update": true/false, "reason": "Brief explanation of why an update is needed or not"}\n\n'
        "Consider the following criteria for story advancement:\n"
        "1. New locations discovered or visited\n"
        "2. New items found or used\n"
        "3. New characters encountered or interacted with\n"
        "4. Important dialogue or revelations\n"
        "5. Significant changes in the game state\n"
        "6. Progress towards game objectives\n\n"
        "IMPORTANT: Return ONLY the raw JSON object, nothing else. No markdown formatting, no code blocks, no additional text."
    ),
    tools=[]
)