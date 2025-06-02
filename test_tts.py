from TTS.api import TTS
from tts_handler import TTSHandler
import logging
import time
import traceback

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_tts_init():
    try:
        print("Starting TTS initialization test...")
        print("Available TTS models:")
        tts = TTS()
        print(tts.list_models())
        print("\nTest completed!")
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        traceback.print_exc()

def test_tts():
    try:
        print("Initializing TTS Handler...")
        tts = TTSHandler()
        print("TTS Handler initialized successfully!")
        
        # Test different types of text
        test_texts = [
            "Hello! This is a test of the text to speech system.",
            "The quick brown fox jumps over the lazy dog.",
            "Testing numbers: 1, 2, 3, 4, 5.",
            "Testing special characters: @#$%^&*()",
        ]
        
        print("\nStarting TTS tests...")
        for i, text in enumerate(test_texts, 1):
            print(f"\nTest {i}: {text}")
            print("Attempting to speak...")
            tts.speak(text)
            print("Speech completed!")
            # Small pause between tests
            time.sleep(1)
        
        print("\nAll tests completed!")
        
    except Exception as e:
        print("\nError occurred:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_tts_init()
    test_tts() 