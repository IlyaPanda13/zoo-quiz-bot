import logging
import time
from datetime import datetime
from collections import Counter
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Статистика
stats = {
    'commands': Counter(),
    'errors': Counter(),
    'users': set(),
    'response_times': [],
    'start_time': datetime.now()
}


def monitor(handler_name):
    """Декоратор для мониторинга обработчиков"""

    def decorator(func):
        import inspect
        is_async = inspect.iscoroutinefunction(func)

        if is_async:
            @wraps(func)
            async def async_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
                start = time.time()
                user_id = update.effective_user.id if update.effective_user else None

                try:
                    if user_id:
                        stats['users'].add(user_id)

                    if update.message and update.message.text:
                        stats['commands'][update.message.text] += 1
                    elif update.callback_query:
                        stats['commands'][update.callback_query.data] += 1

                    result = await func(update, context, *args, **kwargs)

                    response_time = time.time() - start
                    stats['response_times'].append(response_time)

                    if response_time > 2:
                        logger.warning(f"⚠️ Медленный обработчик {handler_name}: {response_time:.2f}с")

                    return result

                except Exception as e:
                    stats['errors'][str(e)[:50]] += 1
                    logger.error(f"❌ Ошибка в {handler_name}: {e}")
                    raise

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    stats['errors'][str(e)[:50]] += 1
                    logger.error(f"❌ Ошибка в {handler_name}: {e}")
                    raise

            return sync_wrapper

    return decorator


def get_stats():
    """Получить статистику"""
    now = datetime.now()
    uptime = now - stats['start_time']

    avg_response = sum(stats['response_times'][-100:]) / max(len(stats['response_times'][-100:]), 1)

    return {
        'uptime': str(uptime).split('.')[0],
        'users_total': len(stats['users']),
        'commands_total': sum(stats['commands'].values()),
        'errors_total': sum(stats['errors'].values()),
        'avg_response': f"{avg_response:.2f}с",
        'slow_commands': [cmd for cmd, count in stats['commands'].most_common(5)],
        'common_errors': stats['errors'].most_common(3)
    }


def log_error(error_type, user_id=None, details=None):
    """Логирование ошибок"""
    stats['errors'][error_type] += 1
    logger.error(f"Error: {error_type} | User: {user_id} | Details: {details}")