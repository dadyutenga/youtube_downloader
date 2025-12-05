"""
YouTube Downloader Helper Module

This module provides robust YouTube video/audio downloading functionality
using yt-dlp with fallback mechanisms for handling various edge cases
including signature-cipher issues and age-restricted videos.
"""

import json
import os
import re
import shutil
import sys
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class YouTubeDownloader:
    """
    A robust YouTube downloader class that handles various download scenarios
    including video (MP4) and audio (MP3) formats with proper error handling.
    """

    # Quality format mappings for yt-dlp
    VIDEO_QUALITY_FORMATS = {
        'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        '1080p': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]',
        '720p': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]',
        '480p': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]',
        'worst': 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]/worst',
    }

    AUDIO_FORMAT = 'bestaudio[ext=m4a]/bestaudio/best'

    # Regex pattern for validating YouTube URLs
    YOUTUBE_URL_PATTERN = re.compile(
        r'^(https?://)?(www\.)?(youtube\.com/(watch\?v=|embed/|v/|shorts/)|youtu\.be/|youtube\.com/playlist\?list=)[\w\-&=]+',
        re.IGNORECASE
    )

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the downloader.

        Args:
            output_dir: Directory to save downloaded files. Uses tempdir if not specified.
        """
        if output_dir:
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.output_dir = Path(tempfile.mkdtemp(prefix='yt_download_'))

    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, str]:
        """
        Validate if the given URL is a valid YouTube URL.

        Args:
            url: The URL to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return False, "URL cannot be empty"

        url = url.strip()

        if not cls.YOUTUBE_URL_PATTERN.match(url):
            return False, "Invalid YouTube URL format"

        # Additional validation for common issues
        if len(url) > 500:
            return False, "URL is too long"

        return True, ""

    @classmethod
    def extract_video_id(cls, url: str) -> Optional[str]:
        """
        Extract the video ID from a YouTube URL.

        Args:
            url: YouTube URL

        Returns:
            Video ID or None if not found
        """
        patterns = [
            r'(?:v=|/v/|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch metadata for a YouTube video without downloading.

        Args:
            url: YouTube video URL

        Returns:
            Dictionary with video metadata or None on failure
        """
        cmd = [
            sys.executable, '-m', 'yt_dlp',
            '--dump-json',
            '--no-download',
            '--no-warnings',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--extractor-args', 'youtube:player_client=android,web',
            url
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout.strip().split('\n')[0])
                return {
                    'title': data.get('title', 'Unknown'),
                    'thumbnail': data.get('thumbnail'),
                    'duration': data.get('duration', 0),
                    'duration_string': data.get('duration_string', '0:00'),
                    'description': data.get('description', ''),
                    'uploader': data.get('uploader', 'Unknown'),
                    'view_count': data.get('view_count', 0),
                    'upload_date': data.get('upload_date', ''),
                    'webpage_url': data.get('webpage_url', url),
                    'id': data.get('id', ''),
                    'age_limit': data.get('age_limit', 0),
                    'is_live': data.get('is_live', False),
                }
            else:
                logger.error(f"Failed to fetch video info: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error("Timeout while fetching video info")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching video info: {e}")
            return None

    def download_video(
        self,
        url: str,
        quality: str = '720p',
        progress_callback: Optional[callable] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Download a YouTube video as MP4.

        Args:
            url: YouTube video URL
            quality: Video quality ('best', '1080p', '720p', '480p', 'worst')
            progress_callback: Optional callback function for progress updates

        Returns:
            Tuple of (success, message, file_path)
        """
        format_string = self.VIDEO_QUALITY_FORMATS.get(quality, self.VIDEO_QUALITY_FORMATS['720p'])
        output_template = str(self.output_dir / '%(title)s.%(ext)s')

        cmd = self._build_download_command(url, format_string, output_template, 'mp4')

        return self._execute_download(cmd, progress_callback)

    def download_audio(
        self,
        url: str,
        progress_callback: Optional[callable] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Download a YouTube video as MP3 audio.

        Args:
            url: YouTube video URL
            progress_callback: Optional callback function for progress updates

        Returns:
            Tuple of (success, message, file_path)
        """
        output_template = str(self.output_dir / '%(title)s.%(ext)s')

        cmd = [
            sys.executable, '-m', 'yt_dlp',
            '-f', self.AUDIO_FORMAT,
            '-x',  # Extract audio
            '--audio-format', 'mp3',
            '--audio-quality', '0',  # Best quality
            '-o', output_template,
            '--newline',
            '--progress',
            '--restrict-filenames',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--extractor-args', 'youtube:player_client=android,web',
            '--no-check-certificate',
            '--no-playlist',
            url
        ]

        return self._execute_download(cmd, progress_callback)

    def _build_download_command(
        self,
        url: str,
        format_string: str,
        output_template: str,
        merge_format: str = 'mp4'
    ) -> list:
        """
        Build the yt-dlp command with optimal settings.

        Args:
            url: YouTube URL
            format_string: yt-dlp format string
            output_template: Output file path template
            merge_format: Output container format

        Returns:
            List of command arguments
        """
        cmd = [
            sys.executable, '-m', 'yt_dlp',
            '-f', format_string,
            '--merge-output-format', merge_format,
            '-o', output_template,
            '--newline',
            '--progress',
            '--restrict-filenames',
            # User agent to avoid bot detection
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # Use multiple player clients for better compatibility
            '--extractor-args', 'youtube:player_client=android,web',
            '--no-check-certificate',
            '--no-playlist',  # Don't download entire playlist if URL contains playlist
            url
        ]

        return cmd

    def _execute_download(
        self,
        cmd: list,
        progress_callback: Optional[callable] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Execute the download command and handle progress.

        Args:
            cmd: Command to execute
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (success, message, file_path)
        """
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            current_file = None
            current_title = ""

            for line in process.stdout:
                line = line.strip()

                # Extract destination file path
                if '[download]' in line and 'Destination:' in line:
                    dest = line.split('Destination:')[-1].strip()
                    current_file = dest
                    current_title = Path(dest).stem

                # Extract progress percentage
                elif '[download]' in line and '%' in line:
                    try:
                        percent_str = line.split('%')[0].split()[-1]
                        percent = float(percent_str)
                        if progress_callback:
                            progress_callback(int(percent), current_title)
                    except (ValueError, IndexError):
                        pass

                # Look for merger output (final file)
                elif '[Merger]' in line and 'Merging formats into' in line:
                    merged_file = line.split('"')[-2] if '"' in line else None
                    if merged_file:
                        current_file = merged_file

                # Look for ExtractAudio output
                elif '[ExtractAudio]' in line and 'Destination:' in line:
                    dest = line.split('Destination:')[-1].strip()
                    current_file = dest

            process.wait()

            if process.returncode == 0:
                # Try to find the downloaded file
                if current_file and Path(current_file).exists():
                    return True, "Download completed successfully", current_file

                # Fallback: search for the most recent file
                if current_title:
                    possible_files = list(self.output_dir.glob(f"{current_title}.*"))
                    if possible_files:
                        # Get the most recently modified file
                        latest_file = max(possible_files, key=lambda f: f.stat().st_mtime)
                        return True, "Download completed successfully", str(latest_file)

                # Last resort: find any recent file
                all_files = sorted(self.output_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
                if all_files:
                    return True, "Download completed successfully", str(all_files[0])

                return False, "Download completed but file not found", None
            else:
                return False, "Download failed", None

        except subprocess.TimeoutExpired:
            return False, "Download timed out", None
        except Exception as e:
            logger.exception(f"Download error: {e}")
            return False, f"Download error: {str(e)}", None

    def cleanup(self, file_path: Optional[str] = None):
        """
        Clean up downloaded files.

        Args:
            file_path: Specific file to delete, or None to delete all temp files
        """
        try:
            if file_path:
                path = Path(file_path)
                if path.exists():
                    path.unlink()
            elif self.output_dir.exists() and str(self.output_dir).startswith(tempfile.gettempdir()):
                # Only delete if it's a temp directory we created
                shutil.rmtree(self.output_dir, ignore_errors=True)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "5:30" or "1:02:15")
    """
    if not seconds or seconds < 0:
        return "0:00"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_view_count(count: int) -> str:
    """
    Format view count to human-readable string.

    Args:
        count: View count

    Returns:
        Formatted string (e.g., "1.2M views")
    """
    if not count:
        return "0 views"

    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.1f}B views"
    elif count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M views"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K views"
    return f"{count} views"
