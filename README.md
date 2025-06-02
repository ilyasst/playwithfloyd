# Text-Based Autoplay

A modular framework for running and interacting with Z-machine games (e.g., .z5, .z3) using the Frotz interpreter, designed for agent-based play and research.

## Installation

You need python 3.11 venv at most: `brew install python@3.11`

You also need google-cloud-sdk: `brew install --cask google-cloud-sdk`

You also need frotz: `brew install frotz`

The rest can be installed from `requirements.txt`

### Setup your gcloud

Check it's installed: `gcloud --version`

Authenticate: `gcloud auth login`

Set your project with: `gcloud config set project [PROJECT_NAME]`

For some reason, you also have to do this: `gcloud auth application-default login`

## Requirements
- Python 3.8+
- [dfrotz](https://github.com/DavidGriffith/frotz) (install via Homebrew: `brew install frotz`)
- Python package: `pyfrotz`

## Usage

### Running a Game Programmatically

Use the `FrotzRunner` class in `runner/frotz_runner.py`:

```python
from runner.frotz_runner import FrotzRunner

runner = FrotzRunner('games/905.z5')
output = runner.run_commands(['look', 'inventory'])
print(output)
```

### Interactive Play

```python
runner = FrotzRunner('games/905.z5')
runner.interactive()
```

## Next Steps
- Implement agent logic in `agents/`
- Build a knowledge base and decision-making system for automated play

---

This project is under active development.
