import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import aiosmtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from data.animals import ANIMALS, get_default_animal
from database import db

load_dotenv()

logger = logging.getLogger(__name__)

# Настройки почты
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.yandex.ru')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
NOTIFY_EMAIL = os.getenv('NOTIFY_EMAIL')


async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса связи с сотрудником"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    result_animal = context.user_data.get('last_result', 'capybara')

    animal = ANIMALS.get(result_animal, get_default_animal())

    try:
        await send_email_notification(user, animal)
        email_status = "✅ Уведомление отправлено сотруднику"
    except Exception as e:
        logger.error(f"Ошибка отправки почты: {e}")
        email_status = "❌ Ошибка отправки, но мы передадим информацию"

    contact_text = f"""
📬 *Связь с сотрудником зоопарка*

{email_status}

Сотрудник свяжется с вами в ближайшее время по указанным в Telegram контактам.

*Ваш результат:* {animal['name']}
    """

    keyboard = [
        [InlineKeyboardButton("◀️ Назад к результату", callback_data="back_to_result")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query.message.photo:
        await context.bot.send_message(
            chat_id=user.id,
            text=contact_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            contact_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def send_email_notification(user, animal):
    """Отправка email уведомления сотруднику"""
    message = EmailMessage()
    message["From"] = SMTP_USER
    message["To"] = NOTIFY_EMAIL
    message["Subject"] = f"Запрос от пользователя {user.first_name}"

    body = f"""
Пользователь запросил связь с сотрудником зоопарка.

👤 Пользователь: {user.first_name} (@{user.username})
🆔 ID: {user.id}
🦁 Результат викторины: {animal['name']}

Животное: {animal['id']}
Интересный факт: {animal['fun_fact']}

Свяжитесь с пользователем через Telegram.
    """

    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=SMTP_USER,
        password=SMTP_PASSWORD,
        use_tls=False,
        start_tls=True
    )


async def share_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса на публикацию результата"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    result_animal = context.user_data.get('last_result', 'capybara')

    animal = ANIMALS.get(result_animal, get_default_animal())

    bot_link = f"https://t.me/{context.bot.username}"
    share_text = f"""
🐾 *Я прошёл викторину Московского зоопарка!*

🎉 Моё тотемное животное — *{animal['name']}!* 🎉

{animal['description'].split('.')[0]}.

✨ *Интересный факт:* {animal['fun_fact']}

---
👉 *Узнай своё тотемное животное:* {bot_link}
#МосковскийЗоопарк #ТотемноеЖивотное
    """

    keyboard = [
        [
            InlineKeyboardButton("📱 Telegram", switch_inline_query=share_text[:100]),
            InlineKeyboardButton("📲 Копировать", callback_data="copy_share_text")
        ],
        [
            InlineKeyboardButton("◀️ Назад к результату", callback_data="back_to_result")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query.message.photo:
        await context.bot.send_message(
            chat_id=user.id,
            text=f"*Поделиться результатом*\n\nВыберите соцсеть или скопируйте текст:\n\n{share_text}",
            reply_markup=reply_markup,
            parse_mode='None'
        )
    else:
        await query.edit_message_text(
            f"*Поделиться результатом*\n\nВыберите соцсеть или скопируйте текст:\n\n{share_text}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def copy_share_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Копирование текста для шаринга"""
    query = update.callback_query
    await query.answer(
        "✅ Текст скопирован! Вставьте его в любую соцсеть ✨",
        show_alert=True
    )


async def feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса обратной связи"""
    query = update.callback_query
    await query.answer()

    feedback_text = """
⭐ *Оставьте отзыв*

Нам очень важно ваше мнение! Напишите любое сообщение в чат, и оно будет передано команде зоопарка.

Ваши пожелания помогут нам стать лучше!
    """

    keyboard = [
        [InlineKeyboardButton("◀️ Назад к результату", callback_data="back_to_result")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query.message.photo:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text=feedback_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            feedback_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    context.user_data['awaiting_feedback'] = True


async def back_to_result_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат к результату"""
    query = update.callback_query
    await query.answer()

    result_animal = context.user_data.get('last_result', 'capybara')

    animal = ANIMALS.get(result_animal, get_default_animal())

    result_text = f"""
🎉 *Ваше тотемное животное — {animal['name']}!* 🎉

{animal['description']}

✨ *Интересный факт:* {animal['fun_fact']}

---
🐾 *Программа опеки*
{animal['guardian_info']}
    """

    # Кнопки
    keyboard = [
        [
            InlineKeyboardButton("📞 Сотрудник", callback_data="contact"),
            InlineKeyboardButton("🔄 Заново", callback_data="start_quiz")
        ],
        [
            InlineKeyboardButton("📤 Поделиться", callback_data="share_result"),
            InlineKeyboardButton("⭐ Отзыв", callback_data="feedback")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_photo(
        chat_id=update.effective_user.id,
        photo=animal["image_url"],
        caption=result_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def handle_feedback_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового сообщения как отзыва"""
    user = update.effective_user
    feedback_text = update.message.text

    if context.user_data.get('awaiting_feedback'):

        result_animal = context.user_data.get('last_result', 'capybara')
        from data.animals import ANIMALS, get_default_animal
        animal = ANIMALS.get(result_animal, get_default_animal())

        db.save_feedback(
            user_id=user.id,
            username=user.username or "no_username",
            feedback_text=feedback_text,
            animal_result=animal['name']
        )

        await update.message.reply_text(
            "✅ Спасибо за ваш отзыв! Мы обязательно его учтем.\n\n"
            "Ваше мнение помогает нам становиться лучше ❤️",
            reply_markup=None
        )

        context.user_data['awaiting_feedback'] = False
    else:
        await update.message.reply_text(
            "Используйте кнопки меню для навигации 🤖"
        )


from config import ADMIN_IDS


async def view_feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра отзывов (только для админов)"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return

    conn = sqlite3.connect('quiz_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT created_at, username, feedback_text, animal_result 
        FROM feedback 
        ORDER BY created_at DESC 
        LIMIT 20
    ''')
    feedbacks = cursor.fetchall()
    conn.close()

    if not feedbacks:
        await update.message.reply_text("📭 Пока нет отзывов")
        return

    text = "📊 *Последние отзывы:*\n\n"
    for f in feedbacks:
        text += f"🕐 {f[0]}\n👤 @{f[1]}\n🦁 {f[3]}\n💬 {f[2]}\n---\n"

    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            await update.message.reply_text(text[i:i + 4000], parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')