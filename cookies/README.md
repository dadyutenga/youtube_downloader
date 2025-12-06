# YouTube Cookies Setup

YouTube now requires authentication to prevent bot detection. You need to export cookies from your browser.

## How to Export Cookies

### Option 1: Using Browser Extension (Recommended)

1. Install a cookie export extension:
   - **Chrome**: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - **Firefox**: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

2. Go to [YouTube](https://www.youtube.com) and **sign in** to your Google account

3. Click the extension icon and export cookies for `youtube.com`

4. Save the file as `cookies.txt` in this folder

### Option 2: Using yt-dlp (from your local machine)

If you have yt-dlp installed locally with a browser:

```bash
# Export from Chrome
yt-dlp --cookies-from-browser chrome --cookies cookies.txt "https://www.youtube.com"

# Export from Firefox
yt-dlp --cookies-from-browser firefox --cookies cookies.txt "https://www.youtube.com"

# Export from Edge
yt-dlp --cookies-from-browser edge --cookies cookies.txt "https://www.youtube.com"
```

Then copy the `cookies.txt` file to your server.

## File Location

Place the `cookies.txt` file in:
```
~/web/youtube_downloader/cookies/cookies.txt
```

## Important Notes

- **Keep cookies private** - they contain your YouTube login session
- **Cookies expire** - you may need to re-export them periodically (usually every few weeks)
- **Use a dedicated account** - consider creating a separate Google account for this
- **Don't share** - never commit cookies.txt to git

## After Adding Cookies

Restart the container:
```bash
cd ~/web/youtube_downloader
docker compose restart
```

## Troubleshooting

If you still get bot detection errors:
1. Make sure you're signed into YouTube when exporting
2. Try a different browser
3. Clear YouTube cookies and sign in fresh before exporting
4. Check if the cookies.txt file has content (not empty)
