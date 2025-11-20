#!/usr/bin/env python3
"""
YouTube Playlist Downloader - Enhanced Version
Downloads videos/playlists from YouTube using yt-dlp
Features: Single video, progress bars, parallel downloads, GUI, range selection, auto-retry
"""

import subprocess
import sys
import json
import os
import platform
import zipfile
import shutil
import threading
import time
from pathlib import Path
from urllib.request import urlretrieve
from concurrent.futures import ThreadPoolExecutor, as_completed

# === UX ENHANCEMENTS START ===
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    print("Installing colorama...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'colorama'])
    from colorama import init, Fore, Style
    init(autoreset=True)

try:
    from tqdm import tqdm
except ImportError:
    print("Installing tqdm...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'tqdm'])
    from tqdm import tqdm

# Color helpers
GREEN = Fore.GREEN + Style.BRIGHT
YELLOW = Fore.YELLOW + Style.BRIGHT
RED = Fore.RED + Style.BRIGHT
CYAN = Fore.CYAN + Style.BRIGHT
WHITE = Fore.WHITE + Style.BRIGHT
RESET = Style.RESET_ALL

# Emoji constants
SUCCESS = GREEN + "Success"
WARNING = YELLOW + "Warning"
ERROR = RED + "Error"
INFO = CYAN + "Info"
DOWNLOAD = "Downloading"
SETUP = "Setting up environment"
PROCESS = "Processing"
CHECK = "Checking"
# === UX ENHANCEMENTS END ===

def get_os():
    """Detect the operating system"""
    system = platform.system().lower()
    if system == 'windows':
        return 'windows'
    elif system == 'darwin':
        return 'mac'
    elif system == 'linux':
        return 'linux'
    else:
        return 'unknown'

def check_command_exists(command):
    """Check if a command exists in PATH with improved detection"""
    # Special handling for yt-dlp as a Python module
    if command == 'yt-dlp':
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'yt_dlp', '--version'],
                capture_output=True,
                timeout=5,
                shell=False
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
    
    # Method 1: Try using shutil.which (most reliable)
    if shutil.which(command):
        return True
    
    # Method 2: Try direct execution
    try:
        result = subprocess.run(
            [command, '--version'],
            capture_output=True,
            timeout=5,
            shell=False
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Method 3: Windows - check common installation paths
    if platform.system().lower() == 'windows':
        common_paths = [
            r'C:\ffmpeg\bin\ffmpeg.exe',
            r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
            r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',
            str(Path.home() / 'ffmpeg' / 'ffmpeg.exe'),
            str(Path.home() / 'AppData' / 'Local' / 'Microsoft' / 'WinGet' / 'Packages' / 'Gyan.FFmpeg_*' / 'ffmpeg-*' / 'bin' / 'ffmpeg.exe'),
        ]
        
        for path in common_paths:
            # Handle wildcards in path
            if '*' in path:
                import glob
                matches = glob.glob(path)
                if matches and Path(matches[0]).exists():
                    return True
            elif Path(path).exists():
                return True
        
        # Check if ffmpeg is in any PATH directories
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
        for path_dir in path_dirs:
            ffmpeg_path = Path(path_dir) / 'ffmpeg.exe'
            if ffmpeg_path.exists():
                return True
    
    # Method 4: Unix-like systems - check common paths
    elif platform.system().lower() in ['linux', 'darwin']:
        common_paths = [
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
            '/opt/homebrew/bin/ffmpeg',  # Mac M1/M2
            '/opt/local/bin/ffmpeg',      # MacPorts
            str(Path.home() / '.local' / 'bin' / 'ffmpeg'),
        ]
        
        for path in common_paths:
            if Path(path).exists():
                return True
    
    return False

def verify_ffmpeg_installation():
    """Comprehensive ffmpeg verification with detailed feedback"""
    print(f"\n{INFO} Verifying ffmpeg installation...")
    
    # Check if ffmpeg is accessible
    if shutil.which('ffmpeg'):
        print(f"  {SUCCESS} ffmpeg found in PATH: {shutil.which('ffmpeg')}")
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            version_line = result.stdout.split('\n')[0]
            print(f"  {SUCCESS} Version: {version_line}")
            return True
        except Exception as e:
            print(f"  {WARNING} Found but unable to execute: {e}")
    
    # Windows-specific checks
    if platform.system().lower() == 'windows':
        print(f"\n  {CHECK} Checking common Windows locations...")
        
        search_paths = [
            (r'C:\ffmpeg\bin', 'C:\\ffmpeg\\bin'),
            (str(Path.home() / 'ffmpeg'), 'User home ffmpeg folder'),
            (r'C:\Program Files\ffmpeg\bin', 'Program Files'),
            (r'C:\Program Files (x86)\ffmpeg\bin', 'Program Files (x86)'),
        ]
        
        found_locations = []
        for path, description in search_paths:
            ffmpeg_exe = Path(path) / 'ffmpeg.exe'
            if ffmpeg_exe.exists():
                found_locations.append(str(ffmpeg_exe))
                print(f"  {INFO} Found at {description}: {ffmpeg_exe}")
        
        if found_locations:
            print(f"\n  {WARNING} ffmpeg is installed but not in PATH!")
            print(f"\n  To fix this, add one of these directories to your PATH:")
            for loc in found_locations:
                print(f"    - {Path(loc).parent}")
            print(f"\n  Quick fix options:")
            print("  1. Restart your terminal/command prompt")
            print("  2. Run this script as Administrator to auto-add to PATH")
            print("  3. Manually add to PATH:")
            print("     - Search 'Environment Variables' in Windows")
            print("     - Edit 'Path' under User or System variables")
            print("     - Add the ffmpeg\\bin directory")
            return False
        
        # Check WinGet packages
        winget_base = Path.home() / 'AppData' / 'Local' / 'Microsoft' / 'WinGet' / 'Packages'
        if winget_base.exists():
            ffmpeg_dirs = list(winget_base.glob('Gyan.FFmpeg*'))
            if ffmpeg_dirs:
                for ffmpeg_dir in ffmpeg_dirs:
                    bin_dirs = list(ffmpeg_dir.glob('ffmpeg-*/bin'))
                    if bin_dirs:
                        print(f"  {INFO} Found WinGet installation: {bin_dirs[0]}")
                        found_locations.append(str(bin_dirs[0]))
                
                if found_locations:
                    print(f"\n  {WARNING} ffmpeg installed via WinGet but not in PATH!")
                    print("  Try running: winget install Gyan.FFmpeg")
                    print("  Or add this to PATH: " + str(found_locations[0]))
                    return False
    
    # Unix-like systems
    else:
        print(f"\n  {CHECK} Checking common Unix/Mac locations...")
        common_paths = {
            '/usr/bin/ffmpeg': 'System binary',
            '/usr/local/bin/ffmpeg': 'Local binary',
            '/opt/homebrew/bin/ffmpeg': 'Homebrew (Apple Silicon)',
            '/usr/local/Cellar/ffmpeg': 'Homebrew (Intel)',
            '/opt/local/bin/ffmpeg': 'MacPorts',
        }
        
        found = False
        for path, description in common_paths.items():
            if Path(path).exists():
                print(f"  {INFO} Found at {description}: {path}")
                found = True
        
        if found:
            print(f"\n  {WARNING} ffmpeg found but not in current PATH")
            print("  Try restarting your terminal or run: hash -r")
            return False
    
    print(f"\n  {ERROR} ffmpeg not found on this system")
    return False


def install_ytdlp():
    """Install yt-dlp using pip"""
    print(f"{DOWNLOAD} Installing yt-dlp...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'yt-dlp'])
        print(f"{SUCCESS} yt-dlp installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print(f"{ERROR} Failed to install yt-dlp. Please install manually:")
        print("  pip install yt-dlp")
        return False

def add_to_windows_path(directory):
    """Add directory to Windows PATH (requires admin rights) - Enhanced version"""
    try:
        import winreg
        
        print(f"\n  {SETUP} Attempting to add {directory} to PATH...")
        
        # Try user PATH first (doesn't require admin)
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0, winreg.KEY_ALL_ACCESS)
            current_path, _ = winreg.QueryValueEx(key, 'PATH')
            
            # Check if already in PATH
            path_dirs = current_path.split(';')
            if any(directory.lower() == p.lower() for p in path_dirs if p):
                print(f"  {SUCCESS} Already in PATH: {directory}")
                winreg.CloseKey(key)
                return True
            
            # Add to PATH
            new_path = f"{current_path};{directory}" if current_path else directory
            winreg.SetValueEx(key, 'PATH', 0, winreg.REG_EXPAND_SZ, new_path)
            winreg.CloseKey(key)
            
            # Update current process environment
            os.environ['PATH'] = f"{os.environ['PATH']};{directory}"
            
            # Broadcast environment change
            try:
                import ctypes
                HWND_BROADCAST = 0xFFFF
                WM_SETTINGCHANGE = 0x1A
                SMTO_ABORTIFHUNG = 0x0002
                result = ctypes.c_long()
                SendMessageTimeoutW = ctypes.windll.user32.SendMessageTimeoutW
                SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, 'Environment', 
                                   SMTO_ABORTIFHUNG, 5000, ctypes.byref(result))
            except:
                pass
            
            print(f"  {SUCCESS} Added to user PATH: {directory}")
            print(f"  {INFO} Changes will take effect in new terminal windows")
            print(f"  {INFO} For this session, you may need to restart the script")
            return True
            
        except PermissionError:
            print(f"  {WARNING} Unable to modify user PATH (permission denied)")
            print("\n  Manual steps:")
            print("  1. Press Win + R, type 'sysdm.cpl', press Enter")
            print("  2. Go to 'Advanced' tab to 'Environment Variables'")
            print("  3. Under 'User variables', select 'Path' to 'Edit'")
            print(f"  4. Click 'New' and add: {directory}")
            print("  5. Click 'OK' on all dialogs")
            return False
            
    except Exception as e:
        print(f"  {ERROR} Could not modify PATH: {e}")
        print(f"\n  Please manually add to PATH: {directory}")
        print("\n  Steps:")
        print("  1. Search 'Environment Variables' in Windows Start")
        print("  2. Click 'Environment Variables' button")
        print("  3. Under 'User variables', select 'Path' to 'Edit'")
        print(f"  4. Click 'New' and add: {directory}")
        return False

def install_ffmpeg_windows():
    """Install ffmpeg on Windows"""
    print(f"\n{DOWNLOAD} Installing ffmpeg for Windows...")
    
    # Check common installation methods
    if shutil.which('winget'):
        print(f"  {PROCESS} Attempting installation via winget...")
        with tqdm(total=1, desc="winget install", bar_format="{l_bar}{bar} [ time left: {remaining} ]") as pbar:
            try:
                subprocess.run(['winget', 'install', 'Gyan.FFmpeg', '--silent'], check=True)
                pbar.update(1)
                print(f"  {SUCCESS} ffmpeg installed via winget!")
                return True
            except subprocess.CalledProcessError:
                pbar.close()
                print(f"  {WARNING} winget installation failed, trying manual installation...")
    
    if shutil.which('choco'):
        print(f"  {PROCESS} Attempting installation via chocolatey...")
        with tqdm(total=1, desc="choco install", bar_format="{l_bar}{bar} [ time left: {remaining} ]") as pbar:
            try:
                subprocess.run(['choco', 'install', 'ffmpeg', '-y'], check=True)
                pbar.update(1)
                print(f"  {SUCCESS} ffmpeg installed via chocolatey!")
                return True
            except subprocess.CalledProcessError:
                pbar.close()
                print(f"  {WARNING} chocolatey installation failed, trying manual installation...")
    
    # Manual installation
    print(f"  {DOWNLOAD} Downloading ffmpeg manually...")
    try:
        ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        install_dir = Path.home() / "ffmpeg"
        zip_path = install_dir / "ffmpeg.zip"
        
        install_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"  {DOWNLOAD} Downloading from {ffmpeg_url}...")
        with tqdm(unit='B', unit_scale=True, desc="Download", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [elapsed: {elapsed}]") as pbar:
            def reporthook(blocknum, blocksize, totalsize):
                if blocknum == 0:
                    pbar.total = totalsize
                pbar.update(blocksize)
            urlretrieve(ffmpeg_url, zip_path, reporthook=reporthook)
        
        print(f"  {PROCESS} Extracting...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(install_dir)
        
        # Find the bin directory
        bin_dirs = list(install_dir.glob("*/bin"))
        if bin_dirs:
            bin_dir = bin_dirs[0]
            
            # Copy executables to install_dir
            for exe in bin_dir.glob("*.exe"):
                shutil.copy2(exe, install_dir)
            
            # Add to PATH
            add_to_windows_path(str(install_dir))
            
            # Cleanup
            zip_path.unlink()
            for item in install_dir.iterdir():
                if item.is_dir() and item.name.startswith('ffmpeg-'):
                    shutil.rmtree(item)
            
            print(f"  {SUCCESS} ffmpeg installed to {install_dir}")
            return True
        
    except Exception as e:
        print(f"  {ERROR} Manual installation failed: {e}")
        print("\n  Please install ffmpeg manually:")
        print("  1. Download from: https://www.gyan.dev/ffmpeg/builds/")
        print("  2. Extract and add to PATH")
        return False
    
    return False

def install_ffmpeg_mac():
    """Install ffmpeg on macOS"""
    print(f"\n{DOWNLOAD} Installing ffmpeg for macOS...")
    
    if not shutil.which('brew'):
        print(f"  {ERROR} Homebrew not found. Please install Homebrew first:")
        print("  /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        return False
    
    try:
        print(f"  {PROCESS} Installing via Homebrew...")
        with tqdm(total=1, desc="brew install", bar_format="{l_bar}{bar} [ time left: {remaining} ]") as pbar:
            subprocess.run(['brew', 'install', 'ffmpeg'], check=True)
            pbar.update(1)
        print(f"  {SUCCESS} ffmpeg installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  {ERROR} Installation failed: {e}")
        return False

def install_ffmpeg_linux():
    """Install ffmpeg on Linux"""
    print(f"\n{DOWNLOAD} Installing ffmpeg for Linux...")
    
    # Try different package managers
    package_managers = [
        (['sudo', 'apt', 'update'], ['sudo', 'apt', 'install', '-y', 'ffmpeg']),
        (['sudo', 'yum', 'install', '-y', 'ffmpeg'], None),
        (['sudo', 'dnf', 'install', '-y', 'ffmpeg'], None),
        (['sudo', 'pacman', '-S', '--noconfirm', 'ffmpeg'], None),
    ]
    
    for commands in package_managers:
        update_cmd, install_cmd = commands if len(commands) == 2 else (None, commands[0])
        
        try:
            if update_cmd:
                with tqdm(total=1, desc="apt update", bar_format="{l_bar}{bar}") as pbar:
                    subprocess.run(update_cmd, check=True, capture_output=True)
                    pbar.update(1)
            
            with tqdm(total=1, desc="install ffmpeg", bar_format="{l_bar}{bar}") as pbar:
                subprocess.run(install_cmd, check=True)
                pbar.update(1)
            print(f"  {SUCCESS} ffmpeg installed successfully!")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    print(f"  {ERROR} Could not install ffmpeg automatically.")
    print("  Please install manually using your package manager:")
    print("    Ubuntu/Debian: sudo apt install ffmpeg")
    print("    Fedora: sudo dnf install ffmpeg")
    print("    Arch: sudo pacman -S ffmpeg")
    return False

def install_ffmpeg():
    """Install ffmpeg based on OS"""
    os_type = get_os()
    
    if os_type == 'windows':
        return install_ffmpeg_windows()
    elif os_type == 'mac':
        return install_ffmpeg_mac()
    elif os_type == 'linux':
        return install_ffmpeg_linux()
    else:
        print(f"{ERROR} Unknown operating system. Please install ffmpeg manually.")
        return False

def setup_dependencies():
    """Check and install all required dependencies"""
    print(f"\n{'=' * 60}")
    print(f"{WHITE}Checking dependencies...")
    print(f"{'=' * 60}")
    
    os_type = get_os()
    print(f"\n{INFO} Detected OS: {os_type.upper()}")
    
    # Check colorama
    print(f"\n[1/4] {CHECK} Checking colorama...")
    try:
        from colorama import init
        print(f"  {SUCCESS} colorama installed")
    except ImportError:
        print(f"  {DOWNLOAD} Installing colorama...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'colorama'])
        print(f"  {SUCCESS} colorama installed")

    # Check tqdm
    print(f"\n[2/4] {CHECK} Checking tqdm...")
    try:
        from tqdm import tqdm
        print(f"  {SUCCESS} tqdm installed")
    except ImportError:
        print(f"  {DOWNLOAD} Installing tqdm...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'tqdm'])
        print(f"  {SUCCESS} tqdm installed")

    # Check yt-dlp
    print(f"\n[3/4] {CHECK} Checking yt-dlp...")
    if check_command_exists('yt-dlp'):
        print(f"  {SUCCESS} yt-dlp is already installed")
        try:
            with tqdm(total=1, desc="Updating yt-dlp", bar_format="{l_bar}{bar}") as pbar:
                subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'yt-dlp'], 
                             capture_output=True, check=True, timeout=30)
                pbar.update(1)
            print(f"  {SUCCESS} Updated to latest version")
        except:
            pass
    else:
        if not install_ytdlp():
            return False
    
    # Check ffmpeg with improved detection
    print(f"\n[4/4] {CHECK} Checking ffmpeg...")
    if check_command_exists('ffmpeg'):
        print(f"  {SUCCESS} ffmpeg is already installed")
        # Verify it actually works
        verify_ffmpeg_installation()
    else:
        ffmpeg_found = verify_ffmpeg_installation()
        
        if not ffmpeg_found:
            print(f"\n  {ERROR} ffmpeg not found")
            install = input(f"\n  {INFO} Install ffmpeg now? (y/n): ").strip().lower()
            if install == 'y':
                if not install_ffmpeg():
                    print(f"\n  {WARNING} Warning: Videos may download as separate audio/video files")
                    print("  You'll need to merge them manually or install ffmpeg later")
                else:
                    # Verify installation
                    print(f"\n  {PROCESS} Verifying installation...")
                    time.sleep(2)  # Give system time to update PATH
                    if not check_command_exists('ffmpeg'):
                        print(f"\n  {WARNING} ffmpeg installed but may require terminal restart")
                        print("  If downloads fail, please restart this script")
            else:
                print(f"\n  {INFO} Skipping ffmpeg installation")
                print(f"  {WARNING} Warning: Videos will download as separate audio/video files")
    
    print(f"\n{'=' * 60}")
    print(f"{SUCCESS} Setup complete!")
    print(f"{'=' * 60}")
    return True


def get_playlist_info(playlist_url):
    """Extract playlist information and video URLs"""
    print(f"\n{PROCESS} Fetching playlist information...")
    try:
        cmd = [
            sys.executable,
            '-m',
            'yt_dlp',
            '--flat-playlist',
            '--dump-json',
            playlist_url
        ]
        
        with tqdm(total=1, desc="Getting info", bar_format="{l_bar}{bar}") as pbar:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            pbar.update(1)
        
        videos = []
        for line in result.stdout.strip().split('\n'):
            if line:
                video_data = json.loads(line)
                videos.append({
                    'title': video_data.get('title', 'Unknown'),
                    'url': f"https://www.youtube.com/watch?v={video_data['id']}",
                    'id': video_data['id'],
                    'duration': video_data.get('duration', 0)
                })
        
        print(f"  {SUCCESS} Found {len(videos)} videos")
        return videos
    except subprocess.CalledProcessError as e:
        print(f"{ERROR} Error fetching playlist info: {e}")
        print(f"{INFO} Error output: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print(f"{ERROR} Error parsing playlist data: {e}")
        return None

def download_single_video(video_url, output_dir='downloads', quality='best', max_retries=3, use_cookies=None):
    """
    Download a single video with progress bar and retry logic
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    quality_formats = {
        'best': 'bestvideo+bestaudio/best',
        '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
        'worst': 'worstvideo+worstaudio/worst'
    }
    
    format_string = quality_formats.get(quality, quality_formats['best'])
    
    cmd = [
        sys.executable,
        '-m',
        'yt_dlp',
        '-f', format_string,
        '--merge-output-format', 'mp4',
        '-o', f'{output_dir}/%(title)s.%(ext)s',
        '--newline',
        '--progress',
    ]
    
    if use_cookies:
        if use_cookies == 'chrome':
            cmd.extend(['--cookies-from-browser', 'chrome'])
        elif use_cookies == 'firefox':
            cmd.extend(['--cookies-from-browser', 'firefox'])
        elif use_cookies == 'edge':
            cmd.extend(['--cookies-from-browser', 'edge'])
        elif use_cookies == 'brave':
            cmd.extend(['--cookies-from-browser', 'brave'])
        elif use_cookies == 'opera':
            cmd.extend(['--cookies-from-browser', 'opera'])
    else:
        cmd.extend([
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '--extractor-args', 'youtube:player_client=android,web',
            '--no-check-certificate',
        ])
    
    cmd.append(video_url)
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n{DOWNLOAD} Downloading video (Attempt {attempt}/{max_retries})...")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                     text=True, bufsize=1)
            
            pbar = None
            for line in process.stdout:
                line = line.strip()
                if '[download]' in line and '%' in line:
                    if not pbar:
                        pbar = tqdm(total=100, desc="Progress", bar_format="{l_bar}{bar}| {percentage:3.0f}%")
                    percent = float(line.split('%')[0].split()[-1])
                    pbar.update(percent - pbar.n)
                elif line:
                    if pbar:
                        pbar.close()
                        pbar = None
                    print(f"  {INFO} {line}")
            
            if pbar:
                pbar.close()
            
            process.wait()
            
            if process.returncode == 0:
                print(f"\n{SUCCESS} Download complete!")
                return True
            else:
                if attempt < max_retries:
                    print(f"\n{WARNING} Download failed. Retrying in 3 seconds...")
                    time.sleep(3)
                else:
                    print(f"\n{ERROR} Download failed after {max_retries} attempts")
                    return False
                    
        except KeyboardInterrupt:
            print(f"\n\n{INFO} Download interrupted by user")
            return False
        except Exception as e:
            if attempt < max_retries:
                print(f"\n{ERROR} Error: {e}. Retrying in 3 seconds...")
                time.sleep(3)
            else:
                print(f"\n{ERROR} Error after {max_retries} attempts: {e}")
                return False
    
    return False

def download_video_worker(video_info, output_dir, quality, max_retries=3, use_cookies=None):
    """Worker function for parallel downloads"""
    video_url = video_info['url']
    video_title = video_info['title']
    video_index = video_info.get('index', '')
    
    quality_formats = {
        'best': 'bestvideo+bestaudio/best',
        '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
        'worst': 'worstvideo+worstaudio/worst'
    }
    
    format_string = quality_formats.get(quality, quality_formats['best'])
    
    if video_index:
        output_template = f'{output_dir}/{video_index} - %(title)s.%(ext)s'
    else:
        output_template = f'{output_dir}/%(title)s.%(ext)s'
    
    cmd = [
        sys.executable,
        '-m',
        'yt_dlp',
        '-f', format_string,
        '--merge-output-format', 'mp4',
        '-o', output_template,
        '--no-progress',
        '--restrict-filenames',
    ]
    
    # Add cookie options to bypass bot detection
    if use_cookies:
        if use_cookies == 'chrome':
            cmd.extend(['--cookies-from-browser', 'chrome'])
        elif use_cookies == 'firefox':
            cmd.extend(['--cookies-from-browser', 'firefox'])
        elif use_cookies == 'edge':
            cmd.extend(['--cookies-from-browser', 'edge'])
        elif use_cookies == 'brave':
            cmd.extend(['--cookies-from-browser', 'brave'])
        elif use_cookies == 'opera':
            cmd.extend(['--cookies-from-browser', 'opera'])
    else:
        cmd.extend([
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '--extractor-args', 'youtube:player_client=android,web',
            '--no-check-certificate',
        ])
    
    cmd.append(video_url)
    
    for attempt in range(1, max_retries + 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode == 0:
                return {'success': True, 'title': video_title, 'index': video_index}
            else:
                if attempt < max_retries:
                    time.sleep(3)
                else:
                    return {'success': False, 'title': video_title, 'index': video_index, 
                           'error': 'Max retries exceeded'}
                    
        except subprocess.TimeoutExpired:
            if attempt < max_retries:
                time.sleep(3)
            else:
                return {'success': False, 'title': video_title, 'index': video_index, 
                       'error': 'Timeout'}
        except Exception as e:
            if attempt < max_retries:
                time.sleep(3)
            else:
                return {'success': False, 'title': video_title, 'index': video_index, 
                       'error': str(e)}
    
    return {'success': False, 'title': video_title, 'index': video_index}

def download_playlist_parallel(playlist_url, output_dir='downloads', quality='best', 
                               max_workers=3, video_range=None, use_cookies=None):
    """
    Download playlist videos in parallel
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    videos = get_playlist_info(playlist_url)
    
    if not videos:
        print(f"{ERROR} Failed to fetch playlist information.")
        return False
    
    # Apply video range filter
    if video_range:
        start, end = video_range
        start = max(1, start)
        end = min(len(videos), end)
        videos = videos[start-1:end]
        print(f"{INFO} Downloading videos {start} to {end} ({len(videos)} videos)")
    else:
        print(f"{INFO} Found {len(videos)} videos")
    
    # Add index to video info
    for i, video in enumerate(videos, 1):
        video['index'] = str(i + (video_range[0] - 1 if video_range else 0)).zfill(3)
    
    print(f"{PROCESS} Starting parallel download with {max_workers} workers...")
    print(f"{INFO} Output directory: {Path(output_dir).absolute()}")
    print(f"{'─' * 60}")
    
    successful = 0
    failed = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_video = {
            executor.submit(download_video_worker, video, output_dir, quality, max_retries, use_cookies): video 
            for video in videos
        }
        
        pbar = tqdm(total=len(videos), desc="Overall", bar_format="{l_bar}{bar}| {n}/{total} [{elapsed}<{remaining}]")
        
        for future in as_completed(future_to_video):
            result = future.result()
            if result['success']:
                successful += 1
                index_str = f"[{result['index']}] " if result['index'] else ""
                pbar.set_description(f"{SUCCESS} {index_str}{result['title'][:30]}...")
            else:
                failed.append(result)
                index_str = f"[{result['index']}] " if result['index'] else ""
                error_msg = result.get('error', 'Unknown error')
                pbar.set_description(f"{ERROR} {index_str}{result['title'][:30]}...")
            pbar.update(1)
        
        pbar.close()
    
    print(f"\n{'=' * 60}")
    print(f"{SUCCESS} Download complete!")
    print(f"{SUCCESS} Successful: {successful}/{len(videos)}")
    if failed:
        print(f"{WARNING} Failed: {len(failed)}")
        print(f"\n{ERROR} Failed videos:")
        for video in failed:
            index_str = f"[{video['index']}] " if video['index'] else ""
            print(f"  • {index_str}{video['title']}")
    print(f"{'=' * 60}")
    
    return True

def download_playlist(playlist_url, output_dir='downloads', quality='best', use_cookies=None):
    """
    Download all videos from a playlist (sequential with progress)
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    quality_formats = {
        'best': 'bestvideo+bestaudio/best',
        '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
        'worst': 'worstvideo+worstaudio/worst'
    }
    
    format_string = quality_formats.get(quality, quality_formats['best'])
    
    print(f"\n{DOWNLOAD} Downloading playlist to: {output_dir}")
    print(f"{INFO} Quality: {quality}")
    print(f"{'─' * 60}")
    
    cmd = [
        sys.executable,
        '-m',
        'yt_dlp',
        '-f', format_string,
        '--merge-output-format', 'mp4',
        '-o', f'{output_dir}/%(playlist_index)s - %(title)s.%(ext)s',
        '--no-playlist-reverse',
        '--ignore-errors',
        '--continue',
        '--newline',
        '--restrict-filenames',
    ]
    
    # Add cookie options to bypass bot detection
    if use_cookies:
        if use_cookies == 'chrome':
            cmd.extend(['--cookies-from-browser', 'chrome'])
        elif use_cookies == 'firefox':
            cmd.extend(['--cookies-from-browser', 'firefox'])
        elif use_cookies == 'edge':
            cmd.extend(['--cookies-from-browser', 'edge'])
        elif use_cookies == 'brave':
            cmd.extend(['--cookies-from-browser', 'brave'])
        elif use_cookies == 'opera':
            cmd.extend(['--cookies-from-browser', 'opera'])
    else:
        cmd.extend([
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '--extractor-args', 'youtube:player_client=android,web',
            '--no-check-certificate',
        ])
    
    cmd.append(playlist_url)
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, bufsize=1)
        
        pbar = None
        current_video = ""
        for line in process.stdout:
            line = line.strip()
            if line:
                if '[download]' in line and '%' in line:
                    if not pbar:
                        pbar = tqdm(total=100, desc=f"{current_video}", bar_format="{l_bar}{bar}| {percentage:3.0f}%")
                    percent = float(line.split('%')[0].split()[-1])
                    pbar.update(percent - pbar.n)
                elif '[download]' in line and 'Destination:' in line:
                    if pbar:
                        pbar.close()
                    current_video = line.split('Destination:')[-1].strip().split('/')[-1]
                    print(f"\n{DOWNLOAD} {current_video}")
                else:
                    if pbar:
                        pbar.close()
                        pbar = None
                    if '\r' not in line:
                        print(f"  {INFO} {line}")
        
        if pbar:
            pbar.close()
        
        process.wait()
        
        print(f"\n{'=' * 60}")
        print(f"{SUCCESS} Download complete!")
        print(f"{'=' * 60}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n{ERROR} Error during download: {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n\n{INFO} Download interrupted by user")
        print("You can resume by running the script again with the same URL")
        return False

def list_playlist_videos(playlist_url):
    """List all videos in the playlist without downloading"""
    print(f"\n{PROCESS} Fetching playlist information...")
    videos = get_playlist_info(playlist_url)
    
    if not videos:
        print(f"{ERROR} Failed to fetch playlist information.")
        return
    
    print(f"\n{SUCCESS} Found {len(videos)} videos in playlist:\n")
    print(f"{'─' * 90}")
    
    for i, video in enumerate(videos, 1):
        duration = video['duration']
        minutes = duration // 60
        seconds = duration % 60
        print(f"{WHITE}{i:3d}. {video['title']}")
        print(f"     {CYAN}URL: {video['url']} | Duration: {minutes}:{seconds:02d}")
        print()
  
def main():
    """Main function"""
    print(f"\n{'=' * 60}")
    print(f"{WHITE}YouTube Playlist Downloader - Enhanced")
    print(f"{'=' * 60}")
    print()
    
    # Setup dependencies
    if not setup_dependencies():
        print(f"\n{ERROR} Failed to setup dependencies. Exiting.")
        return
    
    print()
    
    
    # CLI Mode
    print(f"\n{'=' * 60}")
    
    # Get URL
    url = input(f"{WHITE}Enter YouTube URL (video or playlist): {RESET}").strip()
    
    if not url:
        print(f"{ERROR} No URL provided. Exiting.")
        return
    
    # Detect if it's a playlist
    is_playlist = 'playlist' in url.lower() or 'list=' in url
    
    if is_playlist:
        print(f"\n{SUCCESS} Playlist detected")
        print(f"\n{WHITE}What would you like to do?")
        print(f"{CYAN}1. List all videos (no download)")
        print(f"{CYAN}2. Download entire playlist (sequential)")
        print(f"{CYAN}3. Download entire playlist (parallel - faster)")
        print(f"{CYAN}4. Download specific video range")
        print(f"{CYAN}5. Download with custom quality")
        
        choice = input(f"\n{INFO}Enter choice (1-5): {RESET}").strip()
        
        if choice == '1':
            list_playlist_videos(url)
        
        elif choice == '2':
            output_dir = input(f"\n{INFO}Enter output directory (press Enter for 'downloads'): {RESET}").strip()
            if not output_dir:
                output_dir = 'downloads'
            print(f"{SUCCESS} Videos will be saved to: {Path(output_dir).absolute()}")
            download_playlist(url, output_dir)
        
        elif choice == '3':
            output_dir = input(f"\n{INFO}Enter output directory (press Enter for 'downloads'): {RESET}").strip()
            if not output_dir:
                output_dir = 'downloads'
            
            workers = input(f"{INFO}Number of parallel downloads (1-10, press Enter for 3): {RESET}").strip()
            try:
                workers = int(workers) if workers else 3
                workers = max(1, min(workers, 10))
            except ValueError:
                workers = 3
            
            print(f"\n{SUCCESS} Videos will be saved to: {Path(output_dir).absolute()}")
            print(f"{INFO} Using {workers} parallel workers")
            download_playlist_parallel(url, output_dir, max_workers=workers)
        
        elif choice == '4':
            print(f"\n{INFO}Enter video range to download:")
            try:
                start = int(input(f"  {WHITE}Start from video number: {RESET}").strip())
                end = int(input(f"  {WHITE}End at video number: {RESET}").strip())
                
                if start > end or start < 1:
                    print(f"{ERROR} Invalid range. Exiting.")
                    return
                
                output_dir = input(f"\n{INFO}Enter output directory (press Enter for 'downloads'): {RESET}").strip()
                if not output_dir:
                    output_dir = 'downloads'
                
                use_parallel = input(f"{INFO}Use parallel downloads? (y/n, press Enter for yes): {RESET}").strip().lower()
                
                if use_parallel != 'n':
                    workers = input(f"{INFO}Number of parallel downloads (1-10, press Enter for 3): {RESET}").strip()
                    try:
                        workers = int(workers) if workers else 3
                        workers = max(1, min(workers, 10))
                    except ValueError:
                        workers = 3
                    
                    print(f"\n{SUCCESS} Videos will be saved to: {Path(output_dir).absolute()}")
                    download_playlist_parallel(url, output_dir, max_workers=workers, 
                                             video_range=(start, end))
                else:
                    print(f"\n{SUCCESS} Videos will be saved to: {Path(output_dir).absolute()}")
                    print(f"\n{WARNING} Note: Sequential download doesn't support range selection yet.")
                    print(f"{INFO} Using parallel download with 1 worker instead.")
                    download_playlist_parallel(url, output_dir, max_workers=1, 
                                             video_range=(start, end))
                    
            except ValueError:
                print(f"{ERROR} Invalid input. Exiting.")
                return
        
        elif choice == '5':
            print(f"\n{WHITE}Select video quality:")
            print(f"{CYAN}  1. best   - Best available quality")
            print(f"{CYAN}  2. 1080p  - Full HD (1080p)")
            print(f"{CYAN}  3. 720p   - HD (720p)")
            print(f"{CYAN}  4. 480p   - SD (480p)")
            print(f"{CYAN}  5. worst  - Lowest quality (smallest file)")

            quality_map = {
                '1': 'best',
                '2': '1080p',
                '3': '720p',
                '4': '480p',
                '5': 'worst'
            }

            while True:
                choice = input(f"\n{INFO}Enter choice (1–5, press Enter for best): {RESET}").strip()
                if not choice:
                    quality = 'best'
                    break
                if choice in quality_map:
                    quality = quality_map[choice]
                    break
                else:
                    print(f"{ERROR} Invalid choice. Please enter 1–5 or press Enter for best.")
            
            output_dir = input(f"\n{INFO}Enter output directory (press Enter for 'downloads'): {RESET}").strip()
            if not output_dir:
                output_dir = 'downloads'
            
            use_parallel = input(f"{INFO}Use parallel downloads? (y/n, press Enter for yes): {RESET}").strip().lower()
            
            if use_parallel != 'n':
                workers = input(f"{INFO}Number of parallel downloads (1-10, press Enter for 3): {RESET}").strip()
                try:
                    workers = int(workers) if workers else 3
                    workers = max(1, min(workers, 10))
                except ValueError:
                    workers = 3
                
                print(f"\n{SUCCESS} Videos will be saved to: {Path(output_dir).absolute()}")
                download_playlist_parallel(url, output_dir, quality, workers)
            else:
                print(f"\n{SUCCESS} Videos will be saved to: {Path(output_dir).absolute()}")
                download_playlist(url, output_dir, quality)
        
        else:
            print(f"{ERROR} Invalid choice. Exiting.")
    
    else:
        # Single video
        print(f"\n{WHITE}Select video quality:")
        print(f"{CYAN}  1. best   - Best available quality")
        print(f"{CYAN}  2. 1080p  - Full HD (1080p)")
        print(f"{CYAN}  3. 720p   - HD (720p)")
        print(f"{CYAN}  4. 480p   - SD (480p)")
        print(f"{CYAN}  5. worst  - Lowest quality (smallest file)")

        quality_map = {
            '1': 'best',
            '2': '1080p',
            '3': '720p',
            '4': '480p',
            '5': 'worst'
        }

        while True:
            choice = input(f"\n{INFO}Enter choice (1–5, press Enter for best): {RESET}").strip()
            if not choice:
                quality = 'best'
                break
            if choice in quality_map:
                quality = quality_map[choice]
                break
            else:
                print(f"{ERROR} Invalid choice. Please enter 1–5 or press Enter for best.")
        
        output_dir = input(f"{INFO}Enter output directory (press Enter for 'downloads'): {RESET}").strip()
        if not output_dir:
            output_dir = 'downloads'
        
        # Ask about browser cookies for bot detection bypass
        print(f"\n{YELLOW}If you're getting bot detection errors, use browser cookies:")
        print(f"{CYAN}  1. Chrome")
        print(f"{CYAN}  2. Firefox")
        print(f"{CYAN}  3. Edge")
        print(f"{CYAN}  4. Brave")
        print(f"{CYAN}  5. Opera")
        print(f"{CYAN}  6. None (try without cookies)")
        
        browser_choice = input(f"\n{INFO}Select browser (1-6, press Enter for Chrome): {RESET}").strip()
        browser_map = {
            '1': 'chrome',
            '2': 'firefox',
            '3': 'edge',
            '4': 'brave',
            '5': 'opera',
            '6': None,
            '': 'chrome'
        }
        use_cookies = browser_map.get(browser_choice, 'chrome')
        
        print(f"\n{SUCCESS} Video will be saved to: {Path(output_dir).absolute()}")
        if use_cookies:
            print(f"{INFO} Using cookies from: {use_cookies.upper()}")
            print(f"{YELLOW}Note: Make sure you're logged into YouTube in {use_cookies.capitalize()}")
        
        # Allow downloading multiple single videos without quitting
        while True:
            success = download_single_video(url, output_dir, quality, use_cookies=use_cookies)
            if success:
                choice = input(f"\n{INFO} Downloaded successfully. Download another URL? (y/n): {RESET}").strip().lower()
            else:
                choice = input(f"\n{INFO} Download failed. Try another URL? (y/n): {RESET}").strip().lower()

            if choice == 'y':
                url = input(f"{WHITE}Enter YouTube URL (video or playlist): {RESET}").strip()
                if not url:
                    print(f"{ERROR} No URL provided. Returning to main menu.")
                    break
                # If user provided a playlist URL, return control to main to handle playlist options
                if 'playlist' in url.lower() or 'list=' in url:
                    print(f"\n{INFO} Playlist detected. Returning to main menu to handle playlist options.")
                    main()
                    return
                # continue loop to download the next single video
                continue
            else:
                print(f"\n{INFO} Returning to main menu.")
                break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{INFO} Exiting...")
        sys.exit(0)