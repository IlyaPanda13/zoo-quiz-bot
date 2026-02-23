import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

SECRET_KEY = os.getenv('SECRET_KEY', 'default-dev-key-change-it')

ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле!")

# Настройка логирования в файл
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Файловый handler с ротацией
file_handler = RotatingFileHandler(
    'bot.log',
    maxBytes=10*1024*1024,
    backupCount=5
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Консольный handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# Настраиваем корневой логгер
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)