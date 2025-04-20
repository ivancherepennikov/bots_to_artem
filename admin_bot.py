import telebot
from telebot import types
import json
import os
from datetime import datetime, timedelta
import threading
import hashlib
import time 
from supabase import create_client
import requests

SUPABASE_URL = "https://bvngkihlvtarxgghqffr.supabase.co"
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ2bmdraWhsdnRhcnhnZ2hxZmZyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUwNTkyNDEsImV4cCI6MjA2MDYzNTI0MX0.lS-U84Vlqz4TFvABVJSNis9Vh31ECAj25x2QVpRqbrM'
STORAGE_BUCKET = "bikes" #это название бакета

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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

if not get_file("history.json"):
    save_file("history.json", [])

if not get_file("queue.json"):
    save_file("queue.json", [])

if not get_file("table.json"):
    save_file("table.json", [])

if not get_file("order_in_processing.json"):
    save_file("order_in_processing.json", [])

TOKEN = "7719626488:AAEeZ_k1YVfoOjzxfwZZUqpeYyQwdaCkKtY"
bot = telebot.TeleBot(TOKEN)

temp_data = {}

def show_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("добавить велик")
    item_add = types.KeyboardButton("удалить велик")
    item2 = types.KeyboardButton("сдаем в аренду")
    item3 = types.KeyboardButton("показать актуальную информацию")
    item6= types.KeyboardButton('показать велики в работе')
    item5 = types.KeyboardButton("показать очередь")
    item4 = types.KeyboardButton("возвращение")
    item_history = types.KeyboardButton("показать историю заказов")
    item_main_menu = types.KeyboardButton("главное меню")
    markup.add(item1, item_add)
    markup.add(item2)
    markup.add(item3)
    markup.add(item5)
    markup.add(item6)
    markup.add(item4)
    markup.add(item_history)
    markup.add(item_main_menu)
    bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)

def ask_for_model(message: types.Message):
    """Запрашивает модель велика"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_cancel = types.KeyboardButton("главное меню")
    markup.add(item_cancel)

    msg = bot.send_message(
        chat_id=message.chat.id,
        text="Введите модель велика:",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_model_input)

def process_model_input(message: types.Message):
    """Обрабатывает ввод модели и запрашивает статус"""
    if message.text == "главное меню":
        show_main_menu(message.chat.id)
        return

    global temp_data
    temp_data[message.chat.id] = {'model': message.text}  # Сохраняем только модель
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("free")
    item2 = types.KeyboardButton("occupate")
    markup.add(item1, item2)
    
    msg = bot.send_message(
        chat_id=message.chat.id,
        text="Выберите статус велика:",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_state_input)

def process_state_input(message: types.Message):
    """Обрабатывает ввод статуса и запрашивает пробег"""
    if message.text == "главное меню":
        show_main_menu(message.chat.id)
        return

    global temp_data
    
    temp_data[message.chat.id]['state'] = message.text.lower()
    
    msg = bot.send_message(
        chat_id=message.chat.id,
        text="Введите пробег велика (в км):",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, process_distance_input)

def process_distance_input(message: types.Message):
    """Обрабатывает ввод пробега и сохраняет данные"""
    if message.chat.id in temp_data and message.text == "главное меню":
        show_main_menu(message.chat.id)
        return

    global table
    
    try:
        distance = int(message.text)
    except ValueError:
        bot.send_message(
            chat_id=message.chat.id,
            text="Ошибка: введите число для пробега"
        )
        return ask_for_model(message)
    
    bike_number = len(table) + 1
    
    new_bike = {
        "number": bike_number, 
        "model": temp_data[message.chat.id]['model'],
        "distance": distance,
        "state": temp_data[message.chat.id]['state'],
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "date_to_end": "свободен",
        "all_time_income": "0"
    }
    
    table.append(new_bike)
    save_table()
    del temp_data[message.chat.id]
        
    bot.send_message(
        chat_id=message.chat.id,
        text=f"Велик успешно добавлен в таблицу! Номер: {bike_number}",
    )
    show_main_menu(message.chat.id)


def trade_state(message: types.Message):
    if not queue:
        bot.send_message(
            chat_id=message.chat.id,
            text='нет заявок',
        )
        return

    """Запрашивает номер заявки и меняет статус велосипеда на 'occupate'"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    for bike in queue:
        item = types.KeyboardButton(str(bike['order_number']))
        markup.add(item)

    item_main_menu = types.KeyboardButton("главное меню")
    markup.add(item_main_menu)

    msg = bot.send_message(
        chat_id=message.chat.id,
        text= "номера заявок",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_trade_input)

