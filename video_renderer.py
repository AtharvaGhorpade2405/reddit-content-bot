import os
import random
import logging
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

logger = logging.getLogger(__name__)

def create_video(audio_path: str, transcript_chunks: list[dict], bg_path: str = "background.mp4", output_path: str = "final_short.mp4"):
    logger.info(f"Rendering video using {bg_path} and {audio_path}")
    
    if not os.path.exists(bg_path):
        logger.error(f"Background video {bg_path} not found!")
        return False
        
    try:
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration
        
        bg_clip = VideoFileClip(bg_path)
        bg_duration = bg_clip.duration
        
        if bg_duration < audio_duration:
            logger.warning("Background video is shorter than audio. It will loop or stop.")
            start_time = 0
        else:
            # Randomly slice a chunk of the background video
            max_start = bg_duration - audio_duration
            start_time = random.uniform(0, max_start)
            
        logger.info(f"Slicing background video from {start_time:.2f}s to {start_time + audio_duration:.2f}s")
        video_clip = bg_clip.subclip(start_time, start_time + audio_duration)
        video_clip = video_clip.set_audio(audio_clip)
        
        # Create text clips for each chunk
        text_clips = []
        for chunk in transcript_chunks:
            # Hormozi style specs
            text = chunk["text"].upper()
            start = chunk["start"]
            end = chunk["end"]
            
            try:
                # Need ImageMagick installed for this to work natively
                txt_clip = TextClip(
                    text,
                    fontsize=80,
                    color='#FFE800', # Bright Yellow
                    font='Impact', # Ensure this font is available, fallback is Arial-Black
                    stroke_color='black',
                    stroke_width=4,
                    method='caption',
                    align='center',
                    size=(video_clip.w * 0.8, None) # 80% of width to avoid edge spill
                )
                
                txt_clip = txt_clip.set_position(('center', 'center')).set_start(start).set_end(end)
                text_clips.append(txt_clip)
            except Exception as e:
                logger.warning(f"Error creating text clip for '{text}': {e}. Ensure ImageMagick is installed.")
                # Fallback simple text clip if stroke/font fails
                try:
                    txt_clip = TextClip(text, fontsize=60, color='white')
                    txt_clip = txt_clip.set_position(('center', 'center')).set_start(start).set_end(end)
                    text_clips.append(txt_clip)
                except Exception as inner_e:
                     logger.error(f"Fallback TextClip failed: {inner_e}")

        logger.info("Compositing video with subtitles...")
        final_video = CompositeVideoClip([video_clip] + text_clips)
        
        # We need to explicitly write with libx264 for compatibility and aac audio
        logger.info(f"Exporting to {output_path}...")
        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=30,
            preset="fast",
            logger=None # Suppress moviepy's internal bar to avoid cluttering our logs, or keep it
        )
        
        logger.info("Video rendering complete!")
        return True
        
    except Exception as e:
        logger.error(f"Error during video rendering: {e}")
        return False
    finally:
        # Cleanup moviepy resources
        try:
            audio_clip.close()
            bg_clip.close()
            final_video.close()
        except:
            pass
