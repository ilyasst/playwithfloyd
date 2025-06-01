import subprocess
import os
import time
import logging
from datetime import datetime

# Set up logging with timestamps
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('FrotzRunner')

class FrotzRunner:
    def __init__(self, game_path: str, frotz_path: str = '/opt/homebrew/bin/dfrotz'):
        self.game_path = game_path
        self.frotz_path = frotz_path
        self.process = None
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Generate log filename with game name and timestamp
        game_name = os.path.splitext(os.path.basename(game_path))[0]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = os.path.join('logs', f'{game_name}_{timestamp}.log')
        
        logger.info(f"Initialized FrotzRunner with game: {game_path}")
        logger.info(f"Log file: {self.log_file}")

    def _log_output(self, output: str):
        """Log output to both the logger and the log file."""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_entry = f"[{timestamp}] {output}\n"
        
        # Log to file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        # Log to console
        logger.debug(output)

    def start(self):
        """Start the dfrotz process and log all output, including prompts without newlines."""
        if self.process is None:
            try:
                logger.info("Starting dfrotz process...")
                cmd = [self.frotz_path, self.game_path]
                logger.debug(f"Running command: {' '.join(cmd)}")
                
                # Start the process with a pseudo-terminal
                self.process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=0  # unbuffered
                )
                
                buffer = ''
                while True:
                    char = self.process.stdout.read(1)
                    if not char:
                        if buffer:
                            self._log_output(buffer)
                        break
                    if char == '\n':
                        self._log_output(buffer)
                        buffer = ''
                    else:
                        buffer += char
                        # If we see the MORE prompt, log it immediately
                        if buffer.endswith('***MORE***'):
                            self._log_output(buffer)
                            buffer = ''
                
                logger.info("Game process completed")
            except Exception as e:
                logger.error(f"Failed to start game: {str(e)}")
                if self.process:
                    logger.info("Terminating failed process")
                    self.process.terminate()
                    self.process = None
                raise Exception(f"Failed to start game: {str(e)}")

    def quit(self):
        """Clean up the process."""
        if self.process is not None:
            logger.info("Terminating process")
            self.process.terminate()
            self.process = None

    def __del__(self):
        """Ensure process is cleaned up when object is destroyed."""
        self.quit()

    def interactive(self):
        """
        Runs the game interactively (for manual play/testing).
        """
        os.execv(self.frotz_path, [self.frotz_path, self.game_path]) 