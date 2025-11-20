"""
Utility functions for downloading videos using yt-dlp
Adapted from playlist_downloader.py
"""
import os
import sys
import subprocess
import threading
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from .models import VideoDownload


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
        download.status = 'downloading'
        download.save()
        
        quality_formats = {
            'best': 'bestvideo+bestaudio/best',
            '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
            'worst': 'worstvideo+worstaudio/worst'
        }
        
        format_string = quality_formats.get(download.quality, quality_formats['best'])
        output_dir = get_download_dir()
        output_template = str(output_dir / '%(title)s.%(ext)s')
        
        cmd = [
            sys.executable,
            '-m',
            'yt_dlp',
            '-f', format_string,
            '--merge-output-format', 'mp4',
            '-o', output_template,
            '--newline',
            '--progress',
            '--restrict-filenames',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--extractor-args', 'youtube:player_client=android,web',
            '--no-check-certificate',
            download.url
        ]
        
        # Run the download process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        current_title = ""
        for line in process.stdout:
            line = line.strip()
            
            # Extract title from output
            if '[download]' in line and 'Destination:' in line:
                dest = line.split('Destination:')[-1].strip()
                current_title = Path(dest).stem
                download.title = current_title
                download.save()
            
            # Extract progress percentage
            elif '[download]' in line and '%' in line:
                try:
                    percent_str = line.split('%')[0].split()[-1]
                    percent = float(percent_str)
                    download.progress = int(percent)
                    download.save()
                except (ValueError, IndexError):
                    pass
        
        process.wait()
        
        if process.returncode == 0:
            # Find the downloaded file
            if current_title:
                possible_files = list(output_dir.glob(f"{current_title}.*"))
                if possible_files:
                    download.file_path = str(possible_files[0])
            
            download.status = 'completed'
            download.progress = 100
            download.completed_at = timezone.now()
            download.save()
        else:
            download.status = 'failed'
            download.error_message = 'Download process failed'
            download.save()
            
    except VideoDownload.DoesNotExist:
        pass
    except Exception as e:
        try:
            download = VideoDownload.objects.get(id=download_id)
            download.status = 'failed'
            download.error_message = str(e)
            download.save()
        except:
            pass


def start_download(download_id):
    """Start a download in a background thread"""
    thread = threading.Thread(target=download_video_thread, args=(download_id,))
    thread.daemon = True
    thread.start()
