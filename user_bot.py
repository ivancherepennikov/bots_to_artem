import telebot
from telebot import types
import json
import os
from datetime import datetime
from supabase import create_client
import requests

SUPABASE_URL = "https://bvngkihlvtarxgghqffr.supabase.co"
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ2bmdraWhsdnRhcnhnZ2hxZmZyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUwNTkyNDEsImV4cCI6MjA2MDYzNTI0MX0.lS-U84Vlqz4TFvABVJSNis9Vh31ECAj25x2QVpRqbrM'
STORAGE_BUCKET = "bikes" #это название бакета

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

photo_extensions = ['.jpg', '.jpeg', '.png', '.webp']
all_files = supabase.storage.from_(STORAGE_BUCKET).list()
array_photos = [f['name'] for f in all_files if os.path.splitext(f['name'])[1].lower() in photo_extensions]

def get_file(file_name, default=[]):
    try:
        response = supabase.storage.from_(STORAGE_BUCKET).download(file_name)
        if response is None:
            return default
        data = json.loads(response.decode('utf-8'))
        return data
    except Exception as e:
        print(f"[get_file] Ошибка чтения {file_name}: {e}")
        return default

def save_file(file_name, data):
    content = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
    try:
        if file_exists(file_name):
            # Если файл существует — обновляем
            supabase.storage.from_(STORAGE_BUCKET).update(
                file_name,
                content,
                {"content-type": "application/json"}
            )
            print(f"[save_file] Обновлён: {file_name}")
        else:
            # Иначе создаём новый
            supabase.storage.from_(STORAGE_BUCKET).upload(
                file_name,
                content,
                {"content-type": "application/json"}
            )
            print(f"[save_file] Загружен заново: {file_name}")
    except Exception as e:
        print(f"[save_file] Ошибка при сохранении {file_name}: {e}")
        raise

def file_exists(file_name):
    try:
        files = supabase.storage.from_(STORAGE_BUCKET).list()
        return any(f['name'] == file_name for f in files)
    except Exception as e:
        print(f"Ошибка при проверке существования файла: {e}")
        return False

history = get_file("history.json")
def save_history():
    save_file('history.json', history)

queue = get_file("queue.json")
def save_queue():
    save_file('queue.json', queue)

table = get_file('table.json')
def save_table():
    save_file('table.json', table)

order_in_processing = get_file("order_in_processing.json")
def save_order_in_processing():
    save_file('order_in_processing.json', order_in_processing)

reviews = get_file("reviews")
def save_reviews():
    save_file('reviews', reviews)

if not get_file("history.json"):
    save_file("history.json", [])

if not get_file("queue.json"):
    save_file("queue.json", [])

if not get_file("table.json"):
    save_file("table.json", [])

if not get_file("order_in_processing.json"):
    save_file("order_in_processing.json", [])

if not get_file("reviews.json"):
    save_file("reviews.json", [])  


def get_photo_bytes(photo_name):
    try:
        return supabase.storage.from_(STORAGE_BUCKET).download(photo_name)
    except Exception as e:
        print(f"Ошибка загрузки фото: {e}")
        return None


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
Я бот по сдаче электор велосипедов Jatson в аренду для курьеров и не только
если тебе нужна информация по нашим ценам, то отправляй в бота команду /help
удачного пользования!""",
        reply_markup=markup
    )

@bot.message_handler(commands=['help'])
def help(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("заказ"))
    markup.add(types.KeyboardButton("FAQ"), types.KeyboardButton("назад"))
    bot.send_message(
        chat_id=message.chat.id,
        text = """это информационное сообщение с прайслитом
вы можете взять у нас велосипед в аренду, права на него не нужны
мы предлагаем следущие тарифы:
дни    с одним акб    с двумя акб
  1              900р           1000р
  4           2300р           2700р
  7           3600р           4300р
 14           7100р           8000р
 20          9000р         10000р
 30        12500р         14000р
если вам понадобится большее количество акб, то цена будет рассчитываться по формуле:
цена = цена (с двумя акб) + 100 * количесто доп акб * количество дней
если у вас еще остались вопросы посмотрите раздел FAQ""",
        reply_markup=markup,
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
        text = (
            "*1\\. Нужны ли права на ваши электровелосипеды?*\n"
            "Нет, все электровелосипеды по документам 240 Ватт\\.\n\n"
            "*2\\. Есть ли у Вас залог?*\n"
            "Нет, аренда осуществляется по договору\\.\n\n"
            "*3\\. Должен ли я платить, если электровелосипед сломается?*\n"
            "Износ деталей — бесплатно\\.\n"
            "Поломки по вине арендатора — оплачиваются согласно договору\\.\n\n"
            "*4\\. Есть ли скидки постоянным клиентам?*\n"
            "Да, с третьей аренды предоставляется скидка\\.\n\n"
            "*5\\. Сколько аккумуляторов я могу взять?*\n"
            "Сколько угодно: 1, 2, 3 и т\\.д\\.\n\n"
            "Если остались вопросы — пишите нашим менеджерам:\n"
            "[Артем](https://t.me/temaLiberty) и [Егор](https://t.me/egoorst)"
        )

        bot.send_message(
            message.chat.id,
            text,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,  # ← вот это убирает ссылку-снизу
            reply_markup=markup
        )



    elif message.text == "фотографии":
        current_photo_num = 0
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("предыдущий снимок"), types.KeyboardButton("следующий снимок"))
        markup.add(types.KeyboardButton("назад"))

        if array_photos:
            photo_data = get_photo_bytes(array_photos[current_photo_num])
            if photo_data:
                bot.send_photo(message.chat.id, photo=photo_data, caption=f"Фото {current_photo_num + 1}/{len(array_photos)}", reply_markup=markup)
            else:
                bot.send_message(message.chat.id, "Не удалось загрузить фото.", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Фотографии не найдены.", reply_markup=markup)


    elif message.text == "следующий снимок":
        current_photo_num = (current_photo_num + 1) % len(array_photos)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("предыдущий снимок"), types.KeyboardButton("следующий снимок"))
        markup.add(types.KeyboardButton("назад"))

        photo_data = get_photo_bytes(array_photos[current_photo_num])
        if photo_data:
            bot.send_photo(message.chat.id, photo=photo_data, caption=f"Фото {current_photo_num + 1}/{len(array_photos)}", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Не удалось загрузить фото.", reply_markup=markup)

    elif message.text == "предыдущий снимок":
        current_photo_num = (current_photo_num - 1) % len(array_photos)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("предыдущий снимок"), types.KeyboardButton("следующий снимок"))
        markup.add(types.KeyboardButton("назад"))

        photo_data = get_photo_bytes(array_photos[current_photo_num])
        if photo_data:
            bot.send_photo(message.chat.id, photo=photo_data, caption=f"Фото {current_photo_num + 1}/{len(array_photos)}", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Не удалось загрузить фото.", reply_markup=markup)


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
            price = 1000
        elif days == 4 and batteries == 2:
            price = 2700
        elif days == 7 and batteries == 2:
            price = 4300
        elif days == 14 and batteries == 2:
            price = 8000
        elif days == 20 and batteries == 2:
            price = 10000
        elif days == 30 and batteries == 2:
            price = 14000
        elif batteries > 2:
            base_prices = {
                1: 1000,
                4: 2700,
                7: 4300,
                14: 8000,
                20: 10000,
                30: 14000
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
