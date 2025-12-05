# YouTube Downloader

A production-ready YouTube downloader web application built with Django. Download YouTube videos as MP4 or extract audio as MP3.

![YouTube Downloader UI](https://github.com/user-attachments/assets/74a43194-93df-4819-b312-4db0ca46e68f)

## Features

- **MP4 Video Download**: Download videos in various qualities (Best, 1080p, 720p, 480p, Lowest)
- **MP3 Audio Extraction**: Extract high-quality audio from videos
- **URL Validation**: Validates YouTube URLs before processing
- **Video Metadata**: Fetches and displays video title, thumbnail, duration, and uploader
- **Progress Tracking**: Real-time download progress updates
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Modern UI**: Clean, responsive interface with Bootstrap/custom CSS

## Requirements

- Python 3.10+
- Django 4.2+
- yt-dlp
- ffmpeg (for audio extraction and video merging)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/dadyutenga/youtube_downloader.git
   cd youtube_downloader
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install ffmpeg** (required for audio extraction):
   - **Ubuntu/Debian**: `sudo apt install ffmpeg`
   - **macOS**: `brew install ffmpeg`
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

5. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

6. **Start the development server**:
   ```bash
   python manage.py runserver
   ```

7. **Open your browser** and navigate to `http://127.0.0.1:8000/`

## Project Structure

```
youtube_downloader/
├── youtube_downloader/          # Django project settings
│   ├── settings.py              # Configuration with production settings
│   ├── urls.py                  # Main URL routing
│   └── wsgi.py                  # WSGI application
├── web_downloader/              # Main Django app
│   ├── helpers/                 # Helper modules
│   │   └── downloader.py        # Core YouTube download logic
│   ├── templates/               # HTML templates
│   │   └── web_downloader/
│   │       ├── index.html       # Main page
│   │       ├── preview.html     # Video preview page
│   │       └── error.html       # Error page
│   ├── forms.py                 # Django forms with URL validation
│   ├── models.py                # Database models
│   ├── urls.py                  # App URL routing
│   ├── utils.py                 # Utility functions
│   └── views.py                 # View handlers
├── requirements.txt             # Python dependencies
└── manage.py                    # Django management script
```

## Usage

1. **Enter a YouTube URL** in the input field
2. **Select format**: MP4 (video) or MP3 (audio only)
3. **Choose quality** (for video downloads)
4. Click **Start Download**
5. Wait for the download to complete
6. Click **Download** to save the file to your device

## Production Deployment

For production deployment:

1. Set environment variables:
   ```bash
   export DJANGO_SECRET_KEY='your-secure-secret-key'
   export DJANGO_DEBUG='False'
   export DJANGO_ALLOWED_HOSTS='yourdomain.com,www.yourdomain.com'
   ```

2. Collect static files:
   ```bash
   python manage.py collectstatic
   ```

3. Use a production WSGI server like Gunicorn:
   ```bash
   pip install gunicorn
   gunicorn youtube_downloader.wsgi:application
   ```

## API Endpoints

- `GET /` - Main page with download form
- `POST /` - Submit download request
- `GET /preview/?url=<youtube_url>` - Preview video details
- `GET /progress/<download_id>/` - Get download progress (JSON)
- `GET /download/<download_id>/` - Download completed file
- `POST /delete/<download_id>/` - Delete a download
- `GET /api/video-info/?url=<youtube_url>` - Get video metadata (JSON)

## Testing

Run the test suite:
```bash
python manage.py test web_downloader
```

## Troubleshooting

- **"Invalid YouTube URL"**: Ensure the URL is a valid YouTube video or playlist link
- **Download fails**: Make sure ffmpeg is installed and accessible in your PATH
- **Signature cipher errors**: The app uses yt-dlp with optimal settings to handle most issues

## License

MIT License
