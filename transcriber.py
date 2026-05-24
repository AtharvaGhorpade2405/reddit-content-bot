import logging
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

def transcribe_audio(audio_path: str, max_words_per_chunk: int = 2) -> list[dict] | None:
    """
    Transcribes the audio file and groups words into chunks of 1-3 words (customizable)
    suitable for fast-paced short-form content.
    Returns a list of dictionaries with 'text', 'start', 'end'.
    """
    logger.info(f"Loading faster-whisper model for {audio_path}...")
    try:
        # "tiny" or "base" is usually sufficient and fast, 
        # but "small" gives better punctuation which helps word chunking.
        model = WhisperModel("base", device="cpu", compute_type="int8")
        
        logger.info("Transcribing audio...")
        segments, info = model.transcribe(audio_path, word_timestamps=True)
        
        words = []
        for segment in segments:
            for word in segment.words:
                words.append({
                    "word": word.word.strip(),
                    "start": word.start,
                    "end": word.end
                })
        
        if not words:
            logger.warning("Transcription resulted in no words.")
            return None
        
        # Group words into chunks
        logger.info("Grouping words into chunks...")
        chunks = []
        current_chunk_words = []
        current_chunk_start = 0.0
        
        for i, word_data in enumerate(words):
            if not current_chunk_words:
                current_chunk_start = word_data["start"]
                
            current_chunk_words.append(word_data["word"])
            
            # If we reach the chunk limit or end of sentence (punctuation)
            is_last_word = i == len(words) - 1
            has_punctuation = any(punct in word_data["word"] for punct in ['.', '!', '?', ','])
            
            if len(current_chunk_words) >= max_words_per_chunk or is_last_word or has_punctuation:
                chunks.append({
                    "text": " ".join(current_chunk_words),
                    "start": current_chunk_start,
                    "end": word_data["end"]
                })
                current_chunk_words = []

        logger.info(f"Generated {len(chunks)} text chunks.")
        return chunks

    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        return None
