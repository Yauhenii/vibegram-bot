import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import ffmpeg
import tempfile
from datetime import datetime

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
CHOOSING_CONVERSION_TYPE = 1
CHOOSING_FORMAT = 2
CHOOSING_QUALITY = 3
WAITING_FOR_FILENAME = 4

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

def generate_default_filename(file_type):
    """Generate a default filename based on current timestamp and file type."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{file_type}_{timestamp}"

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

async def show_conversion_type_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show conversion type selection buttons."""
    keyboard = [
        [
            InlineKeyboardButton("Convert to Audio", callback_data='type_audio'),
            InlineKeyboardButton("Convert to Voice", callback_data='type_voice')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.message.reply_text('What would you like to convert this to?', reply_markup=reply_markup)
    else:
        await update.message.reply_text('What would you like to convert this to?', reply_markup=reply_markup)

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle audio files and forwarded messages."""
    try:
        audio = update.message.audio
        if not audio:
            await update.message.reply_text("Please send an audio file.")
            return ConversationHandler.END
            
        # Download the file
        file = await context.bot.get_file(audio.file_id)
        file_path = f"temp_{audio.file_id}.{audio.file_name.split('.')[-1]}"
        await file.download_to_drive(file_path)
        
        # Store file path and show conversion type options
        context.user_data['file_path'] = file_path
        context.user_data['original_type'] = 'audio'
        await show_conversion_type_buttons(update, context)
        return CHOOSING_CONVERSION_TYPE
            
    except Exception as e:
        await update.message.reply_text(f"Error processing audio: {str(e)}")
        return ConversationHandler.END

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle voice messages."""
    try:
        voice = update.message.voice
        if not voice:
            await update.message.reply_text("Please send a voice message.")
            return ConversationHandler.END
            
        # Download the file
        file = await context.bot.get_file(voice.file_id)
        file_path = f"temp_{voice.file_id}.ogg"  # Voice messages are in OGG format
        await file.download_to_drive(file_path)
        
        # Store file path and show conversion type options
        context.user_data['file_path'] = file_path
        context.user_data['original_type'] = 'voice'
        await show_conversion_type_buttons(update, context)
        return CHOOSING_CONVERSION_TYPE
            
    except Exception as e:
        await update.message.reply_text(f"Error processing voice message: {str(e)}")
        return ConversationHandler.END

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
    if update.callback_query:
        await update.callback_query.message.reply_text('Please choose the format:', reply_markup=reply_markup)
    else:
        await update.message.reply_text('Please choose the format:', reply_markup=reply_markup)

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
    if update.callback_query:
        await update.callback_query.message.reply_text('Please choose the quality:', reply_markup=reply_markup)
    else:
        await update.message.reply_text('Please choose the quality:', reply_markup=reply_markup)

async def show_filename_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show filename options."""
    default_filename = context.user_data.get('default_filename', '')
    keyboard = [
        [
            InlineKeyboardButton("Use Default", callback_data='filename_default'),
            InlineKeyboardButton("Custom Name", callback_data='filename_custom')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        f'Default filename: {default_filename}\nWould you like to use this name or provide a custom one?',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle button presses."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('type_'):
        conversion_type = query.data.split('_')[1]
        context.user_data['conversion_type'] = conversion_type
        await show_format_buttons(update, context)
        return CHOOSING_FORMAT
    elif query.data.startswith('format_'):
        context.user_data['format'] = query.data.split('_')[1]
        await show_quality_buttons(update, context)
        return CHOOSING_QUALITY
    elif query.data.startswith('quality_'):
        context.user_data['quality'] = query.data.split('_')[1]
        await query.message.reply_text("Please send me the desired filename (without extension):")
        return WAITING_FOR_FILENAME
    elif query.data.startswith('filename_'):
        choice = query.data.split('_')[1]
        if choice == 'default':
            context.user_data['filename'] = generate_default_filename(context.user_data.get('original_type', 'audio'))
            await process_conversion(update, context)
            return ConversationHandler.END
        elif choice == 'custom':
            await query.message.reply_text("Please send me the desired filename (without extension):")
            return WAITING_FOR_FILENAME
        elif choice == 'cancel':
            await query.message.reply_text("Operation cancelled.")
            return ConversationHandler.END
            
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
            await update.message.reply_text("Something went wrong. Please try sending the file again.")
            return ConversationHandler.END

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
            stream = ffmpeg.output(stream, output_path,
                                 audio_bitrate=quality_settings,
                                 acodec='libvorbis')
            
        ffmpeg.run(stream, overwrite_output=True)
        logger.info("ffmpeg conversion completed")
        
        # Send the converted file
        logger.info(f"Sending converted file as {conversion_type}")
        with open(output_path, 'rb') as audio_file:
            if conversion_type == 'voice':
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
        logger.info("Cleaning up temporary files")
        os.remove(file_path)
        os.remove(output_path)
        
        # Clear user data
        context.user_data.clear()
        logger.info("Conversion process completed successfully")
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error during conversion: {str(e)}", exc_info=True)
        await update.message.reply_text(f"Error during conversion: {str(e)}")
        # Clean up any remaining files
        if 'file_path' in context.user_data:
            try:
                os.remove(context.user_data['file_path'])
            except:
                pass
        context.user_data.clear()
        return ConversationHandler.END

async def handle_filename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the filename input."""
    filename = update.message.text.strip()
    if not filename:
        await update.message.reply_text("Please provide a valid filename.")
        return WAITING_FOR_FILENAME
        
    context.user_data['filename'] = filename
    await process_conversion(update, context)
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
            CHOOSING_CONVERSION_TYPE: [CallbackQueryHandler(button_handler)],
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
    