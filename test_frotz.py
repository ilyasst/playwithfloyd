from runner.frotz_runner import FrotzRunner
import os

def main():
    # Path to your game file - replace this with your actual game path
    game_path = "games/905.z5"  # Example path, adjust as needed
    
    # Check if game file exists
    if not os.path.exists(game_path):
        print(f"Error: Game file not found at {game_path}")
        print("Please make sure the game file exists and update the path in the script.")
        return

    try:
        # Create and start the FrotzRunner
        print(f"Starting game: {game_path}")
        runner = FrotzRunner(game_path)
        runner.start()
    except Exception as e:
        print(f"Error running game: {str(e)}")
    finally:
        # Ensure the process is cleaned up
        if 'runner' in locals():
            runner.quit()

if __name__ == "__main__":
    main() 