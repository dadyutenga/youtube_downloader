"""
Utility functions for downloading videos using yt-dlp
Uses the helpers/downloader.py module for core functionality
"""
import os
import threading
import logging
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from .models import VideoDownload
from .helpers.downloader import YouTubeDownloader

logger = logging.getLogger(__name__)


def get_download_dir():
    """Get or create the downloads directory"""
    download_dir = Path(settings.BASE_DIR) / 'downloads'
    download_dir.mkdir(parents=True, exist_ok=True)
    return download_dir


def download_video_thread(download_id):
    """
    Background thread function to download a video
    Updates the VideoDownload model instance with progress
    """
    try:
        download = VideoDownload.objects.get(id=download_id)
        download.status = 'fetching'
        download.save()
        
        output_dir = get_download_dir()
        downloader = YouTubeDownloader(output_dir=str(output_dir))
        
        # Fetch video info first
        video_info = downloader.get_video_info(download.url)
        if video_info:
            download.title = video_info.get('title', '')[:500]
            download.thumbnail = video_info.get('thumbnail', '')[:500] if video_info.get('thumbnail') else ''
            download.duration = video_info.get('duration', 0) or 0
            download.uploader = video_info.get('uploader', '')[:200] if video_info.get('uploader') else ''
            download.save()
        
        download.status = 'downloading'
        download.save()
        
        def progress_callback(percent, title):
            """Update download progress in database"""
            try:
                dl = VideoDownload.objects.get(id=download_id)
                dl.progress = percent
                if title and not dl.title:
                    dl.title = title[:500]
                dl.save()
            except Exception as e:
                logger.error(f"Error updating progress: {e}")
        
        # Perform the download based on format type
        if download.format_type == 'mp3':
            success, message, file_path = downloader.download_audio(
                download.url,
                progress_callback=progress_callback
            )
        else:
            success, message, file_path = downloader.download_video(
                download.url,
                quality=download.quality,
                progress_callback=progress_callback
            )
        
        if success and file_path:
            download.file_path = str(file_path)
            download.status = 'completed'
            download.progress = 100
            download.completed_at = timezone.now()
            
            # Get file size
            try:
                download.file_size = Path(file_path).stat().st_size
            except Exception:
                pass
            
            download.save()
        else:
            download.status = 'failed'
            download.error_message = message or 'Download failed'
            download.save()
            
    except VideoDownload.DoesNotExist:
        logger.error(f"Download {download_id} not found")
    except Exception as e:
        logger.exception(f"Error in download thread: {e}")
        try:
            download = VideoDownload.objects.get(id=download_id)
            download.status = 'failed'
            download.error_message = str(e)
            download.save()
        except Exception:
            pass


def start_download(download_id):
    """Start a download in a background thread"""
    thread = threading.Thread(target=download_video_thread, args=(download_id,))
    thread.daemon = True
    thread.start()
