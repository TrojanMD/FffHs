import os
import logging
import psutil
import platform
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
BOT_NAME = "Gemini BOT"
RESTRICTED_WORDS = ["spam", "scam", "hate"]  # Add your restricted words here

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with system info"""
    user = update.effective_user
    system_info = await get_system_info()
    
    welcome_msg = f"""
    🤖 *Welcome to {BOT_NAME}* 🤖
    *Powered by Google Gemini AI*

    🖥 *System Status*
    {system_info}

    🔍 *Features:*
    - Smart AI conversations
    - System monitoring
    - Restricted word filtering
    - Multi-language support

    Type /help for commands
    """
    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def get_system_info():
    """Get current system statistics"""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return f"""
    • CPU: {platform.processor()}
    • RAM: {mem.used/1024/1024:.1f}MB/{mem.total/1024/1024:.1f}MB ({mem.percent}%)
    • Storage: {disk.used/1024/1024:.1f}MB/{disk.total/1024/1024:.1f}MB
    • Uptime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    • Host: AWS EC2 (Linux)
    """

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show real-time system stats"""
    stats_msg = f"""
    📊 *Real-time System Stats*
    {await get_system_info()}
    """
    await update.message.reply_text(stats_msg, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process all messages with restricted word check"""
    if update.message.chat.type in ["group", "supergroup"]:
        await check_restricted_words(update, context)
    
    # Normal message processing
    user_message = update.message.text
    response = await generate_gemini_response(user_message)
    await update.message.reply_text(response, parse_mode='Markdown')

async def check_restricted_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check for restricted words and ban users"""
    message_text = update.message.text.lower()
    user = update.message.from_user
    
    for word in RESTRICTED_WORDS:
        if word in message_text:
            try:
                # Ban user from channel
                await context.bot.ban_chat_member(
                    chat_id=update.message.chat.id,
                    user_id=user.id
                )
                # Notify group
                await update.message.reply_text(
                    f"🚨 User @{user.username} was removed for using restricted word: '{word}'",
                    parse_mode='Markdown'
                )
                logger.warning(f"Banned user {user.id} for word: {word}")
                break
            except Exception as e:
                logger.error(f"Ban failed: {str(e)}")

async def generate_gemini_response(prompt: str):
    """Generate AI response using Gemini"""
    try:
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini error: {str(e)}")
        return "⚠️ Sorry, I encountered an error. Please try again later."

def main():
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    
    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start polling
    application.run_polling()

if __name__ == '__main__':
    main()
