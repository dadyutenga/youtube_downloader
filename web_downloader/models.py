from django.db import models
from django.utils import timezone


class VideoDownload(models.Model):
    """Model to track video download status and progress"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('fetching', 'Fetching Info'),
        ('downloading', 'Downloading'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    FORMAT_CHOICES = [
        ('mp4', 'MP4 Video'),
        ('mp3', 'MP3 Audio'),
    ]
    
    QUALITY_CHOICES = [
        ('best', 'Best Quality'),
        ('1080p', '1080p'),
        ('720p', '720p'),
        ('480p', '480p'),
        ('worst', 'Lowest Quality'),
    ]
    
    # Session ID to isolate users
    session_id = models.CharField(max_length=64, db_index=True, default='legacy')
    
    url = models.URLField(max_length=500)
    title = models.CharField(max_length=500, blank=True)
    thumbnail = models.URLField(max_length=500, blank=True)
    duration = models.IntegerField(default=0)  # Duration in seconds
    uploader = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    format_type = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='mp4')
    quality = models.CharField(max_length=10, choices=QUALITY_CHOICES, default='720p')
    progress = models.IntegerField(default=0)  # 0-100
    file_path = models.CharField(max_length=1000, blank=True)
    file_size = models.BigIntegerField(default=0)  # File size in bytes
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title or self.url} - {self.status}"
    
    @property
    def duration_formatted(self):
        """Return duration in human-readable format"""
        if not self.duration:
            return "0:00"
        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
    
    @property
    def file_size_formatted(self):
        """Return file size in human-readable format"""
        if not self.file_size:
            return ""
        if self.file_size >= 1024 * 1024 * 1024:
            return f"{self.file_size / (1024 * 1024 * 1024):.1f} GB"
        elif self.file_size >= 1024 * 1024:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
        elif self.file_size >= 1024:
            return f"{self.file_size / 1024:.1f} KB"
        return f"{self.file_size} bytes"
