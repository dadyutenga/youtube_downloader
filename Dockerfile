# Stage 1: Builder
FROM python:3.13-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt gunicorn


# Stage 2: Production
FROM python:3.13-slim-bookworm AS production

# Labels
LABEL maintainer="Ditronics"
LABEL description="Ditronics YouTube Downloader"
LABEL version="1.0"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=youtube_downloader.settings \
    DB_DIR=/app/data

WORKDIR /app

# Install runtime dependencies only (ffmpeg for yt-dlp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    cron \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /var/cache/apt/archives/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Copy application code
COPY --chown=appuser:appgroup . .

# Create necessary directories
RUN mkdir -p /app/downloads /app/staticfiles /app/logs /app/data && \
    chown -R appuser:appgroup /app

# Setup cron job for daily cleanup of downloads folder
RUN echo "0 3 * * * find /app/downloads -type f -mtime +1 -delete 2>/dev/null" > /etc/cron.d/cleanup-downloads && \
    echo "0 3 * * * find /app/downloads -type d -empty -delete 2>/dev/null" >> /etc/cron.d/cleanup-downloads && \
    chmod 0644 /etc/cron.d/cleanup-downloads && \
    crontab /etc/cron.d/cleanup-downloads

# Collect static files
RUN python manage.py collectstatic --noinput --clear

# Expose port 8090
EXPOSE 8090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8090/')" || exit 1

# Copy and set entrypoint script
COPY --chown=appuser:appgroup docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8090", "--workers", "2", "--threads", "4", "--worker-class", "gthread", "--timeout", "300", "youtube_downloader.wsgi:application"]
