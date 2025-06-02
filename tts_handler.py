from TTS.api import TTS
import os
import tempfile
import pygame
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TTSHandler:
    def __init__(self):
        try:
            logger.info("Initializing TTS with English model...")
            # Initialize TTS with a simple English model
            self.tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")
            logger.info("TTS model loaded successfully!")
            
            # Initialize pygame mixer for audio playback
            logger.info("Initializing pygame mixer...")
            pygame.mixer.init()
            logger.info("Pygame mixer initialized successfully!")
            
        except Exception as e:
            logger.error(f"Error initializing TTS Handler: {str(e)}")
            raise
        
    def speak(self, text):
        """
        Convert text to speech and play it
        """
        try:
            logger.info(f"Generating speech for text: {text[:50]}...")
            # Create a temporary file for the audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                # Generate speech
                self.tts.tts_to_file(
                    text=text,
                    file_path=temp_file.name
                )
                logger.info("Speech generated successfully!")
                
                # Play the audio
                logger.info("Loading audio file...")
                pygame.mixer.music.load(temp_file.name)
                logger.info("Playing audio...")
                pygame.mixer.music.play()
                
                # Wait for the audio to finish playing
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                
                logger.info("Audio playback completed!")
                
                # Clean up the temporary file
                os.unlink(temp_file.name)
                logger.info("Temporary file cleaned up!")
                
        except Exception as e:
            logger.error(f"Error in speak method: {str(e)}")
            raise
    
    def stop(self):
        """
        Stop any currently playing audio
        """
        try:
            logger.info("Stopping audio playback...")
            pygame.mixer.music.stop()
            logger.info("Audio playback stopped!")
        except Exception as e:
            logger.error(f"Error stopping audio: {str(e)}")
            raise

# Test code that runs when the file is executed directly
if __name__ == "__main__":
    print("Starting TTS test...")
    try:
        tts = TTSHandler()
        print("TTS Handler initialized successfully!")
        
        test_text = "Hello! This is a test of the text to speech system."
        print(f"\nTesting with text: {test_text}")
        tts.speak(test_text)
        
        print("\nTest completed!")
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        import traceback
        traceback.print_exc() 