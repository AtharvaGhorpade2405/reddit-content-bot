import os
import json
import logging
import sys
import subprocess
from dotenv import load_dotenv

from scraper import scrape_reddit_posts
from llm_processor import process_story

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("feeder.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("feeder")

QUEUE_FILE = "queue.json"

def get_queue() -> list[dict]:
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("queue.json is corrupted or empty. Starting fresh.")
    return []

def save_queue(queue: list[dict]):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=4)

def push_queue_to_git():
    logger.info("Syncing queue.json to GitHub...")
    try:
        subprocess.run(["git", "add", QUEUE_FILE], check=True)
        # We allow this to fail if there are no changes, hence check=False
        res = subprocess.run(["git", "commit", "-m", "chore: Auto-update queue from feeder"], capture_output=True)
        if res.returncode == 0:
            subprocess.run(["git", "push"], check=True)
            logger.info("Successfully synced queue to GitHub.")
        else:
            logger.info("No changes to commit for queue.json.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git sync failed: {e}")

def main():
    logger.info("=== Starting Feeder (Producer) ===")
    
    # 1. Scrape Reddit
    posts = scrape_reddit_posts(limit=5)
    if not posts:
        logger.error("No suitable posts found. Exiting.")
        return
        
    logger.info(f"Successfully scraped {len(posts)} posts.")
    
    # 2. Process and append to queue
    queue = get_queue()
    existing_ids = {item["id"] for item in queue}
    
    items_added = 0
    for post in posts:
        if post["id"] in existing_ids:
            logger.info(f"Post {post['id']} is already in the queue. Skipping.")
            continue
            
        logger.info(f"Processing post: {post['title']}")
        script_data = process_story(post["title"], post["text"])
        
        if not script_data:
            logger.warning(f"Failed to process post {post['id']}. Skipping.")
            continue
            
        # Add to queue
        queue_item = {
            "id": post["id"],
            "title": post["title"],
            "text": post["text"],
            "hook": script_data.hook,
            "script": script_data.script,
            "youtube_title": script_data.youtube_title,
            "youtube_tags": script_data.youtube_tags,
            "subreddit": post["subreddit"]
        }
        
        queue.append(queue_item)
        items_added += 1
        logger.info(f"Successfully added {post['id']} to queue.")
        
    if items_added > 0:
        save_queue(queue)
        logger.info(f"Saved {items_added} new items to queue.json.")
        push_queue_to_git()
    else:
        logger.info("No new items were added to the queue.")
        
    logger.info("=== Feeder execution complete ===")

if __name__ == "__main__":
    main()
