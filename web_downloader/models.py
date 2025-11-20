from django.db import models
from django.utils import timezone


class VideoDownload(models.Model):
    """Model to track video download status and progress"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('downloading', 'Downloading'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    QUALITY_CHOICES = [
        ('best', 'Best Quality'),
        ('1080p', '1080p'),
        ('720p', '720p'),
        ('480p', '480p'),
        ('worst', 'Worst Quality'),
    ]
    
    url = models.URLField(max_length=500)
    title = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    quality = models.CharField(max_length=10, choices=QUALITY_CHOICES, default='best')
    progress = models.IntegerField(default=0)  # 0-100
    file_path = models.CharField(max_length=1000, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title or self.url} - {self.status}"
