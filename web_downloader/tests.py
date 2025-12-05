from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from .models import VideoDownload
from .forms import DownloadForm
from .helpers.downloader import YouTubeDownloader


class YouTubeURLValidationTestCase(TestCase):
    """Test cases for YouTube URL validation"""

    def test_valid_youtube_url(self):
        """Test that valid YouTube URLs pass validation"""
        valid_urls = [
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtube.com/watch?v=dQw4w9WgXcQ',
            'http://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtu.be/dQw4w9WgXcQ',
            'https://www.youtube.com/embed/dQw4w9WgXcQ',
            'https://www.youtube.com/v/dQw4w9WgXcQ',
            'https://www.youtube.com/shorts/dQw4w9WgXcQ',
        ]
        for url in valid_urls:
            is_valid, error = YouTubeDownloader.validate_url(url)
            self.assertTrue(is_valid, f"URL should be valid: {url}, got error: {error}")

    def test_invalid_youtube_url(self):
        """Test that invalid URLs fail validation"""
        invalid_urls = [
            '',
            'not a url',
            'https://google.com',
            'https://vimeo.com/123456',
            'https://facebook.com/video',
        ]
        for url in invalid_urls:
            is_valid, error = YouTubeDownloader.validate_url(url)
            self.assertFalse(is_valid, f"URL should be invalid: {url}")

    def test_empty_url_returns_error(self):
        """Test that empty URL returns appropriate error message"""
        is_valid, error = YouTubeDownloader.validate_url('')
        self.assertFalse(is_valid)
        self.assertEqual(error, "URL cannot be empty")

    def test_video_id_extraction(self):
        """Test video ID extraction from different URL formats"""
        test_cases = [
            ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://youtu.be/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://www.youtube.com/embed/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://www.youtube.com/v/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://www.youtube.com/shorts/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
        ]
        for url, expected_id in test_cases:
            extracted = YouTubeDownloader.extract_video_id(url)
            self.assertEqual(extracted, expected_id, f"Failed for URL: {url}")


class DownloadFormTestCase(TestCase):
    """Test cases for the download form"""

    def test_valid_form(self):
        """Test form with valid data"""
        form_data = {
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'format_type': 'mp4',
            'quality': '720p',
        }
        form = DownloadForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_url_form(self):
        """Test form with invalid URL"""
        form_data = {
            'url': 'https://google.com',
            'format_type': 'mp4',
            'quality': '720p',
        }
        form = DownloadForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('url', form.errors)

    def test_mp3_format_sets_best_quality(self):
        """Test that MP3 format automatically sets quality to best"""
        form_data = {
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'format_type': 'mp3',
            'quality': '480p',  # This should be overridden
        }
        form = DownloadForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['quality'], 'best')


class VideoDownloadModelTestCase(TestCase):
    """Test cases for the VideoDownload model"""

    def test_create_download(self):
        """Test creating a download record"""
        download = VideoDownload.objects.create(
            url='https://www.youtube.com/watch?v=test123',
            format_type='mp4',
            quality='720p'
        )
        self.assertEqual(download.status, 'pending')
        self.assertEqual(download.progress, 0)
        self.assertEqual(download.format_type, 'mp4')

    def test_duration_formatted(self):
        """Test duration formatting"""
        download = VideoDownload(duration=3661)  # 1h 1m 1s
        self.assertEqual(download.duration_formatted, '1:01:01')

        download.duration = 65  # 1m 5s
        self.assertEqual(download.duration_formatted, '1:05')

        download.duration = 0
        self.assertEqual(download.duration_formatted, '0:00')

    def test_file_size_formatted(self):
        """Test file size formatting"""
        download = VideoDownload()

        download.file_size = 0
        self.assertEqual(download.file_size_formatted, '')

        download.file_size = 500
        self.assertEqual(download.file_size_formatted, '500 bytes')

        download.file_size = 1024
        self.assertEqual(download.file_size_formatted, '1.0 KB')

        download.file_size = 1024 * 1024
        self.assertEqual(download.file_size_formatted, '1.0 MB')

        download.file_size = 1024 * 1024 * 1024
        self.assertEqual(download.file_size_formatted, '1.0 GB')


class ViewsTestCase(TestCase):
    """Test cases for views"""

    def setUp(self):
        self.client = Client()

    def test_index_page_loads(self):
        """Test that the index page loads successfully"""
        response = self.client.get(reverse('web_downloader:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'YouTube Downloader')

    def test_error_page_loads(self):
        """Test that the error page loads successfully"""
        response = self.client.get(
            reverse('web_downloader:error'),
            {'title': 'Test Error', 'message': 'Test message'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Error')

    def test_progress_endpoint_not_found(self):
        """Test progress endpoint returns 404 for non-existent download"""
        response = self.client.get(
            reverse('web_downloader:get_progress', kwargs={'download_id': 99999})
        )
        self.assertEqual(response.status_code, 404)

    def test_progress_endpoint_returns_data(self):
        """Test progress endpoint returns correct data for existing download"""
        download = VideoDownload.objects.create(
            url='https://www.youtube.com/watch?v=test',
            title='Test Video',
            status='downloading',
            progress=50
        )
        response = self.client.get(
            reverse('web_downloader:get_progress', kwargs={'download_id': download.id})
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['title'], 'Test Video')
        self.assertEqual(data['progress'], 50)
        self.assertEqual(data['status'], 'downloading')

    def test_delete_download(self):
        """Test deleting a download"""
        download = VideoDownload.objects.create(
            url='https://www.youtube.com/watch?v=test'
        )
        response = self.client.post(
            reverse('web_downloader:delete_download', kwargs={'download_id': download.id})
        )
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertFalse(VideoDownload.objects.filter(id=download.id).exists())

    @patch('web_downloader.views.start_download')
    def test_form_submission_creates_download(self, mock_start_download):
        """Test that form submission creates a download and starts it"""
        response = self.client.post(
            reverse('web_downloader:index'),
            {
                'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'format_type': 'mp4',
                'quality': '720p',
            }
        )
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(VideoDownload.objects.exists())
        mock_start_download.assert_called_once()


class DownloaderHelperTestCase(TestCase):
    """Test cases for the downloader helper module"""

    def test_quality_format_mappings(self):
        """Test that all quality options have format mappings"""
        expected_qualities = ['best', '1080p', '720p', '480p', 'worst']
        for quality in expected_qualities:
            self.assertIn(quality, YouTubeDownloader.VIDEO_QUALITY_FORMATS)

    def test_downloader_initialization_with_output_dir(self):
        """Test downloader initializes with specified output directory"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = YouTubeDownloader(output_dir=tmpdir)
            self.assertEqual(str(downloader.output_dir), tmpdir)

    def test_downloader_initialization_without_output_dir(self):
        """Test downloader creates temp directory when none specified"""
        downloader = YouTubeDownloader()
        self.assertTrue(downloader.output_dir.exists())
        downloader.cleanup()

