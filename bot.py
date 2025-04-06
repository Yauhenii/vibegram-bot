import os
import logging
import asyncio
import ffmpeg
import tempfile
import shutil
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, filters
from pytube import YouTube
import urllib3

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
SELECTING_FORMAT, SELECTING_QUALITY, SELECTING_CONVERSION_TYPE, ENTERING_FILENAME = range(4)

# Define quality presets
QUALITY_PRESETS = {
    'low': {
        'mp3': '128k',
        'wav': '44100',
        'ogg': '96k'
    },
    'medium': {
        'mp3': '192k',
        'wav': '48000',
        'ogg': '128k'
    },
    'high': {
        'mp3': '320k',
        'wav': '96000',
        'ogg': '192k'
    }
}

# Queue system
class ConversionQueue:
    def __init__(self):
        self.queue = []
        self.progress = {}
        self.lock = asyncio.Lock()
    
    async def add_to_queue(self, user_id, file_path, conversion_type, format, quality, filename):
        async with self.lock:
            self.queue.append({
                'user_id': user_id,
                'file_path': file_path,
                'conversion_type': conversion_type,
                'format': format,
                'quality': quality,
                'filename': filename,
                'status': 'waiting',
                'progress': 0
            })
            return len(self.queue)
    
    async def update_progress(self, user_id, progress):
        async with self.lock:
            for item in self.queue:
                if item['user_id'] == user_id:
                    item['progress'] = progress
                    break
    
    async def get_queue_position(self, user_id):
        async with self.lock:
            for i, item in enumerate(self.queue):
                if item['user_id'] == user_id:
                    return i + 1
            return None
    
    async def remove_from_queue(self, user_id):
        async with self.lock:
            self.queue = [item for item in self.queue if item['user_id'] != user_id]

# Initialize queue
conversion_queue = ConversionQueue()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        'Hi! I can convert audio files to different formats. '
        'Send me an audio file or a YouTube link to get started!'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = """
Available commands:
/start - Start the bot
/help - Show this help message
/queue - Show your position in the conversion queue
/cancel - Cancel your current conversion

Supported formats:
- MP3
- WAV
- OGG (including voice messages)

Quality presets:
- Low (smaller file size)
- Medium (balanced)
- High (best quality)
    """
    await update.message.reply_text(help_text)

async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the user's position in the conversion queue."""
    user_id = update.effective_user.id
    position = await conversion_queue.get_queue_position(user_id)
    
    if position is None:
        await update.message.reply_text("You don't have any files in the conversion queue.")
    else:
        await update.message.reply_text(f"Your file is in position {position} in the queue.")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the user's current conversion."""
    user_id = update.effective_user.id
    await conversion_queue.remove_from_queue(user_id)
    await update.message.reply_text("Your conversion has been cancelled.")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle audio files."""
    try:
        # Get the file
        audio_file = update.message.audio or update.message.voice
        if not audio_file:
            await update.message.reply_text("Please send an audio file.")
            return ConversationHandler.END

        # Download the file
        file = await context.bot.get_file(audio_file.file_id)
        file_path = f"temp_{audio_file.file_id}.{audio_file.file_name.split('.')[-1] if hasattr(audio_file, 'file_name') else 'ogg'}"
        await file.download_to_drive(file_path)

        # Store file path and original voice message if it's a voice message
        context.user_data['file_path'] = file_path
        if update.message.voice:
            context.user_data['original_voice'] = audio_file

        # Show conversion type buttons
        await show_conversion_type_buttons(update, context)
        return SELECTING_CONVERSION_TYPE

    except Exception as e:
        logger.error(f"Error handling audio: {str(e)}", exc_info=True)
        await update.message.reply_text("Sorry, something went wrong. Please try again.")
        return ConversationHandler.END

async def handle_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube links."""
    try:
        url = update.message.text
        yt = YouTube(url)
        audio_stream = yt.streams.filter(only_audio=True).first()
        
        if not audio_stream:
            await update.message.reply_text("No audio stream found in the video.")
            return ConversationHandler.END

        # Download the audio
        file_path = f"temp_{yt.video_id}.{audio_stream.subtype}"
        audio_stream.download(filename=file_path)

        # Store file path
        context.user_data['file_path'] = file_path

        # Show conversion type buttons
        await show_conversion_type_buttons(update, context)
        return SELECTING_CONVERSION_TYPE

    except Exception as e:
        logger.error(f"Error handling YouTube link: {str(e)}", exc_info=True)
        await update.message.reply_text("Sorry, something went wrong. Please try again.")
        return ConversationHandler.END

