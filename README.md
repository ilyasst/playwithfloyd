# Text-Based Autoplay

A modular framework for running and interacting with Z-machine games (e.g., .z5, .z3) using the Frotz interpreter, designed for agent-based play and research.

## Project Structure

```
text-based-autploay/
│
├── games/                  # Z-machine game files (.z5, .z3, etc.)
│   └── 905.z5
│
├── runner/                 # Game runner module
│   ├── __init__.py
│   └── frotz_runner.py     # FrotzRunner class for running/interacting with Frotz
│
├── agents/                 # (For future) Agent logic, planners, etc.
│   └── __init__.py
│
├── tests/                  # Test scripts
│
├── requirements.txt
└── README.md
```

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
