import os
import json
import logging
import sys
import subprocess
from dotenv import load_dotenv

from audio_generator import generate_audio
from transcriber import transcribe_audio
from video_renderer import create_video
from uploader import upload_to_youtube

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("factory.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("factory")

QUEUE_FILE = "queue.json"
BG_VIDEO = "background.mp4"

def get_queue() -> list[dict]:
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("queue.json is corrupted or empty.")
    return []

def save_queue(queue: list[dict]):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=4)

def push_queue_to_git():
    logger.info("Syncing queue.json to GitHub...")
    try:
        subprocess.run(["git", "config", "pull.rebase", "true"], check=True)
        subprocess.run(["git", "add", QUEUE_FILE], check=True)
        res = subprocess.run(["git", "commit", "-m", "chore: Auto-update queue from factory"], capture_output=True)
        if res.returncode == 0:
            subprocess.run(["git", "pull", "origin", "main"], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            logger.info("Successfully synced queue to GitHub.")
        else:
            logger.info("No changes to commit for queue.json.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git sync failed: {e}")

def main():
    logger.info("=== Starting Factory (Consumer) ===")
    
    # 1. Read Queue
    queue = get_queue()
    if not queue:
        logger.info("Queue empty. Nothing to process.")
        return
        
    # Pop the first item
    item = queue[0]
    logger.info(f"Processing item: {item['title']} (ID: {item['id']})")
    
    full_script = f"{item['hook']} {item['script']}"
    
    try:
        # 2. Audio Generation
        logger.info("Generating Audio...")
        audio_path = generate_audio(full_script)
        if not audio_path:
            logger.error("Failed to generate audio. Aborting.")
            return
            
        # 3. Transcription
        logger.info("Transcribing Audio for Subtitles...")
        transcript_chunks = transcribe_audio(audio_path, max_words_per_chunk=3)
        if not transcript_chunks:
            logger.error("Failed to generate transcript chunks. Aborting.")
            return
            
        # 4. Video Rendering
        logger.info("Rendering Final Video...")
        if not os.path.exists(BG_VIDEO):
            logger.warning(f"{BG_VIDEO} not found! Please place a background gameplay video in the root directory.")
            return
            
        success = create_video(audio_path, transcript_chunks, bg_path=BG_VIDEO)
        if not success:
            logger.error("Pipeline failed during video rendering. Aborting.")
            return
            
        # 5. YouTube Upload
        logger.info("Uploading to YouTube...")
        description = f"{item['title']}\n\n{item['script']}"
        video_id = upload_to_youtube(
            file_path="final_short.mp4",
            title=item['youtube_title'],
            description=description,
            tags=item['youtube_tags']
        )
        
        if not video_id:
            logger.error("Pipeline failed during YouTube upload. Aborting.")
            return
            
        logger.info("=== Video Uploaded Successfully! ===")
        
        # 6. Cleanup & Sync
        # Only remove item if everything succeeded
        queue.pop(0)
        save_queue(queue)
        push_queue_to_git()
        
    except Exception as e:
        logger.critical(f"Unhandled exception in factory: {e}", exc_info=True)

if __name__ == "__main__":
    main()
