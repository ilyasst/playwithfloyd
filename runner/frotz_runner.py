import subprocess
import os
import time
import logging
from datetime import datetime
import sys
import json
import select
import fcntl
from utils.logging_utils import get_logger

# Get the Frotz logger
logger = get_logger('frotz')

class FrotzRunner:
    def __init__(self, game_path: str, frotz_path: str = '/opt/homebrew/bin/dfrotz'):
        self.game_path = game_path
        self.frotz_path = frotz_path
        self.process = None
        self.log_file = None
        self.json_log_file = None
        self.output_buffer = []
        self.partial_line = ''
        self._stdout_fd = None
        self._stdin_fd = None
        self._alive = False

        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        game_name = os.path.splitext(os.path.basename(game_path))[0]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = os.path.join('logs', f'{game_name}_{timestamp}.log')
        self.json_log_file = os.path.join('logs', f'{game_name}_{timestamp}.json')
        with open(self.json_log_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        logger.info(f"Initialized FrotzRunner with game: {game_path}")
        logger.info(f"Log file: {self.log_file}")
        logger.info(f"JSON log file: {self.json_log_file}")

    def start(self):
        if self.process is not None:
            return
        logger.info("Starting dfrotz process with subprocess...")
        self.process = subprocess.Popen(
            [self.frotz_path, self.game_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0
        )
        self._stdout_fd = self.process.stdout.fileno()
        self._stdin_fd = self.process.stdin.fileno()
        # Set stdout to non-blocking
        fl = fcntl.fcntl(self._stdout_fd, fcntl.F_GETFL)
        fcntl.fcntl(self._stdout_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        self._alive = True

    def get_output(self) -> str:
        if not self.process or not self._alive:
            return ''
        output = ''
        try:
            while True:
                chunk = self.process.stdout.read(1024)
                if not chunk:
                    break
                text = chunk.decode(errors='replace')
                output += text
        except Exception:
            pass
        if output:
            self._log_output(output)
        return output

    def send_command(self, command: str):
        if not self.process or not self._alive:
            return
        if command.strip().upper() == 'ENTER':
            to_send = '\n'
        else:
            to_send = command.strip() + '\n'
        try:
            self.process.stdin.write(to_send.encode())
            self.process.stdin.flush()
        except Exception as e:
            logger.error(f"Failed to send command: {e}")

    def _log_output(self, output: str):
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        for line in output.splitlines():
            log_entry = f"[{timestamp}] {line}\n"
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            self.output_buffer.append(line)

    def quit(self):
        if self.process is not None:
            logger.info("Terminating process")
            self.process.terminate()
            self.process = None
            self._alive = False

    def __del__(self):
        self.quit()

    def interactive(self):
        """
        Runs the game interactively (for manual play/testing).
        """
        os.execv(self.frotz_path, [self.frotz_path, self.game_path]) 