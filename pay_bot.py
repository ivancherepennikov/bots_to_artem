import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from yookassa import Configuration, Payment

# Токен вашего бота
TELEGRAM_TOKEN = '7965056918:AAFWw8xsyenU5APEnwUgawQbIHrR3dgBg8I'

# Данные для работы с Юкассой
SHOP_ID = 'YOUR_YOOKASSA_SHOP_ID'
SECRET_KEY = 'YOUR_YOOKASSA_SECRET_KEY'

# Инициализация логгера
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка конфигурации Юкассы
Configuration.account_id = SHOP_ID
Configuration.secret_key = SECRET_KEY

def start(update: Update, context: CallbackContext) -> None:
    """Ответ на команду /start"""
    update.message.reply_text('Привет! Для оплаты отправьте команду /pay.')

def pay(update: Update, context: CallbackContext) -> None:
    """Ответ на команду /pay - создание платежа через Юкассу"""
    
    # Создаем платеж через Юкассу
    payment = Payment.create({
        "amount": {"value": "10.00", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": "https://t.me/yourbot"},
        "description": "Покупка в боте"
    })

    # Получаем URL для редиректа и отправляем пользователю
    payment_url = payment.confirmation.confirmation_url
    update.message.reply_text(f'Перейдите по ссылке для завершения оплаты: {payment_url}')

def main() -> None:
    """Запуск бота."""
    updater = Updater(TELEGRAM_TOKEN)

    # Получаем диспетчер для обработки сообщений
    dispatcher = updater.dispatcher

    # Команды
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('pay', pay))

    # Запуск бота
    updater.start_polling()

    # Ожидание завершения работы
    updater.idle()

if __name__ == '__main__':
    main()