async def show_conversion_type_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show buttons for selecting conversion type."""
    keyboard = [
        [
            InlineKeyboardButton("Convert to Audio", callback_data='audio'),
            InlineKeyboardButton("Convert to Voice", callback_data='voice')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = update.message if update.message else update.callback_query.message
    await message.reply_text("How would you like to convert the file?", reply_markup=reply_markup)

async def show_format_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show buttons for selecting format."""
    keyboard = [
        [
            InlineKeyboardButton("MP3", callback_data='mp3'),
            InlineKeyboardButton("WAV", callback_data='wav'),
            InlineKeyboardButton("OGG", callback_data='ogg')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = update.message if update.message else update.callback_query.message
    await message.reply_text("Select the output format:", reply_markup=reply_markup)

async def show_quality_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show buttons for selecting quality."""
    keyboard = [
        [
            InlineKeyboardButton("Low", callback_data='low'),
            InlineKeyboardButton("Medium", callback_data='medium'),
            InlineKeyboardButton("High", callback_data='high')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = update.message if update.message else update.callback_query.message
    await message.reply_text("Select the quality:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses."""
    query = update.callback_query
    await query.answer()
    
    if query.data in ['audio', 'voice']:
        context.user_data['conversion_type'] = query.data
        if query.data == 'voice':
            # For voice messages, skip format selection and use OGG
            context.user_data['format'] = 'ogg'
            await show_quality_buttons(update, context)
            return SELECTING_QUALITY
        else:
            await show_format_buttons(update, context)
            return SELECTING_FORMAT
    
    elif query.data in ['mp3', 'wav', 'ogg']:
        context.user_data['format'] = query.data
        await show_quality_buttons(update, context)
        return SELECTING_QUALITY
    
    elif query.data in ['low', 'medium', 'high']:
        context.user_data['quality'] = query.data
        message = query.message if query.message else update.message
        await message.reply_text("Please enter a filename (without extension) or press /skip to use the default name:")
        return ENTERING_FILENAME

async def handle_filename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle filename input."""
    context.user_data['filename'] = update.message.text
    await process_conversion(update, context)
    return ConversationHandler.END

async def skip_filename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip filename input and use default."""
    context.user_data['filename'] = ''
    await process_conversion(update, context)
    return ConversationHandler.END

async def process_conversion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the conversion with the selected options."""
    try:
        logger.info("Starting conversion process")
        file_path = context.user_data.get('file_path')
        conversion_type = context.user_data.get('conversion_type')
        output_format = context.user_data.get('format', 'mp3')
        quality = context.user_data.get('quality', 'medium')
        filename = context.user_data.get('filename', '')
        
        logger.info(f"Conversion parameters: type={conversion_type}, format={output_format}, quality={quality}, filename={filename}")
        
        if not file_path:
            logger.error("No file path found in user data")
            message = update.message if update.message else update.callback_query.message
            await message.reply_text("Something went wrong. Please try sending the file again.")
            return ConversationHandler.END

        # Add to queue and get position
        queue_position = await conversion_queue.add_to_queue(
            update.effective_user.id,
            file_path,
            conversion_type,
            output_format,
            quality,
            filename
        )
        
        # Send initial queue message
        message = update.message if update.message else update.callback_query.message
        queue_message = await message.reply_text(f"Your file has been added to the queue. Position: {queue_position}")
        
        # Wait for turn in queue
        while queue_position > 1:
            queue_position = await conversion_queue.get_queue_position(update.effective_user.id)
            if queue_position is None:  # User cancelled
                return ConversationHandler.END
            await asyncio.sleep(1)
        
        # Update status to processing
        await queue_message.edit_text("Processing your file... 0%")
        
        # Get quality settings
        quality_settings = QUALITY_PRESETS[quality][output_format]
        logger.info(f"Using quality settings: {quality_settings}")
        
        # Set output file path
        output_path = f"{filename}.{output_format}"
        logger.info(f"Output path: {output_path}")
        
        # Convert the file
        logger.info("Starting ffmpeg conversion")
        if output_format == 'mp3':
            stream = ffmpeg.input(file_path)
            stream = ffmpeg.output(stream, output_path, 
                                 audio_bitrate=quality_settings,
                                 acodec='libmp3lame')
        elif output_format == 'wav':
            stream = ffmpeg.input(file_path)
            stream = ffmpeg.output(stream, output_path,
                                 acodec='pcm_s16le',
                                 ar=quality_settings)
        elif output_format == 'ogg':
            stream = ffmpeg.input(file_path)
            if conversion_type == 'voice':
                stream = ffmpeg.output(stream, output_path,
                                     acodec='libopus',
                                     audio_bitrate='64k',
                                     ar='48000',
                                     ac=1,
                                     application='voip')
            else:
                stream = ffmpeg.output(stream, output_path,
                                     audio_bitrate=quality_settings,
                                     acodec='libvorbis')
        
        # Run conversion with progress tracking
        process = (
            ffmpeg
            .input(file_path)
            .output(output_path, **stream.get_args()[1])
            .overwrite_output()
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )
        
        # Monitor progress
        total_duration = None
        while True:
            line = process.stderr.readline().decode('utf-8')
            if not line:
                break
                
            # Extract duration and time
            if 'Duration:' in line:
                duration_str = line.split('Duration:')[1].split(',')[0].strip()
                h, m, s = map(float, duration_str.split(':'))
                total_duration = h * 3600 + m * 60 + s
            elif 'time=' in line:
                time_str = line.split('time=')[1].split(' ')[0]
                h, m, s = map(float, time_str.split(':'))
                current_time = h * 3600 + m * 60 + s
                if total_duration:
                    progress = int((current_time / total_duration) * 100)
                    await conversion_queue.update_progress(update.effective_user.id, progress)
                    await queue_message.edit_text(f"Processing your file... {progress}%")
        
        process.wait()
        logger.info("ffmpeg conversion completed")
        
        # Send the converted file
        logger.info(f"Sending converted file as {conversion_type}")
        with open(output_path, 'rb') as audio_file:
            if conversion_type == 'voice':
                if 'original_voice' in context.user_data:
                    original_voice = context.user_data['original_voice']
                    await context.bot.send_voice(
                        chat_id=update.effective_chat.id,
                        voice=audio_file,
                        duration=original_voice.duration
                    )
                else:
                    await context.bot.send_voice(
                        chat_id=update.effective_chat.id,
                        voice=audio_file
                    )
            else:
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=audio_file,
                    title=f"{filename}.{output_format}"
                )
        
        # Clean up
        os.remove(file_path)
        os.remove(output_path)
        await conversion_queue.remove_from_queue(update.effective_user.id)
        
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in conversion process: {str(e)}", exc_info=True)
        message = update.message if update.message else update.callback_query.message
        await message.reply_text("Sorry, something went wrong during the conversion. Please try again.")
        await conversion_queue.remove_from_queue(update.effective_user.id)
        return ConversationHandler.END

def main():
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.AUDIO | filters.VOICE, handle_audio),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_youtube)
        ],
        states={
            SELECTING_CONVERSION_TYPE: [CallbackQueryHandler(button_handler)],
            SELECTING_FORMAT: [CallbackQueryHandler(button_handler)],
            SELECTING_QUALITY: [CallbackQueryHandler(button_handler)],
            ENTERING_FILENAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_filename),
                CommandHandler('skip', skip_filename)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_command)]
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("queue", queue_command))
    application.add_handler(conv_handler)

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 
    