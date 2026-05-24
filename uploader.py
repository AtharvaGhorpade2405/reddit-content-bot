import os
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Scope required for uploading YouTube videos
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"

def get_authenticated_service():
    """
    Handles OAuth 2.0 authentication.
    Checks for a saved token.json for headless execution.
    If none exists or it's invalid, triggers a local browser flow to login
    and saves the resulting credentials.
    """
    creds = None
    
    # Check if we already have saved credentials (vital for headless VPS)
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            logger.info("Loaded existing credentials from token.json")
        except Exception as e:
            logger.warning(f"Error loading token.json: {e}")

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials...")
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}. Falling back to manual auth.")
                creds = None
        
        if not creds:
            logger.info("Starting manual OAuth flow...")
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise FileNotFoundError(f"Missing {CLIENT_SECRET_FILE}. Download it from Google Cloud Console.")
                
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            # Run local server allows the script to handle the redirect URI automatically
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(TOKEN_FILE, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())
            logger.info("Saved new credentials to token.json")

    return build("youtube", "v3", credentials=creds)

def upload_to_youtube(file_path: str, title: str, description: str, tags: list[str]) -> str | None:
    """
    Uploads a video to YouTube.
    Returns the YouTube Video ID upon success, or None on failure.
    """
    if not os.path.exists(file_path):
        logger.error(f"Video file not found at {file_path}")
        return None

    # Ensure Shorts hashtags are present
    shorts_tags_str = "\n\n#shorts #reddit"
    if shorts_tags_str not in description:
        description += shorts_tags_str

    try:
        logger.info("Authenticating with YouTube API...")
        youtube = get_authenticated_service()

        logger.info(f"Preparing upload for: {title}")
        
        # Define video metadata
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "24" # 24 = Entertainment
            },
            "status": {
                # CHANGE THIS TO "public" WHEN READY FOR PRODUCTION DEPLOYMENT
                "privacyStatus": "public", 
                "selfDeclaredMadeForKids": False
            }
        }

        # MediaFileUpload handles the chunked, resumable upload automatically
        media = MediaFileUpload(
            file_path, 
            chunksize=-1, # -1 indicates standard chunk sizes
            resumable=True
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        logger.info("Starting upload. This may take a few minutes...")
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"Uploaded {int(status.progress() * 100)}%")

        video_id = response.get("id")
        logger.info(f"Upload Complete! Video ID: {video_id}")
        logger.info(f"View video at: https://youtu.be/{video_id}")
        return video_id

    except HttpError as e:
        logger.error(f"An HTTP error occurred: {e.resp.status} - {e.content}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during upload: {e}", exc_info=True)
        return None
