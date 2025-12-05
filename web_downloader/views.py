from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from pathlib import Path
import logging
import uuid
from .models import VideoDownload
from .forms import DownloadForm
from .utils import start_download
from .helpers.downloader import YouTubeDownloader

logger = logging.getLogger(__name__)


def get_or_create_session_id(request):
    """Get or create a unique session ID for the user"""
    if 'downloader_session_id' not in request.session:
        request.session['downloader_session_id'] = str(uuid.uuid4())
    return request.session['downloader_session_id']


def index(request):
    """Main page with download form and recent downloads"""
    session_id = get_or_create_session_id(request)
    
    if request.method == 'POST':
        form = DownloadForm(request.POST)
        if form.is_valid():
            download = form.save(commit=False)
            download.session_id = session_id
            download.save()
            # Start download in background thread
            start_download(download.id)
            messages.success(request, 'Download started successfully!')
            return redirect('web_downloader:index')
        else:
            # Form has validation errors
            messages.error(request, 'Please fix the errors below.')
    else:
        form = DownloadForm()
    
    # Get only this user's downloads
    recent_downloads = VideoDownload.objects.filter(session_id=session_id)[:20]
    
    context = {
        'form': form,
        'downloads': recent_downloads,
        'session_id': session_id[:8],  # Show first 8 chars for display
    }
    return render(request, 'web_downloader/index.html', context)


def preview(request):
    """Preview page to show video details before downloading"""
    url = request.GET.get('url', '').strip()
    
    if not url:
        messages.error(request, 'Please provide a YouTube URL')
        return redirect('web_downloader:index')
    
    # Validate URL
    is_valid, error_message = YouTubeDownloader.validate_url(url)
    if not is_valid:
        return render(request, 'web_downloader/error.html', {
            'error_title': 'Invalid URL',
            'error_message': error_message,
        })
    
    # Fetch video info
    downloader = YouTubeDownloader()
    video_info = downloader.get_video_info(url)
    
    if not video_info:
        return render(request, 'web_downloader/error.html', {
            'error_title': 'Video Not Found',
            'error_message': 'Could not fetch video information. The video may be private, deleted, or the URL may be incorrect.',
        })
    
    # Create form with pre-filled URL
    form = DownloadForm(initial={'url': url})
    
    context = {
        'form': form,
        'video_info': video_info,
        'url': url,
    }
    return render(request, 'web_downloader/preview.html', context)


@require_http_methods(["GET"])
def get_progress(request, download_id):
    """API endpoint to get download progress"""
    session_id = get_or_create_session_id(request)
    try:
        # Only allow access to user's own downloads
        download = VideoDownload.objects.get(id=download_id, session_id=session_id)
        data = {
            'id': download.id,
            'title': download.title or 'Processing...',
            'status': download.status,
            'progress': download.progress,
            'error_message': download.error_message,
            'file_available': bool(download.file_path and download.status == 'completed'),
            'thumbnail': download.thumbnail,
            'duration': download.duration_formatted,
            'format_type': download.format_type,
        }
        return JsonResponse(data)
    except VideoDownload.DoesNotExist:
        return JsonResponse({'error': 'Download not found'}, status=404)


@require_http_methods(["GET"])
def get_video_info(request):
    """API endpoint to fetch video information without downloading"""
    url = request.GET.get('url', '').strip()
    
    if not url:
        return JsonResponse({'error': 'URL is required'}, status=400)
    
    is_valid, error_message = YouTubeDownloader.validate_url(url)
    if not is_valid:
        return JsonResponse({'error': error_message}, status=400)
    
    downloader = YouTubeDownloader()
    video_info = downloader.get_video_info(url)
    
    if video_info:
        return JsonResponse(video_info)
    else:
        return JsonResponse({'error': 'Could not fetch video information'}, status=404)


@require_http_methods(["GET"])
def download_file(request, download_id):
    """Serve the downloaded file to the user"""
    session_id = get_or_create_session_id(request)
    # Only allow access to user's own downloads
    download = get_object_or_404(VideoDownload, id=download_id, session_id=session_id)
    
    if not download.file_path or download.status != 'completed':
        raise Http404("File not available")
    
    file_path = Path(download.file_path)
    if not file_path.exists():
        raise Http404("File not found on disk")
    
    # Determine content type based on format
    content_type = 'audio/mpeg' if download.format_type == 'mp3' else 'video/mp4'
    
    response = FileResponse(open(file_path, 'rb'), content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{file_path.name}"'
    return response


@require_http_methods(["POST"])
def delete_download(request, download_id):
    """Delete a download record and optionally its file"""
    session_id = get_or_create_session_id(request)
    # Only allow deletion of user's own downloads
    download = get_object_or_404(VideoDownload, id=download_id, session_id=session_id)
    
    # Delete the file if it exists
    if download.file_path:
        file_path = Path(download.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                logger.error(f"Error deleting file: {e}")
    
    download.delete()
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Download deleted successfully!'})
    
    messages.success(request, 'Download deleted successfully!')
    return redirect('web_downloader:index')


def error_page(request):
    """Generic error page"""
    error_title = request.GET.get('title', 'Error')
    error_message = request.GET.get('message', 'An unexpected error occurred.')
    
    return render(request, 'web_downloader/error.html', {
        'error_title': error_title,
        'error_message': error_message,
    })
