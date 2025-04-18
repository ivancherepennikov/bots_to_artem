import telebot
from telebot import types
import json
import os
from datetime import datetime

# Текущая директория проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Пути к JSON-файлам
TABLE_FILE = os.path.join(BASE_DIR, 'table.json')
QUEUE_FILE = os.path.join(BASE_DIR, 'queue.json')
REVIEWS_FILE = os.path.join(BASE_DIR, 'reviews.json')

# Папка с фото
array_photos = [
    os.path.join(BASE_DIR, 'photos', 'photo_1.jpeg'),
    os.path.join(BASE_DIR, 'photos', 'photo_2.jpeg'),
    os.path.join(BASE_DIR, 'photos', 'photo_3.jpeg'),
    os.path.join(BASE_DIR, 'photos', 'photo_4.jpeg'),
    os.path.join(BASE_DIR, 'photos', 'photo_5.jpeg'),
]

# Создание JSON-файлов, если не существуют
for file in [TABLE_FILE, QUEUE_FILE, REVIEWS_FILE]:
    if not os.path.exists(file):
        with open(file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)

# Загрузка JSON
def load_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Загрузка данных
table = load_json(TABLE_FILE)
queue = load_json(QUEUE_FILE)
reviews = load_json(REVIEWS_FILE)

# Сохранение
def save_json(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_reviews():
    save_json(reviews, REVIEWS_FILE)

def save_queue():
    save_json(queue, QUEUE_FILE)

def save_table():
    save_json(table, TABLE_FILE)

# Токен бота
TOKEN = "7648025267:AAGkXss5g-EPy0hKZKkoImLkjiAoO6cGC1Y"
bot = telebot.TeleBot(TOKEN)

# Глобальные переменные
current_photo_num = 0
current_review_num = 0
user_rent_data = {}


def show_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("FAQ")
    item2 = types.KeyboardButton("фотографии/отзывы")
    item3 = types.KeyboardButton("заказ")
    markup.add(item3)
    markup.add(item1, item2)
    bot.send_message(chat_id, "Главное меню", reply_markup=markup)

def process_review_input(message: types.Message):
    global current_review_num, reviews

    if message.text == "назад":
        show_main_menu(message.chat.id)
    else:
        new_review = {
            'text': message.text,
            'user': message.from_user.first_name,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        reviews.append(new_review)
        current_review_num = len(reviews) - 1
        save_reviews()

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        back = types.KeyboardButton("назад")
        next_btn = types.KeyboardButton("следующий отзыв")  
        prev_btn = types.KeyboardButton('предыдущий отзыв') 
        add_review = types.KeyboardButton('написать отзыв')
        markup.add(prev_btn, next_btn)
        markup.add(add_review)
        markup.add(back)

        review = reviews[current_review_num]
        response = (f"Отзыв {current_review_num + 1}/{len(reviews)}\n"
                   f"Автор: {review['user']}\n"
                   f"Дата: {review['date']}\n\n"
                   f"{review['text']}")

        bot.send_message(message.chat.id, response, reply_markup=markup)

def process_rent_request(message: types.Message, days: int, batteries: int):
    global queue

    # Прайслист
    if batteries > 2:
        base_prices = {
            1: 1900,
            4: 3300,
            7: 4600,
            14: 8100,
            20: 10000,
            30: 13500
        }
        price = base_prices.get(days, 0) + (batteries - 2) * 50 * days
    else:
        price_table = {
            (1, 1): 900,
            (4, 1): 2300,
            (7, 1): 3600,
            (14, 1): 7100,
            (20, 1): 9000,
            (30, 1): 12500,
            (1, 2): 1900,
            (4, 2): 3300,
            (7, 2): 4600,
            (14, 2): 8100,
            (20, 2): 10000,
            (30, 2): 13500
        }
        price = price_table.get((days, batteries), 0)

    bot.send_message(
        chat_id=message.chat.id,
        text=f'Заявка на {days} {"день" if days == 1 else "дня" if days < 5 else "дней"} принята и будет рассмотрена в ближайшее время.\n'
             f'Аккумуляторов: {batteries}\nЦена: {price} руб.'
    )

    current_request_num = int(queue[-1]['order_number']) + 1 if queue else 1
    now = datetime.now()

    new_request = {
        "order_number": str(current_request_num),
        "tern_to_rent": str(days),
        "batteries": str(batteries),
        "user": message.from_user.first_name,
        "tag": message.from_user.username,
        "date": now.strftime("%Y-%m-%d %H:%M"),
        "date_to_end": 'с момента отдачи',
        "price_to_order": str(price)
    }

    queue.append(new_request)
    save_queue()
    show_main_menu(message.chat.id)

@bot.message_handler(commands=["start"])
def start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("заказ"))
    markup.add(types.KeyboardButton("FAQ"), types.KeyboardButton("фотографии/отзывы"))

    bot.send_message(
        chat_id=message.chat.id, 
        text=f"""Привет, {message.from_user.first_name}!
Я бот канала Кузнецов и Володин))
Мы занимаемся сдачей электровелосипедов для курьеров в аренду""",
        reply_markup=markup
    )

@bot.message_handler(content_types=['text'])
def parse_buttons(message: types.Message):
    global current_photo_num, current_review_num

    if message.text == "фотографии/отзывы":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("фотографии"), types.KeyboardButton("отзывы"))
        markup.add(types.KeyboardButton("назад"))
        bot.send_message(message.chat.id, "Вы в разделе фотографии и отзывы", reply_markup=markup)

    elif message.text == "FAQ":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("назад"))
        bot.send_message(message.chat.id, """1. Нужны ли права на ваши электровелосипеды?
Нет, все электровелосипеды по документам 240 Ватт. 
2. Есть ли у Вас залог?
Нет, аренда осуществляется по договору. 
3. Должен ли я платить, если электровелосипед сломается?
Повреждения по типу износа колодок, износа резины оплачиваются за наш счет;
В случае, если повреждения на велосипеде по вашей вине(разбито зеркало заднего вида, например), то они оплачиваются в соответствии с приложением «штрафы» к договору. 
4. Есть ли у Вас скидки постоянным клиентам?
Да, с третьей аренды предоставляется скидка. 
5. Сколько аккумуляторов я могу взять? 
Количество не ограничено, хоть 1, хоть 5.""", reply_markup=markup)

    elif message.text == "фотографии":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("предыдущий снимок"), types.KeyboardButton("следующий снимок"))
        markup.add(types.KeyboardButton("назад"))
        with open(array_photos[current_photo_num], 'rb') as photo:
            bot.send_photo(message.chat.id, photo=photo, caption=f"Фото {current_photo_num + 1}/{len(array_photos)}", reply_markup=markup)

    elif message.text == "следующий снимок":
        current_photo_num = (current_photo_num + 1) % len(array_photos)
        photo_path = array_photos[current_photo_num]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("предыдущий снимок"), types.KeyboardButton("следующий снимок"))
        markup.add(types.KeyboardButton("назад"))
        
        with open(photo_path, 'rb') as photo:
            bot.send_photo(
                chat_id=message.chat.id,
                photo=photo,
                caption=f"Фото {current_photo_num + 1}/{len(array_photos)}",
                reply_markup=markup
            )

    elif message.text == "предыдущий снимок":
        current_photo_num = (current_photo_num - 1) % len(array_photos)
        photo_path = array_photos[current_photo_num]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("предыдущий снимок"), types.KeyboardButton("следующий снимок"))
        markup.add(types.KeyboardButton("назад"))
        
        with open(photo_path, 'rb') as photo:
            bot.send_photo(
                chat_id=message.chat.id,
                photo=photo,
                caption=f"Фото {current_photo_num + 1}/{len(array_photos)}",
                reply_markup=markup
            )

    elif message.text == "отзывы":
        current_review_num = 0
        if not reviews:
            bot.send_message(message.chat.id, "Пока нет отзывов")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("предыдущий отзыв"), types.KeyboardButton("следующий отзыв"))
        markup.add(types.KeyboardButton("написать отзыв"))
        markup.add(types.KeyboardButton("назад"))
        bot.send_message(
            chat_id=message.chat.id,
            text=f"вы в разделе отзывы",
            reply_markup=markup
        )

    elif message.text == "следующий отзыв":
        current_review_num = (current_review_num + 1) % len(reviews)
        review = reviews[current_review_num]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("предыдущий отзыв"), types.KeyboardButton("следующий отзыв"))
        markup.add(types.KeyboardButton("написать отзыв"))
        markup.add(types.KeyboardButton("назад"))
        bot.send_message(
            chat_id=message.chat.id,
            text=f"Отзыв {current_review_num + 1}/{len(reviews)}\nАвтор: {review['user']}\nДата: {review['date']}\n\n{review['text']}",
            reply_markup=markup
        )

    elif message.text == "предыдущий отзыв":
        current_review_num = (current_review_num - 1) % len(reviews)
        review = reviews[current_review_num]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("предыдущий отзыв"), types.KeyboardButton("следующий отзыв"))
        markup.add(types.KeyboardButton("написать отзыв"))
        markup.add(types.KeyboardButton("назад"))
        bot.send_message(
            chat_id=message.chat.id,
            text=f"Отзыв {current_review_num + 1}/{len(reviews)}\nАвтор: {review['user']}\nДата: {review['date']}\n\n{review['text']}",
            reply_markup=markup
        )

    elif message.text == "написать отзыв":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("назад"))
        msg = bot.send_message(message.chat.id, "Напишите ваш отзыв в сообщении:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_review_input)

    elif message.text == "назад":
        show_main_menu(message.chat.id)
        current_photo_num = 0
        current_review_num = 0

    elif message.text == "заказ":
        free_bikes = [bike for bike in table if bike.get('state') == 'free']
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("сделать заказ"))
        markup.add(types.KeyboardButton("назад"))

        k = len(free_bikes)
        m = len(queue)
        if k == 0:
            bot.send_message(message.chat.id, f"свободных велосипедов сейчас: {k}\nзаказов в очереди сейчас: {m}\nмодель: Jatson\nВы можете оставить заявку — с вами свяжутся", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, f"свободных велосипедов сейчас: {k}\nзаказов в очереди сейчас: {m}\nмодель: Jatson", reply_markup=markup)

    elif message.text == "сделать заказ":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            types.KeyboardButton("1 день"), types.KeyboardButton("4 дня"),
            types.KeyboardButton("7 дней"), types.KeyboardButton("14 дней"),
            types.KeyboardButton("20 дней"), types.KeyboardButton("30 дней")
        )
        markup.add(types.KeyboardButton("назад"))
        bot.send_message(message.chat.id, "Выберите срок аренды:", reply_markup=markup)


    elif message.text in ["1 день", "4 дня", "7 дней", "14 дней", "20 дней", "30 дней"]:
        days = int(message.text.split()[0])
        user_rent_data[message.chat.id] = {"days": days}

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("1"), types.KeyboardButton("2"))
        markup.add(types.KeyboardButton("назад"))
        bot.send_message(
            message.chat.id,
            "Сколько аккумуляторов вам нужно?\nЕсли больше двух — просто введите число сообщением.",
            reply_markup=markup
        )


    elif message.text.replace(" ", "").isdigit():
        if message.chat.id not in user_rent_data:
            bot.send_message(message.chat.id, "Сначала выберите срок аренды.")
            return

        batteries = int(message.text.split()[0])
        days = user_rent_data[message.chat.id]["days"]

        # Прайс
        if days == 1 and batteries == 1:
            price = 900
        elif days == 4 and batteries == 1:
            price = 2300
        elif days == 7 and batteries == 1:
            price = 3600
        elif days == 14 and batteries == 1:
            price = 7100
        elif days == 20 and batteries == 1:
            price = 9000
        elif days == 30 and batteries == 1:
            price = 12500
        elif days == 1 and batteries == 2:
            price = 1900
        elif days == 4 and batteries == 2:
            price = 3300
        elif days == 7 and batteries == 2:
            price = 4600
        elif days == 14 and batteries == 2:
            price = 8100
        elif days == 20 and batteries == 2:
            price = 10000
        elif days == 30 and batteries == 2:
            price = 13500
        elif batteries > 2:
            base_prices = {
                1: 1900,
                4: 3300,
                7: 4600,
                14: 8100,
                20: 10000,
                30: 13500
            }
            price = base_prices.get(days, 0) + (batteries - 2) * 50 * days
        else:
            bot.send_message(message.chat.id, "Что-то пошло не так. Попробуйте снова.")
            return

        bot.send_message(
            chat_id=message.chat.id,
            text=f"Заявка на {days} дней с {batteries} аккумулятор{'ом' if batteries == 1 else 'ами'} принята.\nЦена: {price} руб."
        )

        current_request_num = int(queue[-1]['order_number']) + 1 if queue else 1
        now = datetime.now()

        new_request = {
            "order_number": str(current_request_num),
            "tern_to_rent": f"{days}",
            "batteries": str(batteries),
            "user": message.from_user.first_name,
            "tag": message.from_user.username,
            "date": now.strftime("%Y-%m-%d %H:%M"),
            "date_to_end": 'с момента отдачи',
            "price_to_order": str(price)
        }

        queue.append(new_request)
        save_queue()
        user_rent_data.pop(message.chat.id, None)
        show_main_menu(message.chat.id)



if __name__ == "__main__":
    bot.polling(none_stop=True)
