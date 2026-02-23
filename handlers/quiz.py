from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from data.questions import QUESTIONS, TOTAL_QUESTIONS
import logging
from monitoring import monitor

logger = logging.getLogger(__name__)

@monitor("start_quiz")
async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало викторины - показ первого вопроса"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    db.reset_user(user_id)

    if query.message.photo:
        await context.bot.send_message(
            chat_id=user_id,
            text="🔄 Начинаем викторину заново!"
        )
        await show_question_new(update, context, 1)
    else:
        await show_question(update, context, 1)

@monitor("show_question_new")
async def show_question_new(update: Update, context: ContextTypes.DEFAULT_TYPE, question_index: int):
    """Показать вопрос новым сообщением (для случаев, когда нельзя редактировать)"""
    question_data = next((q for q in QUESTIONS if q["id"] == question_index), None)

    if not question_data:
        await finish_quiz(update, context)
        return

    question_text = f"*Вопрос {question_index}/{TOTAL_QUESTIONS}*\n\n"
    question_text += f"{question_data['text']}\n\n"

    for i, option in enumerate(question_data["options"], 1):
        question_text += f"{i}. {option['text']}\n\n"

    keyboard = []
    row = []
    for i in range(len(question_data["options"])):
        callback_data = f"answer:{question_index}:{i}"
        row.append(InlineKeyboardButton(f"{i + 1}", callback_data=callback_data))

    keyboard.append(row)
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=question_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

@monitor("show_question")
async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE, question_index: int):
    """Показать вопрос по номеру"""
    query = update.callback_query

    question_data = next((q for q in QUESTIONS if q["id"] == question_index), None)

    if not question_data:
        await finish_quiz(update, context)
        return

    question_text = f"*Вопрос {question_index}/{TOTAL_QUESTIONS}*\n\n"
    question_text += f"{question_data['text']}\n\n"

    for i, option in enumerate(question_data["options"], 1):
        question_text += f"{i}. {option['text']}\n\n"

    keyboard = []
    row = []
    for i in range(len(question_data["options"])):
        callback_data = f"answer:{question_index}:{i}"
        row.append(InlineKeyboardButton(f"{i + 1}", callback_data=callback_data))

        # По 2 кнопки в ряд
        if len(row) == 2 or i == len(question_data["options"]) - 1:
            keyboard.append(row)
            row = []

    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.edit_message_text(
            question_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            question_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

@monitor("handle_answer")
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответа пользователя"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    _, question_id, option_index = query.data.split(':')
    question_id = int(question_id)
    option_index = int(option_index)

    current_question, scores_dict = db.get_user_state(user_id)

    if scores_dict:
        scores = scores_dict
    else:
        scores = {}

    question_data = next((q for q in QUESTIONS if q["id"] == question_id), None)
    if question_data:
        selected_option = question_data["options"][option_index]

        for animal_id, points in selected_option["weights"].items():
            current_score = scores.get(animal_id, 0)
            scores[animal_id] = current_score + points
            logger.info(f"User {user_id}: {animal_id} +{points} = {scores[animal_id]}")

    db.update_user_state(user_id, question_id, scores)

    next_question = question_id + 1

    if next_question <= TOTAL_QUESTIONS:
        await show_question(update, context, next_question)
    else:
        await finish_quiz(update, context)

@monitor("finish_quiz")
async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение викторины и показ результата"""
    query = update.callback_query
    user_id = update.effective_user.id

    _, scores_dict = db.get_user_state(user_id)

    result_animal = determine_animal(scores_dict)

    context.user_data['last_result'] = result_animal

    await show_result(update, context, result_animal)

@monitor("determine_animal")
def determine_animal(scores_dict):
    """Определяет животное по сумме баллов"""
    if not scores_dict:
        return "capybara"

    max_score = -1
    result_animal = "capybara"

    for animal_id, score in scores_dict.items():
        if score > max_score:
            max_score = score
            result_animal = animal_id

    logger.info(f"Определено животное: {result_animal} с баллами {max_score}")
    return result_animal

@monitor("show_result")
async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE, animal_id: str):
    """Показывает результат викторины"""
    from data.animals import ANIMALS, get_default_animal

    query = update.callback_query
    animal = ANIMALS.get(animal_id, get_default_animal())

    result_text = f"""
🎉 *Ваше тотемное животное — {animal['name']}!* 🎉

{animal['description']}

✨ *Интересный факт:* {animal['fun_fact']}

---
🐾 *Программа опеки*
{animal['guardian_info']}
    """

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

    if query:
        await query.message.delete()
        await context.bot.send_photo(
            chat_id=update.effective_user.id,
            photo=animal["image_url"],
            caption=result_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )