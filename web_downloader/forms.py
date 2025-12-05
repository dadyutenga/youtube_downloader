from django import forms
from django.core.exceptions import ValidationError
from .models import VideoDownload
from .helpers.downloader import YouTubeDownloader


class DownloadForm(forms.ModelForm):
    """Form for initiating a video download"""
    
    class Meta:
        model = VideoDownload
        fields = ['url', 'format_type', 'quality']
        widgets = {
            'url': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter YouTube URL (e.g., https://www.youtube.com/watch?v=...)',
                'required': True,
                'autocomplete': 'off',
            }),
            'format_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'quality': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
        labels = {
            'url': 'YouTube URL',
            'format_type': 'Format',
            'quality': 'Video Quality',
        }
    
    def clean_url(self):
        """Validate the YouTube URL"""
        url = self.cleaned_data.get('url', '').strip()
        
        is_valid, error_message = YouTubeDownloader.validate_url(url)
        if not is_valid:
            raise ValidationError(error_message)
        
        return url
    
    def clean(self):
        """Additional form-level validation"""
        cleaned_data = super().clean()
        format_type = cleaned_data.get('format_type')
        quality = cleaned_data.get('quality')
        
        # Quality selection doesn't matter for MP3 audio extraction
        if format_type == 'mp3':
            # For audio, we always use best quality extraction
            cleaned_data['quality'] = 'best'
        
        return cleaned_data
