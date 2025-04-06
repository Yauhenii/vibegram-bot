import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import ffmpeg
import tempfile

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_FILENAME = 1
CHOOSING_FORMAT = 2
CHOOSING_QUALITY = 3

# Quality presets
QUALITY_PRESETS = {
    'low': {
        'mp3': '96k',
        'wav': '16k',
        'ogg': '64k'
    },
    'medium': {
        'mp3': '192k',
        'wav': '32k',
        'ogg': '128k'
    },
    'high': {
        'mp3': '320k',
        'wav': '48k',
        'ogg': '256k'
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        'Hi! I am an audio converter bot.\n'
        '• Send me any audio file and I will convert it to your preferred format\n'
        '• Send me a voice message and I will convert it to your preferred format\n'
        '• Use /help to see available formats and quality settings'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/cancel - Cancel current operation\n\n"
        "Supported formats:\n"
        "• MP3 - Most compatible format\n"
        "• WAV - High quality, uncompressed\n"
        "• OGG - Good quality, smaller size\n\n"
        "Quality settings:\n"
        "• Low - Smaller file size\n"
        "• Medium - Balanced quality and size\n"
        "• High - Best quality, larger file size"
    )
    await update.message.reply_text(help_text)

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming audio file and ask for format."""
    context.user_data['file_id'] = update.message.audio.file_id
    context.user_data['file_type'] = 'audio'
    await show_format_buttons(update, context)
    return CHOOSING_FORMAT

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming voice message and ask for format."""
    context.user_data['file_id'] = update.message.voice.file_id
    context.user_data['file_type'] = 'voice'
    await show_format_buttons(update, context)
    return CHOOSING_FORMAT

async def show_format_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show format selection buttons."""
    keyboard = [
        [
            InlineKeyboardButton("MP3", callback_data='format_mp3'),
            InlineKeyboardButton("WAV", callback_data='format_wav'),
            InlineKeyboardButton("OGG", callback_data='format_ogg')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please choose the output format:', reply_markup=reply_markup)

async def show_quality_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show quality selection buttons."""
    keyboard = [
        [
            InlineKeyboardButton("Low", callback_data='quality_low'),
            InlineKeyboardButton("Medium", callback_data='quality_medium'),
            InlineKeyboardButton("High", callback_data='quality_high')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text('Please choose the quality:', reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith('format_'):
        context.user_data['format'] = query.data.split('_')[1]
        await show_quality_buttons(update, context)
        return CHOOSING_QUALITY
    elif query.data.startswith('quality_'):
        context.user_data['quality'] = query.data.split('_')[1]
        await query.message.reply_text("Please send me the desired filename (without extension):")
        return WAITING_FOR_FILENAME

async def handle_filename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the filename and perform the conversion."""
    filename = update.message.text.strip()
    if not filename:
        await update.message.reply_text("Please provide a valid filename.")
        return WAITING_FOR_FILENAME

    try:
        file_id = context.user_data.get('file_id')
        file_type = context.user_data.get('file_type')
        output_format = context.user_data.get('format', 'mp3')
        quality = context.user_data.get('quality', 'medium')
        
        if not file_id or not file_type:
            await update.message.reply_text("Something went wrong. Please try sending the file again.")
            return ConversationHandler.END

        # Get the file
        file = await context.bot.get_file(file_id)
        
        # Get bitrate based on format and quality
        bitrate = QUALITY_PRESETS[quality][output_format]
        
        if file_type == 'audio':
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as input_file, \
                 tempfile.NamedTemporaryFile(suffix=f'.{output_format}', delete=False) as output_file:
                
                # Download the file
                await file.download_to_drive(input_file.name)
                
                # Convert the file using ffmpeg
                stream = ffmpeg.input(input_file.name)
                if output_format == 'mp3':
                    stream = ffmpeg.output(stream, output_file.name, acodec='libmp3lame', audio_bitrate=bitrate)
                elif output_format == 'wav':
                    stream = ffmpeg.output(stream, output_file.name, acodec='pcm_s16le', audio_bitrate=bitrate)
                else:  # ogg
                    stream = ffmpeg.output(stream, output_file.name, acodec='libopus', audio_bitrate=bitrate)
                
                ffmpeg.run(stream, overwrite_output=True, quiet=True)
                
                # Send the converted file
                with open(output_file.name, 'rb') as audio:
                    await update.message.reply_audio(
                        audio=audio,
                        title=filename,
                        performer="Audio Bot"
                    )
                
                # Clean up
                os.unlink(input_file.name)
                os.unlink(output_file.name)
                
        else:  # voice message
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as input_file, \
                 tempfile.NamedTemporaryFile(suffix=f'.{output_format}', delete=False) as output_file:
                
                # Download the file
                await file.download_to_drive(input_file.name)
                
                # Convert the file using ffmpeg
                stream = ffmpeg.input(input_file.name)
                if output_format == 'mp3':
                    stream = ffmpeg.output(stream, output_file.name, acodec='libmp3lame', audio_bitrate=bitrate)
                elif output_format == 'wav':
                    stream = ffmpeg.output(stream, output_file.name, acodec='pcm_s16le', audio_bitrate=bitrate)
                else:  # ogg
                    stream = ffmpeg.output(stream, output_file.name, acodec='libopus', audio_bitrate=bitrate)
                
                ffmpeg.run(stream, overwrite_output=True, quiet=True)
                
                # Send the converted file
                with open(output_file.name, 'rb') as audio:
                    await update.message.reply_audio(
                        audio=audio,
                        title=filename,
                        performer="Voice Bot"
                    )
                
                # Clean up
                os.unlink(input_file.name)
                os.unlink(output_file.name)
        
        # Clear user data
        context.user_data.clear()
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        await update.message.reply_text("Sorry, I couldn't process the file. Please try again.")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation."""
    context.user_data.clear()
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

def main():
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.AUDIO, handle_audio),
            MessageHandler(filters.VOICE, handle_voice)
        ],
        states={
            CHOOSING_FORMAT: [CallbackQueryHandler(button_handler)],
            CHOOSING_QUALITY: [CallbackQueryHandler(button_handler)],
            WAITING_FOR_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_filename)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(conv_handler)

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 
    