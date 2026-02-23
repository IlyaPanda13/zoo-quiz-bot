from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from monitoring import monitor

@monitor("start_handler")
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    message = update.message

    db.add_user(user.id, user.username, user.first_name)

    db.reset_user(user.id)

    welcome_text = f"""
    🦁 Привет, {user.first_name}!

    Добро пожаловать в викторину *«Какое у вас тотемное животное?»* от Московского зоопарка!

    🎯 *Как это работает?*
    • Ответьте на {5} простых вопроса о себе
    • На основе ваших ответов мы определим ваше тотемное животное
    • Узнайте интересные факты о нём
    • И конечно, расскажем о программе опеки!

    🐾 Все вопросы основаны на реальных фактах о наших обитателях.

    Готовы начать?
    """

    keyboard = [
        [InlineKeyboardButton("🎮 Начать викторину", callback_data="start_quiz")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if message:
        await message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.callback_query.edit_message_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )