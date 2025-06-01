import subprocess
import os
from typing import List, Optional

class FrotzRunner:
    def __init__(self, game_path: str, frotz_path: str = '/opt/homebrew/bin/dfrotz'):
        self.game_path = game_path
        self.frotz_path = frotz_path
        self.process = None

    def run_commands(self, commands: List[str], timeout: Optional[float] = 5.0) -> str:
        """
        Runs the game with a list of commands and returns the output.
        """
        input_str = '\n'.join(commands + ['quit']) + '\n'
        result = subprocess.run(
            [self.frotz_path, self.game_path],
            input=input_str,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout

    def interactive(self):
        """
        Runs the game interactively (for manual play/testing).
        """
        os.execv(self.frotz_path, [self.frotz_path, self.game_path]) 