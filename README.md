# Text-Based Autoplay

An AI-powered framework for playing Z-machine games (e.g., .z5, .z3) using the Frotz interpreter. Features automated gameplay with AI agents and story narration.

## Quick Start

1. Install dependencies:
```bash
brew install python@3.11 frotz google-cloud-sdk
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Set up Google Cloud:
```bash
gcloud auth login
gcloud config set project [PROJECT_NAME]
gcloud auth application-default login
```

3. Configure environment variables in `.env`:
```
USE_TTS=false        # Enable/disable text-to-speech narration
WAIT_FOR_KEY=true    # Enable/disable key press after each command
```

4. Run a game:
```bash
python main.py [path/to/game.z5]
```

## Features

- AI-powered gameplay using Google's Gemini model
- Automated story narration
- Optional text-to-speech narration
- JSON and text-based logging
- Interactive or automated play modes

## Project Structure

```
.
├── agents/          # AI agent definitions
├── games/          # Z-machine game files
├── logs/           # Game and narration logs
├── runner/         # Frotz game runner
├── main.py         # Main game loop
├── tts_handler.py  # Text-to-speech support
└── requirements.txt
```

## Requirements

- Python 3.11+
- Frotz interpreter
- Google Cloud SDK
- Dependencies in requirements.txt

## License

MIT License - see LICENSE file for details
