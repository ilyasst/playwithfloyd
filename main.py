from runner.frotz_runner import FrotzRunner
import sys
import traceback
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('main')

def main():
    logger.info("Starting game...")
    runner = None
    
    try:
        logger.info("Initializing FrotzRunner")
        runner = FrotzRunner('games/905.z5')
        
        # Initial look command to show starting room
        logger.info("Loading game...")
        output = runner.run_command('look')
        logger.debug(f"Initial output: {output}")
        print(output)
        
        while True:
            try:
                # Get player input
                command = input('> ').strip()
                logger.debug(f"Received command: {command}")
                
                # Check for quit command
                if command.lower() in ['quit', 'exit', 'q']:
                    logger.info("Quitting game...")
                    print("Quitting game...")
                    break
                    
                # Run the command and print output
                output = runner.run_command(command)
                logger.debug(f"Command output: {output}")
                print(output)
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                print("\nQuitting game...")
                break
            except Exception as e:
                logger.error(f"Error during gameplay: {e}", exc_info=True)
                print(f"Error during gameplay: {e}")
                traceback.print_exc()
                break
    except Exception as e:
        logger.error(f"Failed to start game: {e}", exc_info=True)
        print(f"Failed to start game: {e}")
        traceback.print_exc()
    finally:
        # Ensure we clean up the process
        if runner:
            logger.info("Cleaning up runner")
            runner.quit()
        logger.info("Game closed.")
        print("Game closed.")

if __name__ == '__main__':
    main()
