import os
import sys
import logging
from dotenv import load_dotenv

# Load env variables first
load_dotenv()

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pipeline.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("main")

from scraper import scrape_reddit_post
from llm_processor import process_story
from audio_generator import generate_audio
from transcriber import transcribe_audio
from video_renderer import create_video
from uploader import upload_to_youtube

def main():
    logger.info("=== Starting YouTube Shorts Automation Pipeline ===")
    
    try:
        # Step 1: Scrape Reddit
        logger.info("STEP 1: Scraping Reddit")
        post_data = scrape_reddit_post()
        if not post_data:
            logger.error("Failed to fetch a suitable Reddit post. Exiting.")
            return
            
        logger.info(f"Successfully scraped post: '{post_data['title']}' from r/{post_data['subreddit']}")
        
        # Step 2: LLM Processing
        logger.info("STEP 2: Processing with LLM")
        script_data = process_story(post_data['title'], post_data['text'])
        if not script_data:
            logger.error("Failed to generate script from LLM. Exiting.")
            return
            
        full_script = f"{script_data.hook} {script_data.script}"
        logger.info(f"Successfully generated script ({len(full_script.split())} words)")
        logger.info(f"Proposed YouTube Title: {script_data.youtube_title}")
        logger.info(f"Proposed Tags: {', '.join(script_data.youtube_tags)}")
        
        # Step 3: Audio Generation
        logger.info("STEP 3: Generating Audio")
        audio_path = generate_audio(full_script)
        if not audio_path:
            logger.error("Failed to generate audio. Exiting.")
            return
            
        # Step 4: Transcription (Timestamps)
        logger.info("STEP 4: Transcribing Audio for Subtitles")
        transcript_chunks = transcribe_audio(audio_path, max_words_per_chunk=3)
        if not transcript_chunks:
            logger.error("Failed to generate transcript chunks. Exiting.")
            return
            
        # Step 5: Video Rendering
        logger.info("STEP 5: Rendering Final Video")
        bg_video = "background.mp4"
        if not os.path.exists(bg_video):
            logger.warning(f"{bg_video} not found! Please place a background gameplay video in the root directory.")
            return
            
        success = create_video(audio_path, transcript_chunks, bg_path=bg_video)
        
        if success:
            logger.info("=== Video Pipeline Completed Successfully! ===")
            logger.info(f"Final video saved as 'final_short.mp4'")
            
            # Step 6: Upload to YouTube
            logger.info("STEP 6: Uploading to YouTube")
            video_id = upload_to_youtube(
                file_path="final_short.mp4",
                title=script_data.youtube_title,
                description=f"{post_data['title']}\n\n{script_data.script}",
                tags=script_data.youtube_tags
            )
            
            if video_id:
                logger.info("=== Full Automation Pipeline Completed Successfully! ===")
            else:
                logger.error("Pipeline failed during YouTube upload.")
        else:
            logger.error("Pipeline failed during video rendering.")

    except Exception as e:
        logger.critical(f"Unhandled exception in pipeline: {e}", exc_info=True)

if __name__ == "__main__":
    main()
