import time
import hashlib
import os
import tempfile
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

try:
    import win32clipboard
except ImportError:
    print("Error: pywin32 is required. Run: python -m pip install pywin32")
    sys.exit(1)
try:
    from PIL import ImageGrab, Image
except ImportError:
    print("Error: Pillow is required. Run: python -m pip install pillow")
    sys.exit(1)

# ----------------- Configuration -----------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")
WORKER_URL = os.getenv("CLOUDFARE_WORKER_URL")

if not all([BOT_TOKEN, CHAT_ID, WORKER_URL]):
    print("Error: Missing credentials. Please check your .env file.")
    sys.exit(1)

API_URL = f"{WORKER_URL}/bot{BOT_TOKEN}"
TELEGRAM_FILE_LIMIT = 50 * 1024 * 1024
POLL_INTERVAL = 1.0
# --------------------------------------------------

def get_clipboard_text():
    """Retrieve the current Unicode text content from the system clipboard.

    This function checks whether Unicode text is available on the clipboard
    and returns it if present, otherwise it returns None.

    Returns:
        Optional[str]: The Unicode text from the clipboard if available,
            otherwise None.
    """
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
    except Exception:
        pass
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception as e:
            print(f"[Clipboard] Error encountered: {e}")
    return None

def get_clipboard_image_bytes():
    """Retrieve the current image content from the system clipboard as bytes.

    This function checks whether an image is available on the clipboard
    and returns it as a PNG-encoded byte string if present, otherwise it returns None.

    Returns:
        Optional[bytes]: The image data as PNG bytes if available, otherwise None.
    """
    try:
        img = ImageGrab.grabclipboard()
        if isinstance(img, Image.Image):
            with tempfile.SpooledTemporaryFile() as buf:
                img2 = img.convert("RGB") if img.mode in ("RGBA", "P") else img
                img2.save(buf, format="PNG")
                buf.seek(0)
                return buf.read()
    except Exception as e:
        print(f"[Clipboard] Error encountered: {e}")
    return None

def get_clipboard_file_list():
    """Retrieve the list of files currently in the system clipboard.

    This function checks whether file drop data is available on the clipboard
    and returns it as a list if present, otherwise it returns None.

    Returns:
        Optional[List[str]]: The list of file paths if available, otherwise None.
    """
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
            data = win32clipboard.GetClipboardData(win32clipboard.CF_HDROP)
            if isinstance(data, (list, tuple)) and data:
                return list(data)
    except Exception:
        pass
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception as e:
            print(f"[Clipboard] Error encountered: {e}")
    return None

def send_text(text: str):
    """Send a text message to the configured Telegram chat.

    This function sends the provided text to Telegram using the bot API and
    logs any exceptions that occur during the request.

    Args:
        text: The message text to send to the Telegram chat.
    """
    url = f"{API_URL}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=15)
    except Exception as e:
        print(f"[Telegram] Exception sending text: {e}")

def send_image_bytes(img_bytes: bytes):
    """Send an image to the configured Telegram chat from raw bytes.

    This function writes the given image bytes to a temporary PNG file,
    uploads it to Telegram as a photo, and then removes the temporary file.

    Args:
        img_bytes: The raw image data to send as a PNG.
    """
    url = f"{API_URL}/sendPhoto"
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(img_bytes)
        with open(tmp_path, "rb") as f:
            requests.post(url, data={"chat_id": CHAT_ID}, files={"photo": f}, timeout=30)
    except Exception as e:
        print(f"[Telegram] Exception sending image: {e}")
    finally:
        try:
            os.remove(tmp_path)
        except Exception as e:
            print(f"[Image] Error encountered: {e}")

def send_file_or_fallback(path: str):
    """Send a file via Telegram or fall back to an external file host.

    This function attempts to upload the file to Telegram if it is within
    the allowed size limit, and otherwise (or on specific errors) sends it
    using transfer.sh and shares the download link instead.

    Args:
        path: The filesystem path to the file that should be sent.
    """
    try:
        size = os.path.getsize(path)
    except Exception:
        return

    if size <= TELEGRAM_FILE_LIMIT:
        url = f"{API_URL}/sendDocument"
        try:
            with open(path, "rb") as f:
                resp = requests.post(url, data={"chat_id": CHAT_ID}, files={"document": f}, timeout=60)
                if resp.status_code == 400:
                    send_file_via_gofile(path)
        except Exception as e:
            print(f"[Telegram] Exception sending file: {e}")
    else:
        send_file_via_gofile(path)

def send_file_via_gofile(file_path: str):
    """Upload a file to gofile and share the download link via Telegram.

    This function sends the specified file to gofile and, if successful,
    posts a message to Telegram containing the generated download URL.

    Args:
        path: The filesystem path to the file that should be uploaded.
    """
    filename = os.path.basename(file_path)

    url = "https://upload.gofile.io/uploadfile"

    try:
        with open(file_path, "rb") as f:
            files = {"file": (filename, f)}
            response = requests.post(url, files=files)

        if response.status_code != 200:
            raise ConnectionError(f"HTTP upload failed with status code: {response.status_code}")
        result = response.json()
        if result.get("status") == "ok":
            send_text(f"File too large for Telegram; download from:\n{result['data']['downloadPage']}")
        else:
            raise ConnectionError(f"GoFile error: {result.get('status')}")
    except Exception as e:
        print(f"[GoFile] Error encountered: {e}")
        print(e.stacktrace())

def main():
    """Continuously monitor the clipboard and sync new content to Telegram.

    This function detects changes to copied text, images, or files and forwards
    them to Telegram while avoiding duplicate sends of recently seen content.

    """
    last_text, last_image_hash, last_files_list = None, None, None
    while True:
        try:
            if files := get_clipboard_file_list():
                sorted_paths = sorted(files)
                fingerprint = "|".join(sorted_paths)
                if fingerprint != last_files_list:
                    for path in sorted_paths:
                        send_file_or_fallback(path)
                    last_files_list, last_text, last_image_hash = fingerprint, None, None
            else:
                text = get_clipboard_text()
                if text and text.strip('\r\n '):
                    if text != last_text:
                        send_text(text)
                        last_text, last_image_hash, last_files_list = text, None, None
                elif img_bytes := get_clipboard_image_bytes():
                    h = hashlib.sha256(img_bytes).hexdigest()
                    if h != last_image_hash:
                        send_image_bytes(img_bytes)
                        last_image_hash, last_text, last_files_list = h, None, None
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception:
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()