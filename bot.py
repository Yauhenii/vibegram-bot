import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        'Hi! I am an audio converter bot.\n'
        '• Send me any audio file and I will convert it to a voice message\n'
        '• Send me a voice message and I will convert it to an audio file'
    )

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming audio file and ask for filename."""
    context.user_data['file_id'] = update.message.audio.file_id
    context.user_data['file_type'] = 'audio'
    await update.message.reply_text("Please send me the desired filename (without extension):")
    return WAITING_FOR_FILENAME

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming voice message and ask for filename."""
    context.user_data['file_id'] = update.message.voice.file_id
    context.user_data['file_type'] = 'voice'
    await update.message.reply_text("Please send me the desired filename (without extension):")
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
        
        if not file_id or not file_type:
            await update.message.reply_text("Something went wrong. Please try sending the file again.")
            return ConversationHandler.END

        # Get the file
        file = await context.bot.get_file(file_id)
        
        if file_type == 'audio':
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as input_file, \
                 tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as output_file:
                
                # Download the file
                await file.download_to_drive(input_file.name)
                
                # Convert the file using ffmpeg
                stream = ffmpeg.input(input_file.name)
                stream = ffmpeg.output(stream, output_file.name, acodec='libopus', audio_bitrate='128k')
                ffmpeg.run(stream, overwrite_output=True, quiet=True)
                
                # Send the converted file as a voice message
                with open(output_file.name, 'rb') as voice:
                    await update.message.reply_voice(voice=voice)
                
                # Clean up
                os.unlink(input_file.name)
                os.unlink(output_file.name)
                
        else:  # voice message
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as input_file, \
                 tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as output_file:
                
                # Download the file
                await file.download_to_drive(input_file.name)
                
                # Convert the file using ffmpeg
                stream = ffmpeg.input(input_file.name)
                stream = ffmpeg.output(stream, output_file.name, acodec='libmp3lame', audio_bitrate='192k')
                ffmpeg.run(stream, overwrite_output=True, quiet=True)
                
                # Send the converted file as an audio file
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
            WAITING_FOR_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_filename)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 
    