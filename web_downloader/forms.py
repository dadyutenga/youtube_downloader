from django import forms
from .models import VideoDownload


class DownloadForm(forms.ModelForm):
    """Form for initiating a video download"""
    
    class Meta:
        model = VideoDownload
        fields = ['url', 'quality']
        widgets = {
            'url': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter YouTube URL (video or playlist)',
                'required': True,
            }),
            'quality': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
