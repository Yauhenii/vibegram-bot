# Audio to Voice Message Telegram Bot

This Telegram bot converts audio files to voice messages. It uses the python-telegram-bot library and ffmpeg for audio conversion.

## Prerequisites

- Python 3.7 or higher
- ffmpeg installed on your system
- A Telegram Bot Token (get it from [@BotFather](https://t.me/BotFather))

## Installation

1. Clone this repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install ffmpeg:
   - On macOS: `brew install ffmpeg`
   - On Ubuntu/Debian: `sudo apt-get install ffmpeg`
   - On Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## Configuration

1. Create a `.env` file in the project root
2. Add your Telegram Bot Token:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

## Usage

1. Run the bot:
   ```bash
   python bot.py
   ```
2. Start a chat with your bot on Telegram
3. Send any audio file to the bot
4. The bot will convert it to a voice message and send it back

## Features

- Converts various audio formats to Telegram voice messages
- Handles errors gracefully
- Uses temporary files for processing
- Automatic cleanup of temporary files

## Note

The bot uses the OGG format with the Opus codec, which is the format Telegram uses for voice messages. The audio is converted to a bitrate of 128k for optimal quality. 