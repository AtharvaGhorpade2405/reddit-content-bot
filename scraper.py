import os
import json
import random
import praw
import logging

logger = logging.getLogger(__name__)

SUBREDDITS = [
    "AmItheAsshole",
    "TrueOffMyChest",
    "tifu",
    "MaliciousCompliance",
    "pettyrevenge",
    "entitledparents"
]

LEDGER_FILE = "processed_posts.json"

def get_processed_posts() -> set:
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, 'r') as f:
                return set(json.load(f))
        except Exception as e:
            logger.warning(f"Failed to read ledger file: {e}")
            return set()
    return set()

def update_processed_posts(post_id: str):
    processed = get_processed_posts()
    processed.add(post_id)
    with open(LEDGER_FILE, 'w') as f:
        json.write(f, list(processed))
        
def save_processed_posts(processed: set):
    with open(LEDGER_FILE, 'w') as f:
        json.dump(list(processed), f)

def scrape_reddit_post() -> dict | None:
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "reddit-content-bot:v1.0 (by /u/your_username)")

    if not client_id or not client_secret:
        logger.error("Reddit credentials are not set in the environment variables.")
        return None

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
    except Exception as e:
        logger.error(f"Failed to initialize PRAW: {e}")
        return None

    random.shuffle(SUBREDDITS)
    processed_ids = get_processed_posts()

    for subreddit_name in SUBREDDITS:
        logger.info(f"Checking subreddit: r/{subreddit_name}")
        try:
            subreddit = reddit.subreddit(subreddit_name)
            # Fetch Top - Past 24 Hours
            top_posts = subreddit.top(time_filter="day", limit=25)
            
            for post in top_posts:
                if post.score < 2000:
                    continue
                if post.id in processed_ids:
                    continue
                if post.over_18: # Avoid NSFW optionally? User didn't specify, but often a good idea for shorts. Actually, some of these subreddits have nsfw tags for text. I'll include them if not explicitly asked to exclude, just text.
                    pass 
                
                # We found a valid post!
                # Ensure it has text
                if not post.selftext.strip():
                    continue

                processed_ids.add(post.id)
                save_processed_posts(processed_ids)
                
                logger.info(f"Selected post: {post.title} (Score: {post.score}, ID: {post.id})")
                return {
                    "id": post.id,
                    "title": post.title,
                    "text": post.selftext,
                    "subreddit": subreddit_name,
                    "score": post.score
                }
        except Exception as e:
            logger.warning(f"Error accessing r/{subreddit_name}: {e}")

    logger.warning("No suitable posts found in any of the targeted subreddits.")
    return None
