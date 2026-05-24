import os
import asyncio
import logging
import edge_tts

logger = logging.getLogger(__name__)

# A good English voice for stories
VOICE = "en-US-GuyNeural"
OUTPUT_FILE = "voiceover.mp3"

async def _generate_audio_async(text: str, output_path: str) -> bool:
    try:
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(output_path)
        return True
    except Exception as e:
        logger.error(f"Error generating audio with edge-tts: {e}")
        return False

def generate_audio(text: str, output_path: str = OUTPUT_FILE) -> str | None:
    """
    Takes the full text (hook + script) and generates a voiceover MP3.
    Returns the path to the generated MP3, or None if failed.
    """
    logger.info(f"Generating voiceover using voice: {VOICE}")
    success = asyncio.run(_generate_audio_async(text, output_path))
    
    if success and os.path.exists(output_path):
        logger.info(f"Successfully generated audio at: {output_path}")
        return output_path
    else:
        logger.error("Audio generation failed or output file not found.")
        return None
