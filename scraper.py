import os
import json
import random
import logging
import requests

logger = logging.getLogger(__name__)

# List of target subreddits
SUBREDDITS = [
    "TrueOffMyChest",
    "AmItheAsshole",
    "tifu",
    "MaliciousCompliance",
    "pettyrevenge",
    "creepyencounters",
    "relationship_advice",
    "aita",
    "confessions",
    "nosleep",
    "antiwork",
    "ProRevenge",
    "NuclearRevenge"
]

LEDGER_FILE = "processed_posts.json"

def get_processed_posts() -> set:
    """Reads the ledger file and returns a set of processed post IDs."""
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception as e:
            logger.warning(f"Failed to read ledger file: {e}")
            return set()
    return set()

def save_processed_posts(processed: set):
    """Saves the set of processed post IDs to the ledger file."""
    try:
        with open(LEDGER_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(processed), f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save ledger file: {e}")

def get_viral_stories(limit: int = 5) -> list[dict]:
    """
    Randomly selects subreddits, fetches the top posts of the day using Reddit's JSON endpoint,
    filters for >2000 upvotes and unprocessed posts, and returns up to `limit` posts.
    """
    random.shuffle(SUBREDDITS)
    processed_ids = get_processed_posts()
    
    # Standard web browser User-Agent to prevent 429 Too Many Requests
    headers = {
        "User-Agent": "python:yt-shorts-bot:v1.0 (by /u/Severus2405)"
    }

    found_posts = []

    for subreddit in SUBREDDITS:
        if len(found_posts) >= limit:
            break
            
        logger.info(f"Checking subreddit: r/{subreddit}")
        url = f"https://old.reddit.com/r/{subreddit}/top.json?limit=25&t=day"
        
        try:
            # Fetch data from the public JSON endpoint
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            data = response.json()
            posts = data.get('data', {}).get('children', [])
            
            for post in posts:
                if len(found_posts) >= limit:
                    break
                    
                post_data = post.get('data', {})
                post_id = post_data.get('id')
                score = post_data.get('score', 0)
                title = post_data.get('title', '')
                selftext = post_data.get('selftext', '').strip()
                
                # Minimum of 2,000 upvotes
                if score < 2000:
                    continue
                # Ensure the post has text content
                if not selftext:
                    continue
                # Skip previously processed posts
                if post_id in processed_ids:
                    continue
                    
                # We found a valid post
                logger.info(f"Selected post: '{title}' (Score: {score}, ID: {post_id})")
                
                # Update ledger to avoid processing this story again
                processed_ids.add(post_id)
                save_processed_posts(processed_ids)
                
                found_posts.append({
                    "id": post_id,
                    "title": title,
                    "selftext": selftext,
                    "subreddit": subreddit,
                    "score": score
                })
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error fetching data from r/{subreddit}: {e}")
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response from r/{subreddit}")

    if not found_posts:
        logger.warning("No suitable viral posts found in any of the targeted subreddits.")
    
    return found_posts

# Wrapper to maintain compatibility with main.py's expected interface
def scrape_reddit_posts(limit: int = 5) -> list[dict]:
    stories = get_viral_stories(limit=limit)
    return [
        {
            "id": story["id"],
            "title": story["title"],
            "text": story["selftext"], # Map selftext to text for compatibility
            "subreddit": story["subreddit"],
            "score": story["score"]
        } for story in stories
    ]
