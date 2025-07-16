import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from youtubesearchpython import VideosSearch
import yt_dlp

# Bot token from BotFather
TOKEN = "7768342919:AAGbEvC2kUzKG4DJ-fPc70yR94u158rAQ84"
DOWNLOAD_DIR = "downloads"

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Function to handle the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name
    await update.message.reply_html(
        f"Hi {user_name}!\n\nWelcome to Ringtone Pro Bot.\n"
        "Just send me the name of the ringtone you want."
    )

# Function to handle all text messages (ringtone search)
async def search_ringtone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.message.text
    chat_id = update.message.chat_id
    
    # Inform the user that the search has started
    processing_message = await update.message.reply_text(f"Searching for '{query}'...")

    try:
        # Search for videos on YouTube
        search_query = f"{query} ringtone"
        videos_search = VideosSearch(search_query, limit=3)
        results = videos_search.result()["result"]

        if not results:
            await processing_message.edit_text("Sorry, I couldn't find any ringtones for that name.")
            return

        # Create download directory if it doesn't exist
        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)
        
        await processing_message.edit_text(f"Found ringtones! Downloading and sending now...")

        # Download and send the top 3 results
        for i, video in enumerate(results):
            video_url = video["link"]
            video_title = video["title"]
            file_path = os.path.join(DOWNLOAD_DIR, f"ringtone_{chat_id}_{i}")

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'{file_path}.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'external_downloader': 'aria2c',
                'external_downloader_args': ['-x', '16', '-s', '16', '-k', '1M'],
                'quiet': True,
                'no_warnings': True,
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])
                
                audio_file = f"{file_path}.mp3"
                
                if os.path.exists(audio_file):
                    await context.bot.send_audio(
                        chat_id=chat_id,
                        audio=open(audio_file, 'rb'),
                        title=video_title,
                        filename=f"{video_title}.mp3"
                    )
                    os.remove(audio_file) # Clean up the file
                else:
                    logger.warning(f"Downloaded file not found: {audio_file}")

            except Exception as e:
                logger.error(f"Error downloading {video_url}: {e}")
                await context.bot.send_message(chat_id, f"Failed to download a ringtone: {video_title}")
                # Clean up if a partial file was created
                if os.path.exists(f"{file_path}.mp3"):
                    os.remove(f"{file_path}.mp3")

    except Exception as e:
        logger.error(f"An error occurred during search: {e}")
        await processing_message.edit_text("An unexpected error occurred. Please try again later.")

def main() -> None:
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_ringtone))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
