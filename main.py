import logging
from monitoring import get_stats, monitor
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from config import BOT_TOKEN, ADMIN_IDS
from database import db

from handlers.start import start_handler
from handlers.quiz import (
    start_quiz,
    handle_answer,
)
from handlers.results import (
    contact_handler,
    share_handler,
    feedback_handler,
    back_to_result_handler,
    copy_share_handler,
    handle_feedback_text,
    view_feedback_command,
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

@monitor("clean_data_command")
async def clean_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для очистки старых данных (только админ)"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return

    days = 30
    if context.args:
        try:
            days = int(context.args[0])
        except:
            pass

    db.clean_old_data(days)
    await update.message.reply_text(f"✅ Удалены данные старше {days} дней")

@monitor("stats_command")
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику бота (только для админов)"""
    user_id = update.effective_user.id

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа")
        return

    stats = get_stats()

    text = f"""
📊 Статистика бота

🕐 Uptime: {stats['uptime']}
👥 Всего пользователей: {stats['users_total']}
📨 Команд обработано: {stats['commands_total']}
❌ Ошибок: {stats['errors_total']}
⚡ Среднее время ответа: {stats['avg_response']}

Популярные команды:
{chr(10).join([f"• {cmd}" for cmd in stats['slow_commands']]) if stats['slow_commands'] else "• Нет данных"}

Частые ошибки:
{chr(10).join([f"• {err[0]}: {err[1]}" for err in stats['common_errors']]) if stats['common_errors'] else "• Нет ошибок"}
    """

    await update.message.reply_text(text)

async def cleanup_old_logs(context: ContextTypes.DEFAULT_TYPE):
    """Очистка старых данных мониторинга"""
    if len(stats['response_times']) > 1000:
        stats['response_times'] = stats['response_times'][-1000:]


def main():
    """Запуск бота"""
    application = Application.builder().token(BOT_TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", start_handler))
    application.add_handler(CommandHandler("feedback_view", view_feedback_command))
    application.add_handler(CommandHandler("clean_data", clean_data_command))
    application.add_handler(CommandHandler("stats", stats_command))

    # Обработчики callback-запросов (кнопок)
    application.add_handler(CallbackQueryHandler(start_quiz, pattern="^start_quiz$"))
    application.add_handler(CallbackQueryHandler(handle_answer, pattern="^answer:"))
    application.add_handler(CallbackQueryHandler(contact_handler, pattern="^contact$"))
    application.add_handler(CallbackQueryHandler(share_handler, pattern="^share_result$"))
    application.add_handler(CallbackQueryHandler(feedback_handler, pattern="^feedback$"))
    application.add_handler(CallbackQueryHandler(back_to_result_handler, pattern="^back_to_result$"))
    application.add_handler(CallbackQueryHandler(copy_share_handler, pattern="^copy_share_text$"))

    # Обработчик текстовых сообщений (для обратной связи)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback_text))

    if application.job_queue:
        application.job_queue.run_repeating(cleanup_old_logs, interval=3600, first=10)
    else:
        logger.warning("JobQueue не доступен, пропускаем планировщик")

    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=[])


if __name__ == '__main__':
    main()