def process_bike_rent(message: types.Message):
    """Привязывает выбранный велик к заявке и меняет его статус"""
    if message.text == "главное меню":
        show_main_menu(message.chat.id)
        return

    global table, queue, order_in_processing

    try:
        bike_number = int(message.text)
        bike = next((b for b in table if b['number'] == bike_number and b['state'] == 'free'), None)

        if not bike:
            bot.send_message(message.chat.id, "Велосипед не найден или уже занят. Выберите другой.")
            return trade_state(message)

        bike['state'] = 'occupate'
        bike['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M")

        order_number = temp_data[message.chat.id]['order_number']
        order = next((o for o in queue if int(o['order_number']) == order_number), None)

        if not order:
            bot.send_message(message.chat.id, "Заявка не найдена.")
            return show_main_menu(message.chat.id)

        rent_start = datetime.now()

        try:
            rent_days = int(order.get("tern_to_rent", "1").split()[0])
        except (ValueError, IndexError):
            rent_days = 1

        batteries = int(order.get("batteries", 1))
        rent_end = rent_start + timedelta(days=rent_days)
        
        # Определяем цену по прайс-листу
        if rent_days == 1 and batteries == 1:
            price = 900
        elif rent_days == 4 and batteries == 1:
            price = 2300
        elif rent_days == 7 and batteries == 1:
            price = 3600
        elif rent_days == 14 and batteries == 1:
            price = 7100
        elif rent_days == 20 and batteries == 1:
            price = 9000
        elif rent_days == 30 and batteries == 1:
            price = 12500
        elif rent_days == 1 and batteries == 2:
            price = 1000
        elif rent_days == 4 and batteries == 2:
            price = 2700
        elif rent_days == 7 and batteries == 2:
            price = 4300
        elif rent_days == 14 and batteries == 2:
            price = 8000
        elif rent_days == 20 and batteries == 2:
            price = 10000
        elif rent_days == 30 and batteries == 2:
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
            price = base_prices.get(rent_days, 0) + (batteries - 2) * 100 * rent_days
        else:
            bot.send_message(
                message.chat.id,
                "Неподдерживаемый срок аренды или количество батарей."
            )
            return show_main_menu(message.chat.id)

        # Обновляем данные велосипеда
        bike["date_to_end"] = rent_end.strftime("%Y-%m-%d %H:%M")

        # Обновляем запись в очереди (а не в истории)
        updated_order = {
            "order_number": str(order_number),
            "tern_to_rent": f"{rent_days}",
            "number_of_bike": str(bike_number),
            "user": order['user'],
            "tag": order['tag'],
            "date": order['date'],
            "date_to_end": rent_end.strftime("%Y-%m-%d %H:%M"),
            "price_to_order": str(price),
            "batteries": str(batteries)
        }

        # Добавляем заказ в работу
        order_in_processing.append({
            "number_of_bike": str(bike_number),
            "user": order['user'],
            "tag": order['tag'],
            "date_to_end": rent_end.strftime("%Y-%m-%d %H:%M"),
            "price": str(price),
            "batteries": str(batteries)
        })

        # Обновляем очередь (заменяем старую запись на обновленную)
        queue = [updated_order if int(q['order_number']) == order_number else q for q in queue]

        # Обновляем прибыль у велосипеда
        for bike in table:
            if str(bike["number"]) == str(bike_number):
                try:
                    previous_income = int(bike.get("all_time_income", "0"))
                except ValueError:
                    previous_income = 0
                bike["all_time_income"] = str(previous_income + price)
                break

        # Сохраняем все изменения
        save_table()
        save_queue()
        save_order_in_processing()

        bot.send_message(
            chat_id=message.chat.id,
            text=f"""
✅ Заказ оформлен:
Велосипед №{bike_number}
Арендатор: @{order['tag']}
Срок: {rent_days} дней
Батареи: {batteries} шт.
Окончание: {rent_end.strftime('%Y-%m-%d %H:%M')}
Цена: {price} руб.
"""
        )
        show_main_menu(message.chat.id)

    except ValueError:
        bot.send_message(message.chat.id, "Введите корректный номер велосипеда.")
        trade_state(message)
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {str(e)}")
        show_main_menu(message.chat.id)


def process_trade_input(message: types.Message):
    """Обрабатывает выбор заявки и показывает список свободных велосипедов"""
    if message.text == "главное меню":
        show_main_menu(message.chat.id)
        return

    global temp_data

    try:
        order_number = int(message.text)
        selected_order = next((item for item in queue if int(item['order_number']) == order_number), None)

        if not selected_order:
            bot.send_message(message.chat.id, "Заявка не найдена. Попробуйте снова.")
            return trade_state(message)

        # Сохраняем заявку во временные данные
        temp_data[message.chat.id] = {"order_number": order_number}

        # Получаем список свободных велосипедов
        free_bikes = [bike for bike in table if bike['state'] == 'free']

        if not free_bikes:
            bot.send_message(message.chat.id, "Нет доступных велосипедов для аренды.")
            return show_main_menu(message.chat.id)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for bike in free_bikes:
            markup.add(types.KeyboardButton(str(bike['number'])))
        markup.add(types.KeyboardButton("главное меню"))

        msg = bot.send_message(
            chat_id=message.chat.id,
            text="Выберите велосипед для аренды (номер):",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, process_bike_rent)

    except ValueError:
        bot.send_message(message.chat.id, "Введите корректный номер заявки.")
        trade_state(message)


def show_table(message: types.Message):
    for bike in table:
        bot.send_message(
            chat_id=message.chat.id,
            text=f'номер: {bike['number']}\nмодель: {bike['model']}\nпробег: {bike['distance']}\nстатус: {bike['state']}\nкогда освободится: {bike["date_to_end"]}\nприбыль с велика: {bike['all_time_income']}',
        )

def trade_state_free(message: types.Message):
    """Запрашивает номер велосипеда и меняет его статус на 'free'"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    k = 0
    for bike in table:
        if bike['state'] == 'occupate':
            item = types.KeyboardButton(str(bike['number']))
            markup.add(item)
            k += 1

    if k == 0:
        bot.send_message(
            chat_id=message.chat.id,
            text="Нет занятых велосипедов для возврата.",
        )
        return

    item_main_menu = types.KeyboardButton("главное меню")
    markup.add(item_main_menu)

    msg = bot.send_message(
        chat_id=message.chat.id,
        text="Выберите номер велосипеда для возврата:",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_trade_free_input)

def process_trade_free_input(message: types.Message):
    if message.text == "главное меню":
        show_main_menu(message.chat.id)
        return

    global table, order_in_processing

    try:
        bike_number = int(message.text)
        bike = next((b for b in table if b['number'] == bike_number), None)

        if not bike:
            bot.send_message(message.chat.id, "Велосипед с таким номером не найден.")
            return trade_state_free(message)

        if bike['state'] != 'occupate':
            bot.send_message(message.chat.id, "Этот велосипед не находится в аренде.")
            return trade_state_free(message)

        # Обновляем состояние велика
        bike['state'] = 'free'
        bike['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        bike['date_to_end'] = 'свободен'

        # Удаляем из order_in_processing все заказы с этим великом
        # Найдём активный заказ до удаления
        active_order = next((o for o in order_in_processing if str(o['number_of_bike']) == str(bike_number)), None)

        if active_order:
            history.append({
                "user": active_order['user'],
                "tag": active_order['tag'],
                "number_of_bike": active_order['number_of_bike'],
                "batteries": active_order.get('batteries', "1"),
                "date_to_end": active_order['date_to_end'],
                "price_to_order": active_order['price'],
                "return_time": datetime.now().strftime("%Y-%m-%d %H:%M")
            })

            # Только теперь удаляем из order_in_processing
            order_in_processing[:] = [o for o in order_in_processing if str(o['number_of_bike']) != str(bike_number)]


        save_history()
        save_table()
        save_order_in_processing()

        bot.send_message(
            chat_id=message.chat.id,
            text=f"Велосипед №{bike_number} возвращён и удалён из работы."
        )

    except ValueError:
        bot.send_message(message.chat.id, "Ошибка: введите корректный номер.")
        trade_state_free(message)
        return

    show_main_menu(message.chat.id)    
    
def change_distanse(message: types.Message):
    """Запрашивает новый пробег для выбранного велосипеда"""
    try:
        bike_number = int(message.text) 
    except ValueError:
        bot.send_message(message.chat.id, "Ошибка: введите корректный номер велосипеда.")
        return

    if 1 <= bike_number <= len(table):
        bike = table[bike_number - 1]  

        msg = bot.send_message(
            chat_id=message.chat.id,
            text=f"Введите актуальный пробег для велосипеда №{bike_number} (текущий пробег: {bike['distance']} км):"
        )
        bot.register_next_step_handler(msg, process_new_distance, bike_number)
    else:
        bot.send_message(message.chat.id, "Велосипед с таким номером не найден.")
        show_main_menu(message.chat.id)

def process_new_distance(message: types.Message, bike_number: int):
    """Обрабатывает новый пробег и обновляет данные в таблице"""
    try:
        new_distance = int(message.text) 
    except ValueError:
        bot.send_message(message.chat.id, "Ошибка: введите корректное число для пробега.")
        return

    if 1 <= bike_number <= len(table):
        bike = table[bike_number - 1]
        bike['distance'] = new_distance  

        bike['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_table() 

        bot.send_message(
            chat_id=message.chat.id,
            text=f"Пробег для велосипеда №{bike_number} успешно обновлён на {new_distance} км."
        )
        show_main_menu(message.chat.id)
    else:
        bot.send_message(message.chat.id, "Ошибка: велосипед не найден.")
        show_main_menu(message.chat.id)

def delete_bike(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    for bike in table:
        if bike['state'] == 'free':
            item = types.KeyboardButton(str(bike['number']))
            markup.add(item)
    
    item_main_menu = types.KeyboardButton("главное меню")
    markup.add(item_main_menu)

    msg = bot.send_message(
        chat_id=message.chat.id,
        text="Выберите номер велосипеда для удаления (только свободные).",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_delete_input)

def process_delete_input(message: types.Message):
    if message.text.lower() == "главное меню":
        show_main_menu(message.chat.id)
        return

    try:
        bike_number = int(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "Введите корректный номер велосипеда.")
        delete_bike(message)
        return

    global table
    for bike in table:
        if bike['number'] == bike_number and bike['state'] == 'free':
            table = [b for b in table if b['number'] != bike_number]
            
            for idx, bike in enumerate(table):
                bike['number'] = idx + 1

            save_table()

            bot.send_message(
                message.chat.id,
                f"Велосипед №{bike_number} удалён из базы данных."
            )
            show_main_menu(message.chat.id)
            return

    bot.send_message(message.chat.id, "Велосипед с таким номером не найден или он занят.")
    delete_bike(message)

def show_queue(message: types.Message):
    if not queue:
        bot.send_message(
            chat_id=message.chat.id,
            text='очередь пуста'
        )
    else:
        for bike in queue:
            bot.send_message(
                chat_id=message.chat.id,
                text=f"номер: {bike['order_number']}\nвремя аренды: {bike['tern_to_rent']}\nколическто батарей: {bike['batteries']}\nимя заказчика: {bike['user']}\nтег: @{bike['tag']}\nвремя заявки: {bike['date']}\nконец аренды: {bike['date_to_end']}\nцена заказа:{bike['price_to_order']}"
        )
            
def show_order_in_processing(message: types.Message):
    if not order_in_processing:
        bot.send_message(
            chat_id=message.chat.id,
            text='нет великов в работе'
        )
    else:
        for order in order_in_processing:
            bot.send_message(
                chat_id=message.chat.id,
                text=f"номер: {order['number_of_bike']}\nпользователь: {order['user']}\nтег: @{order['tag']}\nвремя окончания: {order['date_to_end']}\nбатарей: {order.get('batteries', '1')}\nприбыль: {order['price']}"
            )

def show_history(message: types.Message):
    if not history:
        bot.send_message(
            chat_id=message.chat.id,
            text='пока пусто'
        )
    else:
        for order in history:
            bot.send_message(
                chat_id=message.chat.id,
                text=f"заказчик: {order['user']}\nтег @{order['tag']}\nномер велосипеда: {order['number_of_bike']}\nколичество батарей: {order['batteries']}\nвремя окончания аренды: {order['date_to_end']}\nвремя возврата: {order['return_time']}\nцена заказа: {order['price_to_order']}"
            )

@bot.message_handler(commands=["start"])
def start(message: types.Message):
    """Обработчик команды /start"""
    show_main_menu(message.chat.id)

@bot.message_handler(content_types=["text"])
def add(message: types.Message):
    if message.text == "добавить велик":
        ask_for_model(message)

    elif message.text == "удалить велик":
        delete_bike(message)

    elif message.text == "сдаем в аренду":
        trade_state(message)

    elif message.text == "показать актуальную информацию":
        show_table(message)

    elif message.text == "показать очередь":
        show_queue(message)

    elif message.text == "возвращение":
        trade_state_free(message)

    elif message.text == "показать велики в работе":
        show_order_in_processing(message)

    elif message.text == "показать историю заказов":
        show_history(message)

    elif message.text == "главное меню":
        show_main_menu(message.chat.id)


# Укажи ID пользователя, которому отправлять уведомления
# работает только в ирл
ADMIN_CHAT_ID = 1320878937  # заменишь на свой chat_id

def hash_data(data):
    """Создает хеш от данных для отслеживания изменений"""
    return hashlib.md5(json.dumps(data, sort_keys=True).encode('utf-8')).hexdigest()
def monitor_queue_file():
    global queue
    last_hash = hash_data(queue)
    last_len = len(queue)

    while True:
        time.sleep(5)

        try:
            current_queue = get_file("queue.json")
            current_hash = hash_data(current_queue)
            current_len = len(current_queue)

            if current_hash != last_hash:
                if current_len > last_len:
                    bot.send_message(
                        chat_id=ADMIN_CHAT_ID,
                        text="🔔 Добавлена новая заявка в очередь!"
                    )

                queue[:] = current_queue
                last_hash = current_hash
                last_len = current_len

        except Exception as e:
            print(f"[monitor_queue_file] Ошибка обработки: {e}")

if __name__ == "__main__":
    threading.Thread(target=monitor_queue_file, daemon=True).start()
    bot.polling(none_stop=True)
