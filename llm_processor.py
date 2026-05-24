import os
import json
import logging
from typing import List
from pydantic import BaseModel, Field
from groq import Groq

logger = logging.getLogger(__name__)

class ProcessedScript(BaseModel):
    hook: str = Field(description="A catchy opening sentence to hook the viewer.")
    script: str = Field(description="The cleaned, grammar-corrected story optimized for spoken audio, MAXIMUM 150 words.")
    youtube_title: str = Field(description="An engaging title for the final YouTube Short.")
    youtube_tags: List[str] = Field(description="A list of relevant hashtag strings without the # symbol.")

def process_story(title: str, text: str) -> ProcessedScript | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY is not set in environment variables.")
        return None

    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}")
        return None

    prompt = f"""
    You are an expert content creator for YouTube Shorts. I will give you a Reddit post's title and text.
    Your task is to re-write and sanitize the story into a highly engaging, fast-paced script for a YouTube Short.
    
    Rules:
    1. No Cliffhangers: The script must contain the complete story, including the final consequence, realization, or resolution. Do not end with "stay tuned" or cut off the climax.
    2. The Dynamic 3-Act Structure:
       - Act 1: The Hook. A punchy, 1-2 sentence opening that grabs attention.
       - Act 2: The Escalation. The core context and buildup of the conflict, mistake, or situation.
       - Act 3: The Climax & Resolution. Detect the genre of the story and deliver the satisfying conclusion. If it's a revenge story, detail the retaliation. If it's a "TIFU", reveal the embarrassing disaster. If it's a confession, drama, or scary story, reveal the final twist, confrontation, or escape.
    3. Tone & Pacing: The script must be between 130 and 180 words, optimized for spoken word. Use conversational flow, and avoid complex formatting or unpronounceable symbols.
    4. Provide an engaging YouTube title and relevant tags.
    
    You MUST output your response as a valid JSON object matching exactly this format:
    {{
      "hook": "Your catchy opening sentence here.",
      "script": "The rest of your story script here.",
      "youtube_title": "Your Engaging Title Here",
      "youtube_tags": ["tag1", "tag2", "tag3"]
    }}
    
    Original Title: {title}
    Original Text: {text}
    """

    try:
        logger.info("Sending text to Groq for processing...")
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that outputs JSON matching the requested schema."
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
            # Using tools/function calling or JSON mode to enforce Pydantic schema
            response_format={"type": "json_object"},
        )
        
        response_content = chat_completion.choices[0].message.content
        logger.info("Received response from Groq. Validating schema...")
        
        # Pydantic validation
        result = ProcessedScript.model_validate_json(response_content)
        return result

    except Exception as e:
        logger.error(f"Error processing story with Groq: {e}")
        return None
