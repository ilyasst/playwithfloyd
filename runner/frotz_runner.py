import subprocess
import os
import time
import logging
from datetime import datetime
import sys
import select

# Set up logging with timestamps
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
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
        """Log output to both the log file and print to terminal (no DEBUG logger)."""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_entry = f"[{timestamp}] {output}\n"
        
        # Log to file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        # Explicitly print to main terminal
        print(log_entry, end='')

    def start(self):
        """Start dfrotz in a PTY, log all output, and allow user to inject commands after 1s of inactivity."""
        if self.process is not None:
            return
        try:
            logger.info("Starting dfrotz process in PTY mode...")
            cmd = [self.frotz_path, self.game_path]
            logger.debug(f"Running command: {' '.join(cmd)}")

            pid, fd = os.forkpty()
            if pid == 0:
                # Child process: replace with dfrotz
                os.execv(self.frotz_path, cmd)
            else:
                # Parent process: interact with PTY
                buffer = ''
                last_output_time = time.time()
                fd_eof = False
                while True:
                    rlist = [fd, sys.stdin]
                    ready, _, _ = select.select(rlist, [], [], 0.1)
                    now = time.time()
                    output_received = False
                    for ready_fd in ready:
                        if ready_fd == fd:
                            try:
                                data = os.read(fd, 1024)
                                if not data:
                                    fd_eof = True
                                    break
                                output_received = True
                                last_output_time = now
                                text = data.decode(errors='replace')
                                for char in text:
                                    if char == '\n':
                                        self._log_output(buffer)
                                        buffer = ''
                                    else:
                                        buffer += char
                                        if buffer.endswith('***MORE***'):
                                            self._log_output(buffer)
                                            buffer = ''
                            except OSError:
                                fd_eof = True
                                break
                        elif ready_fd == sys.stdin:
                            user_input = sys.stdin.readline().rstrip('\n')
                            if user_input.strip().upper() == 'ENTER':
                                os.write(fd, b'\n')
                                print('[Sent ENTER to dfrotz]')
                            elif user_input:
                                os.write(fd, (user_input + '\n').encode())
                                print(f'[Sent "{user_input}" to dfrotz]')
                    if fd_eof:
                        if buffer:
                            self._log_output(buffer)
                        logger.info("Game process completed")
                        break
                    if not output_received and (now - last_output_time) > 1.0:
                        print('No changes detected. Type a command (or ENTER for Enter key): ', end='', flush=True)
                        # Wait for user input or output
                        rlist = [fd, sys.stdin]
                        ready, _, _ = select.select(rlist, [], [], None)
                        for ready_fd in ready:
                            if ready_fd == sys.stdin:
                                user_input = sys.stdin.readline().rstrip('\n')
                                if user_input.strip().upper() == 'ENTER':
                                    os.write(fd, b'\n')
                                    print('[Sent ENTER to dfrotz]')
                                elif user_input:
                                    os.write(fd, (user_input + '\n').encode())
                                    print(f'[Sent "{user_input}" to dfrotz]')
                            elif ready_fd == fd:
                                break  # Resume normal loop
        except Exception as e:
            logger.error(f"Failed to start game: {str(e)}")
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