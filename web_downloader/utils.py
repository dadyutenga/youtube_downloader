"""
Utility functions for downloading videos using yt-dlp
Uses the helpers/downloader.py module for core functionality
"""
import os
import threading
import logging
import time
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from django.db import transaction, OperationalError
from .models import VideoDownload
from .helpers.downloader import YouTubeDownloader

logger = logging.getLogger(__name__)


def retry_on_db_lock(func, max_retries=5, initial_delay=0.1):
    """
    Retry a database operation if it's locked
    Uses exponential backoff
    """
    for attempt in range(max_retries):
        try:
            return func()
        except OperationalError as e:
            if 'database is locked' in str(e).lower() and attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Database locked, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                raise
    raise OperationalError("Max retries exceeded for database operation")


def safe_save(instance):
    """Safely save a model instance with retry logic"""
    def save_func():
        with transaction.atomic():
            instance.save()
    retry_on_db_lock(save_func)


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
        def get_download():
            return VideoDownload.objects.get(id=download_id)
        
        download = retry_on_db_lock(get_download)
        download.status = 'fetching'
        safe_save(download)
        
        output_dir = get_download_dir()
        downloader = YouTubeDownloader(output_dir=str(output_dir))
        
        # Fetch video info first
        video_info = downloader.get_video_info(download.url)
        if video_info:
            download.title = video_info.get('title', '')[:500]
            download.thumbnail = video_info.get('thumbnail', '')[:500] if video_info.get('thumbnail') else ''
            download.duration = video_info.get('duration', 0) or 0
            download.uploader = video_info.get('uploader', '')[:200] if video_info.get('uploader') else ''
            safe_save(download)
        
        download.status = 'downloading'
        safe_save(download)
        
        def progress_callback(percent, title):
            """Update download progress in database"""
            try:
                def get_and_update():
                    dl = VideoDownload.objects.get(id=download_id)
                    dl.progress = percent
                    if title and not dl.title:
                        dl.title = title[:500]
                    return dl
                
                dl = retry_on_db_lock(get_and_update)
                safe_save(dl)
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
            
            safe_save(download)
        else:
            download.status = 'failed'
            download.error_message = message or 'Download failed'
            safe_save(download)
            
    except VideoDownload.DoesNotExist:
        logger.error(f"Download {download_id} not found")
    except Exception as e:
        logger.exception(f"Error in download thread: {e}")
        try:
            def get_download():
                return VideoDownload.objects.get(id=download_id)
            
            download = retry_on_db_lock(get_download)
            download.status = 'failed'
            download.error_message = str(e)
            safe_save(download)
        except Exception:
            pass


def start_download(download_id):
    """Start a download in a background thread"""
    thread = threading.Thread(target=download_video_thread, args=(download_id,))
    thread.daemon = True
    thread.start()
