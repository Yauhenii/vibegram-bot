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

## Deployment

### Option 1: Railway.app (Recommended for Free Tier)

1. Create an account on [Railway.app](https://railway.app/)
2. Install Railway CLI:
   ```bash
   npm i -g @railway/cli
   ```
3. Login to Railway:
   ```bash
   railway login
   ```
4. Initialize and deploy:
   ```bash
   railway init
   railway up
   ```
5. Set environment variables in Railway dashboard:
   - `TELEGRAM_BOT_TOKEN`: Your bot token

### Option 2: Heroku

1. Create an account on [Heroku](https://www.heroku.com/)
2. Install Heroku CLI:
   ```bash
   brew tap heroku/brew && brew install heroku
   ```
3. Login to Heroku:
   ```bash
   heroku login
   ```
4. Create a new app:
   ```bash
   heroku create your-app-name
   ```
5. Deploy:
   ```bash
   git push heroku main
   ```
6. Set environment variables:
   ```bash
   heroku config:set TELEGRAM_BOT_TOKEN=your_bot_token
   ```

### Option 3: PythonAnywhere

1. Create an account on [PythonAnywhere](https://www.pythonanywhere.com/)
2. Upload your code
3. Set up a web app or scheduled task
4. Configure environment variables in the web interface

## Building and Rebuilding the Application

### Initial Deployment

1. Create a Heroku app:
   ```bash
   heroku create your-app-name
   ```

2. Add the required buildpacks:
   ```bash
   heroku buildpacks:add heroku/python
   heroku buildpacks:add https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
   ```

3. Set the Python version by creating a `.python-version` file:
   ```
   3.12
   ```

4. Deploy to Heroku:
   ```bash
   git push heroku main
   ```

### Rebuilding the Application

1. Make your code changes

2. Commit the changes:
   ```bash
   git add .
   git commit -m "your commit message"
   ```

3. Push to Heroku:
   ```bash
   git push heroku main
   ```

4. If you need to force a rebuild without code changes:
   ```bash
   git commit --allow-empty -m "trigger rebuild"
   git push heroku main
   ```

5. To restart the worker process:
   ```bash
   heroku ps:restart worker
   ```

6. Check the logs:
   ```bash
   heroku logs --tail
   ```

### Troubleshooting

- If you encounter dependency issues, update `requirements.txt` and redeploy
- If the bot stops responding, check the logs and restart the worker
- If ffmpeg issues occur, verify the buildpack is properly installed

## License

MIT 