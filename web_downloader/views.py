from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_http_methods
from pathlib import Path
from .models import VideoDownload
from .forms import DownloadForm
from .utils import start_download


def index(request):
    """Main page with download form and recent downloads"""
    if request.method == 'POST':
        form = DownloadForm(request.POST)
        if form.is_valid():
            download = form.save()
            # Start download in background thread
            start_download(download.id)
            return redirect('index')
    else:
        form = DownloadForm()
    
    # Get recent downloads
    recent_downloads = VideoDownload.objects.all()[:20]
    
    context = {
        'form': form,
        'downloads': recent_downloads,
    }
    return render(request, 'web_downloader/index.html', context)


@require_http_methods(["GET"])
def get_progress(request, download_id):
    """API endpoint to get download progress"""
    try:
        download = VideoDownload.objects.get(id=download_id)
        data = {
            'id': download.id,
            'title': download.title or 'Processing...',
            'status': download.status,
            'progress': download.progress,
            'error_message': download.error_message,
            'file_available': bool(download.file_path),
        }
        return JsonResponse(data)
    except VideoDownload.DoesNotExist:
        return JsonResponse({'error': 'Download not found'}, status=404)


@require_http_methods(["GET"])
def download_file(request, download_id):
    """Serve the downloaded file to the user"""
    download = get_object_or_404(VideoDownload, id=download_id)
    
    if not download.file_path or download.status != 'completed':
        raise Http404("File not available")
    
    file_path = Path(download.file_path)
    if not file_path.exists():
        raise Http404("File not found on disk")
    
    response = FileResponse(open(file_path, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="{file_path.name}"'
    return response


@require_http_methods(["POST"])
def delete_download(request, download_id):
    """Delete a download record and optionally its file"""
    download = get_object_or_404(VideoDownload, id=download_id)
    
    # Delete the file if it exists
    if download.file_path:
        file_path = Path(download.file_path)
        if file_path.exists():
            file_path.unlink()
    
    download.delete()
    return redirect('index')
