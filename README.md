# Vibegram Bot

A Telegram bot that converts audio files and voice messages to MP3 format.

## Features

- Converts audio files to MP3
- Converts voice messages to MP3
- Supports custom filenames
- Easy to use interface

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your Telegram bot token:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```
4. Run the bot:
   ```bash
   python bot.py
   ```

## Deployment

### Initial Setup

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

### Updating the App

1. Make your code changes

2. Commit and push to Heroku:
   ```bash
   git add .
   git commit -m "your commit message"
   git push heroku main
   ```

3. To force a rebuild without code changes:
   ```bash
   git commit --allow-empty -m "trigger rebuild"
   git push heroku main
   ```

4. To restart the worker:
   ```bash
   heroku ps:restart worker
   ```

5. Check the logs:
   ```bash
   heroku logs --tail
   ```

### Troubleshooting

- If you encounter dependency issues, update `requirements.txt` and redeploy
- If the bot stops responding, check the logs and restart the worker
- If ffmpeg issues occur, verify the buildpack is properly installed 