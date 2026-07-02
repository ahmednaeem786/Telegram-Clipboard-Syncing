# Telegram Clipboard Syncing

A lightweight Python application that monitors your system clipboard and automatically sends new content (text, images, and files) to a Telegram chat. Perfect for quick file sharing, cross-device communication, and clipboard synchronization.

## Features

- **Real-time Clipboard Monitoring**: Continuously monitors system clipboard for changes
- **Multi-format Support**: 
  - Text messages
  - Images (automatically converted to PNG)
  - Files and drag-and-drop file lists
- **Smart Deduplication**: Prevents sending duplicate content using SHA-256 hashing
- **File Size Handling**: 
  - Files up to 50MB sent directly to Telegram
  - Larger files uploaded to gofile.io with shareable link
- **Reliable Message Delivery**: Uses Telegram Bot API via Cloudflare Workers for enhanced reliability
- **Error Handling**: Graceful error handling with informative logging
- **Windows Clipboard Integration**: Full support for Windows clipboard formats

## Requirements

- **Python 3.7+**
- **Windows OS** (uses Windows clipboard API)
- **Telegram Bot** (configured with a bot token)
- **Cloudflare Worker** (or direct Telegram API access)
- **Internet Connection**

## Dependencies

The application requires the following Python packages:

- `pywin32` - Windows clipboard access
- `Pillow (PIL)` - Image processing and clipboard capture
- `python-dotenv` - Environment variable management
- `requests` - HTTP requests to Telegram and file hosting

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/Telegram-Clipboard-Syncing.git
cd Telegram-Clipboard-Syncing
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install pywin32 Pillow python-dotenv requests
```

## Configuration

### 1. Set up Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Create a new bot with `/newbot` command
3. Copy the **Bot Token** provided by BotFather
4. Get your **Chat ID**:
   - Send a message to your bot
   - Visit `https://api.telegram.org/bot{YOUR_BOT_TOKEN}/getUpdates`
   - Find your Chat ID in the response

### 2. Set up Cloudflare Worker (Optional)

If using a Cloudflare Worker for API relay:
- Deploy a worker that forwards requests to Telegram API
- Get the worker URL

### 3. Create `.env` File

Create a `.env` file in the project root directory:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
CLOUDFARE_WORKER_URL=https://your-worker.your-domain.workers.dev
```

**Example:**
```env
TELEGRAM_BOT_TOKEN=123456789:ABCDefGHIjklmnoPQRstuvwxyzABCDefGH
TELEGRAM_CHAT_ID=987654321
CLOUDFARE_WORKER_URL=https://clipboard-sync.example.workers.dev
```

> **Note**: Never commit the `.env` file to version control. Add it to `.gitignore`.

## Usage

### Run the Application

```bash
python telegram_clipboard_push.py
```

Or with the virtual environment:

```bash
.venv\Scripts\python.exe telegram_clipboard_push.py
```

### Behavior

1. **Text Clipboard**: Any text you copy will be sent to Telegram within 1 second
2. **Images**: Screenshots or images copied to clipboard are sent as PNG files
3. **Files**: Files dragged to clipboard or from file explorers are automatically sent
4. **Large Files**: Files larger than 50MB are uploaded to gofile.io and a download link is sent

### Stop the Application

Press `Ctrl+C` in the terminal to stop the clipboard monitoring.

### Run in Background (No Console Window)

To run the script silently in the background without displaying a console window:

1. **Rename the file**: Change the file extension from `.py` to `.pyw`
   - Right-click `telegram_clipboard_push.py` → Rename
   - Change to `telegram_clipboard_push.pyw`

2. **Double-click to run**: Simply double-click the `.pyw` file to start the clipboard monitoring
   - The script will run in the background without showing a console window
   - Your clipboard syncing will continue running silently

3. **Stop the application**: 
   - Open Task Manager (`Ctrl+Shift+Esc`)
   - Find `python.exe` in the processes list
   - Select it and click "End Task"

> **Tip**: You can create a shortcut to the `.pyw` file and place it in your Windows Startup folder (`C:\Users\YourUsername\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`) to automatically run the script when your computer starts.

## How It Works

```
System Clipboard → Polling (1s intervals)
                      ↓
              ┌───────┴────────┐
              ↓                ↓
          Files?          Text/Image?
              ↓                ↓
         Send File(s)    Check Hash
              ↓          /        ↓
         Size Check?   Cache    New?
         /         \    Hit       ↓
    ≤50MB        >50MB   ↓      Send to Telegram
      ↓             ↓     (skip)
   Telegram    GoFile + Link
      ↓
   Message Sent
```

### Key Features:

- **Polling Interval**: 1 second (configurable in code)
- **Deduplication**: Uses SHA-256 hash for images and file fingerprinting for files
- **File Format Support**: All file types supported (limited only by Telegram/GoFile)
- **Image Conversion**: Automatically converts RGBA and palette images to RGB PNG

## Error Handling

The application gracefully handles various error scenarios:

- **Missing Dependencies**: Displays helpful error messages with installation commands
- **Missing Credentials**: Validates environment variables at startup
- **Network Errors**: Logs exceptions and continues monitoring
- **File Errors**: Catches read/write errors and continues operation
- **Clipboard Errors**: Safely handles clipboard access exceptions

## Troubleshooting

### "Error: pywin32 is required"
```bash
pip install pywin32
```

### "Error: Pillow is required"
```bash
pip install Pillow
```

### "Error: Missing credentials"
- Verify your `.env` file exists in the project root
- Check that all three variables are set: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `CLOUDFARE_WORKER_URL`
- Ensure no typos in variable names

### Files Not Being Sent
- Check internet connection
- Verify Telegram bot token is valid
- Test bot with: `https://api.telegram.org/bot{YOUR_BOT_TOKEN}/getMe`
- Ensure Chat ID is correct and the bot has access to the chat

### Images Not Detected
- Only images on clipboard are detected (not files named *.jpg)
- Use screenshot tools or copy-paste from image editors
- Supported formats: JPEG, PNG, BMP, GIF, RGBA

## Configuration Customization

Edit these values in `telegram_clipboard_push.py` to customize behavior:

```python
TELEGRAM_FILE_LIMIT = 50 * 1024 * 1024  # File size limit for Telegram (50MB)
POLL_INTERVAL = 1.0                      # Polling interval in seconds
```

## API References

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [GoFile API Documentation](https://gofile.io/api)
- [Cloudflare Workers Documentation](https://developers.cloudflare.com/workers/)

## Security Considerations

- **Keep `.env` Private**: Never share or commit your `.env` file
- **Bot Token**: Treat your bot token like a password
- **File Sharing**: Be cautious about what files are in your clipboard
- **GoFile**: Large files are uploaded to a third-party service; ensure you're comfortable with their privacy policy

## Performance

- **Memory Usage**: Minimal (~20-50MB)
- **CPU Usage**: <1% at idle (polling at 1s intervals)
- **Network**: Only sends when clipboard changes