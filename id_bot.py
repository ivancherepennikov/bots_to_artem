import telebot
from telebot import types

TOKEN = "7965056918:AAFWw8xsyenU5APEnwUgawQbIHrR3dgBg8I"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=["start"])
def start(message: types.Message):
    bot.send_message(
        chat_id=message.chat.id, 
        text=message.chat.id,
    )

if __name__ == "__main__":
    bot.polling(non_stop=True)