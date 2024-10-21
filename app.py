# import asyncio
# import logging
# import uvicorn
# from langchain_openai import ChatOpenAI
# from langchain_core.pydantic_v1 import BaseModel, Field
# from difflib import SequenceMatcher
# import aiohttp
# import subprocess
# from files.products import products
# from fastapi import FastAPI, Request
#
# BITRIX24_WEBHOOK_URL = 'https://b24-gzxsfy.bitrix24.by/rest/1/eaq0l1mucp7xjm3o/crm.lead.add.json'
#
# # Устанавливаем уровень логирования
# logging.basicConfig(level=logging.INFO)
#
# app = FastAPI()
#
# # Настройка OpenAI
# llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, base_url='https://api.vsegpt.ru/v1', api_key='sk-or-vv-4fd1b5093c0c0441ac93ede59ee8ef136400a20e71e4ca65dec345ba468ce8ce')
#
# user_states = {}
# leads = {}
# user_last_product = {}
#
# # Функция для запуска скрипта pars.py периодически
# async def run_parsing_script_periodically():
#     while True:
#         try:
#             subprocess.run(['python', 'pars.py'])
#             logging.info("Pars.py script executed successfully.")
#         except Exception as e:
#             logging.error(f"Error running pars.py script: {e}")
#         await asyncio.sleep(4000)  # задаем ожидание парсинга в секундах
#
#
# class GetProduct(BaseModel):
#     name: str = Field('', description="which product the user has in mind, e.g. есть гольфы, колготки")
#     color: str = Field('', description="what color the user has in mind, e.g. черный")
#     size: str = Field('', description="what size the user has in mind, e.g. 4")
#     compression_class: str = Field('', description="If the user specifies compression 1, write in a value of I. If the user specifies compression 2, write in value II. In other cases any other values. e.g. компрессия 22 - 27 мм")
#     country: str = Field('', description="which country of manufacture the user is referring to, e.g. строана производитель Чехия")
#     manufacturer: str = Field('', description="which manufacturer the user has in mind, e.g. фирма Calze")
#     price: str = Field('', description="what price the user has in mind. Write in the meaning of the number only, e.g. цена 50.")
#     greeting: str = Field('', description="recognize the user's sentence as a greeting, e.g. здравствуйте/привет/добрый день.")
#     contacts: str = Field('', description="The user is interested in contacts, e.g. позвонить.")
#     thank: str = Field('', description="The user would like to thank, e.g. спасибо.")
#     advice: str = Field('', description="User asks for advice, e.g. что посоветуете.")
#     interest: str = Field('', description="The user is interested in how the product can be purchased, e.g. способ купить, как приобрести, как сделать заказ. как оформить заявку")
#     place: str = Field('', description="understand intuitively that the user wants to buy the product, e.g. готов купить, хочу купить, хорошо оставлю заявку, давайте оформим")
#     fsl: str = Field('', description="User wrote his/her Surname First Name Second Name, e.g. Иванов Сергей Андреевич.")
#     phone: str = Field('', description="The user wrote his phone number, e.g. +375257903263.")
#     city: str = Field('', description="The user wrote his city, e.g. Минск.")
#     cancel: str = Field('', description="User wants to cancel data collection, e.g. Отмена/Не сейчас.")
#
#
# llm_with_tools = llm.bind_tools([GetProduct])
#
# def is_similar_name(keyword, product_name):
#     if keyword.lower() in product_name.lower():
#         return True
#     matcher = SequenceMatcher(None, keyword.lower(), product_name.lower())
#     return matcher.ratio() > 0.5
#
# def is_similar_color(keyword, product_color):
#     if keyword.lower() == product_color.lower():
#         return True
#     matcher = SequenceMatcher(None, keyword.lower(), product_color.lower())
#     return matcher.ratio() > 0.7
#
# def is_similar_manufacturer(keyword, product_manufacturer):
#     if keyword.lower() == product_manufacturer.lower():
#         return True
#     matcher = SequenceMatcher(None, keyword.lower(), product_manufacturer.lower())
#     return matcher.ratio() > 0.5
#
# def is_similar_country(keyword, product_country):
#     if keyword.lower() == product_country.lower():
#         return True
#     matcher = SequenceMatcher(None, keyword.lower(), product_country.lower())
#     return matcher.ratio() > 0.5
#
# def is_similar_compression(keyword, compression_class):
#     if keyword.lower() == compression_class.lower()[:2] or keyword.lower() == compression_class.lower()[3::]:
#         return True
#     matcher = SequenceMatcher(None, keyword.lower(), compression_class.lower())
#     return matcher.ratio() > 0.8
#
# def find_products_by_keywords(name=None, color=None, size=None, compression_class=None, country=None, manufacturer=None, price=None):
#     matches = []
#     for product in products:
#         if name and not is_similar_name(name, product["name"]):
#             continue
#         if color and not is_similar_color(color, product["color"]):
#             continue
#         if size and size != product["size"]:
#             continue
#         if compression_class and not is_similar_compression(compression_class, product["compression_class"]):
#             continue
#         if country and not is_similar_country(country, product["country"]):
#             continue
#         if manufacturer and not is_similar_manufacturer(manufacturer, product["manufacturer"]):
#             continue
#         if price:
#             try:
#                 price_float = float(price)
#                 lower_bound = price_float - 3
#                 upper_bound = price_float + 3
#                 if not (lower_bound <= float(product["price"]) <= upper_bound):
#                     continue
#             except ValueError:
#                 logging.warning(f"Invalid price format: {price}")
#                 continue
#         matches.append(product)
#     return matches
#
# def format_product_info(product):
#     index = product['name'].find(",")
#     if index != -1:
#         name = product['name'][:index].rstrip()
#     else:
#         name = product['name']
#
#     stock_info = "\n".join([f"Магазин \"{store}\": {quantity} единиц" for store, quantity in product['stock'].items()])
#     return (
#         f"Наименование: {name}\n"
#         f"Цена: {product['price']} BYN\n"
#         f"Размер: {product['size']}\n"
#         f"Компрессия: {product['compression_class']}\n"
#         f"Цвет: {product['color']}\n"
#         f"Магазины, где можно приобрести:\n{stock_info}"
#     )
#
# async def send_to_bitrix24(chat_id, lead_data):
#     params = {
#         'fields': {
#             'TITLE': f"Заявка от клиента: {lead_data.get('last_name', '')} {lead_data.get('first_name', '')} {lead_data.get('middle_name', '')}",
#             'NAME': lead_data.get('first_name', ''),
#             'LAST_NAME': lead_data.get('last_name', ''),
#             'SECOND_NAME': lead_data.get('middle_name', ''),
#             'PHONE': [{'VALUE': lead_data.get('phone', ''), 'VALUE_TYPE': 'WORK'}],
#             'CITY': lead_data.get('city', ''),
#             'COMMENTS': f"ФИО: {lead_data.get('last_name', '')} {lead_data.get('first_name', '')} {lead_data.get('middle_name', '')}\nНазвание товара: {lead_data.get('name', '')}"
#                         f"\nЦвет товара: {lead_data.get('color', '')}\nРазмер товара: {lead_data.get('size', '')}"
#                         f"\nТелефон: {lead_data.get('phone', '')}\nГород: {lead_data.get('city', '')}"
#         }
#     }
#
#     async with aiohttp.ClientSession() as session:
#         async with session.post(BITRIX24_WEBHOOK_URL, json=params) as resp:
#             if resp.status == 200:
#                 return {"status": "success", "message": "Ваша заявка успешно отправлена!"}
#             else:
#                 return {"status": "error", "message": "Произошла ошибка при отправке заявки. Пожалуйста, попробуйте позже."}
#
# # Маршрут обработки запросов
# @app.post("/process")
# async def process_request(request: Request):
#     data = await request.json()
#     user_id = data.get('user_id')
#     user_text = data.get('text').lower()
#
#     user_state = user_states.get(user_id, "idle")
#
#     if user_state == "place_order":
#         ai_msg = llm_with_tools.invoke(user_text)
#         tool_calls = ai_msg.tool_calls
#
#         if tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
#             args = tool_calls[0].get('args', {})
#             cancel = args.get('cancel', '')
#             if cancel != "":
#                 user_states[user_id] = "idle"
#                 return {"message": "Отмена оформления заказа. Вы можете продолжить поиск товаров."}
#
#         if tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
#             args = tool_calls[0].get('args', {})
#             fsl = args.get('fsl', '')
#             phone = args.get('phone', '')
#             city = args.get('city', '')
#             cancel = args.get('cancel', '')
#             name = args.get('name', '')
#             color = args.get('color', '')
#             size = args.get('size', '')
#
#             if cancel != "":
#                 user_states[user_id] = "idle"
#                 return {"message": "Отмена оформления заказа. Вы можете продолжить поиск товаров."}
#
#             if 'last_name' not in leads[user_id] or 'first_name' not in leads[user_id] or 'middle_name' not in leads[
#                 user_id]:
#                 if fsl != "" and len(fsl.split()) == 3:
#                     last_name, first_name, middle_name = fsl.split()
#                     leads[user_id]['last_name'] = last_name.capitalize()
#                     leads[user_id]['first_name'] = first_name.capitalize()
#                     leads[user_id]['middle_name'] = middle_name.capitalize()
#                     return {"message": "Пожалуйста, укажите ваш номер телефона и город."}
#                 else:
#                     return {"message": "Недостающие данные, введите ваше ФИО"}
#
#                 # Проверка и обработка телефона и города
#             if 'phone' not in leads[user_id] or 'city' not in leads[user_id]:
#                 if phone != "" and city != "":
#                     leads[user_id]['phone'] = phone
#                     leads[user_id]['city'] = city.capitalize()
#                     return {"message": "Укажите, пожалуйста, товар, который Вы выбрали\nЦвет и размер."}
#                 else:
#                     return {"message": "Недостающие данные, укажите ваш телефон и город"}
#
#                 # Проверка и обработка товара, цвета и размера
#             if 'name' not in leads[user_id] or 'color' not in leads[user_id] or 'size' not in leads[user_id]:
#                 if name != "" and color != "" and size != "":
#                     leads[user_id]['name'] = name.capitalize()
#                     leads[user_id]['color'] = color.capitalize()
#                     leads[user_id]['size'] = size.capitalize()
#                     bitrix_response = await send_to_bitrix24(user_id, leads[user_id])
#                     user_states[user_id] = "idle"
#                     return {"message": bitrix_response['message']}
#                 else:
#                     return {"message": "Недостающие данные, укажите товар, цвет и размер"}
#
#             return {"message": "Все данные уже заполнены"}
#
#
#     ai_msg = llm_with_tools.invoke(user_text)
#     tool_calls = ai_msg.tool_calls
#
#     logging.info(f"User text: {user_text}")
#     logging.info(f"Tool calls: {tool_calls}")
#
#     last_product = user_last_product.get(user_id, {
#         'name': '',
#         'color': '',
#         'size': '',
#         'compression_class': '',
#         'country': '',
#         'manufacturer': '',
#         'price': ''
#     })
#
#     if tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
#         args = tool_calls[0].get('args', {})
#         name = args.get('name', last_product['name'])
#         color = args.get('color', last_product['color'])
#         size = args.get('size', last_product['size'])
#         compression_class = args.get('compression_class', '')
#         country = args.get('country', '')
#         manufacturer = args.get('manufacturer', '')
#         price = args.get('price', last_product['price'])
#         greeting = args.get('greeting', '')
#         contacts = args.get('contacts', '')
#         thank = args.get('thank', '')
#         advice = args.get('advice', '')
#         interest = args.get('interest', '')
#         place = args.get('place', '')
#         fsl = args.get('fsl', '')
#         phone = args.get('phone', '')
#         city = args.get('city', '')
#         cancel = args.get('cancel', '')
#
#         if cancel != "":
#             user_states[user_id] = "idle"
#             return {"message": "Запрос отменен. Вы можете продолжить поиск товаров."}
#
#         if greeting != "":
#             return {"message": "Здравствуйте! Вы можете выбрать товар, напишите, что вас интересует?"}
#
#         if contacts != "":
#             user_last_product[user_id] = {
#                 'name': '',
#                 'color': '',
#                 'size': '',
#                 'compression_class': '',
#                 'country': '',
#                 'manufacturer': '',
#                 'price': ''
#             }
#             return {"message": "Вы можете связаться с нами по телефону +375257903263."}
#
#         if thank != "":
#             user_last_product[user_id] = {
#                 'name': '',
#                 'color': '',
#                 'size': '',
#                 'compression_class': '',
#                 'country': '',
#                 'manufacturer': '',
#                 'price': ''
#             }
#             return {"message": "Пожалуйста! Рад был помочь."}
#
#         if advice != "":
#             user_last_product[user_id] = {
#                 'name': '',
#                 'color': '',
#                 'size': '',
#                 'compression_class': '',
#                 'country': '',
#                 'manufacturer': '',
#                 'price': ''
#             }
#             return {"message": "У нас большой ассортимент товаров. Пожалуйста, уточните, что именно вы ищете."}
#
#         if interest != "":
#             return {"message": "Вы можете сделать заказ, предоставив мне свои контактные данные. Пожалуйста, напишите 'оформим заявку', если вы готовы продолжить."}
#
#         if place != "":
#             user_states[user_id] = "place_order"
#             user_last_product[user_id] = {
#                 'name': '',
#                 'color': '',
#                 'size': '',
#                 'compression_class': '',
#                 'country': '',
#                 'manufacturer': '',
#                 'price': ''
#             }
#             leads[user_id] = {}
#
#             return {"message": "Пожалуйста, предоставьте ваше ФИО."}
#
#
#
#         if last_product['name'] != '' and name != last_product['name']:
#             size = args['size'] if 'size' in args and args['size'] != '' else None
#             color = args['color'] if 'color' in args and args['color'] != '' else None
#             compression_class = args['compression_class'] if 'compression_class' in args and args[
#                 'compression_class'] != '' else None
#             price = args['price'] if 'price' in args and args['price'] != '' else None
#             country = ''
#             manufacturer = ''
#             print(f"last_product['name']: {args}, {sum(1 for value in args.values() if value)}")
#             print(f"last_product: {last_product}")
#
#         user_last_product[user_id] = {
#             'name': name,
#             'color': color,
#             'size': size,
#             'compression_class': compression_class,
#             'country': country,
#             'manufacturer': manufacturer,
#             'price': price
#         }
#
#         product_data = user_last_product[user_id]
#
#         matches = find_products_by_keywords(
#             name=product_data['name'],
#             color=product_data['color'],
#             size=product_data['size'],
#             compression_class=product_data['compression_class'],
#             country=product_data['country'],
#             manufacturer=product_data['manufacturer'],
#             price=product_data['price']
#         )
#
#         if matches:
#             response = f"Вот что мне удалось найти по вашему запросу:\n\n" + "\n\n".join([format_product_info(product) for product in matches[:3]])
#             if len(matches) > 3:
#                 response += "\n\nЯ нашел больше товаров, чем вы запросили. Пожалуйста, уточните детали, чтобы показать все соответствующие."
#             return {"message": response}
#         else:
#             return {"message": "Товары не найдены. Пожалуйста, уточните ваш запрос."}
#
#     return {"message": "Извините, я не могу помочь с вашим запросом. Пожалуйста, попробуйте снова."}
#
#
# def start():
#     loop = asyncio.get_event_loop()
#     loop.create_task(run_parsing_script_periodically())
#     config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
#     server = uvicorn.Server(config)
#     loop.run_until_complete(server.serve())
#
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     start()
#
#





import asyncio
import logging
import uvicorn
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from difflib import SequenceMatcher
import aiohttp
import subprocess
from files.products import products
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request

BITRIX24_WEBHOOK_URL = 'https://b24-gzxsfy.bitrix24.by/rest/1/eaq0l1mucp7xjm3o/crm.lead.add.json'

# Устанавливаем уровень логирования
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Настройка OpenAI
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key='my_api')

user_states = {}
leads = {}
user_last_product = {}

# Функция для запуска скрипта pars.py периодически
async def run_parsing_script_periodically():
    while True:
        try:
            subprocess.run(['python', 'pars.py'])
            logging.info("Pars.py script executed successfully.")
        except Exception as e:
            logging.error(f"Error running pars.py script: {e}")
        await asyncio.sleep(4000)  # задаем ожидание парсинга в секундах


class GetProduct(BaseModel):
    name: str = Field('', description="which product the user has in mind, e.g. есть гольфы, колготки")
    color: str = Field('', description="what color the user has in mind, e.g. черный")
    size: str = Field('', description="what size the user has in mind, e.g. 4")
    compression_class: str = Field('', description="If the user specifies compression 1, write in a value of I. If the user specifies compression 2, write in value II. In other cases any other values. e.g. компрессия 22 - 27 мм")
    country: str = Field('', description="which country of manufacture the user is referring to, e.g. строана производитель Чехия")
    manufacturer: str = Field('', description="which manufacturer the user has in mind, e.g. фирма Calze")
    price: str = Field('', description="what price the user has in mind. Write in the meaning of the number only, e.g. цена 50.")
    greeting: str = Field('', description="recognize the user's sentence as a greeting, e.g. здравствуйте/привет/добрый день.")
    contacts: str = Field('', description="The user is interested in contacts, e.g. позвонить.")
    thank: str = Field('', description="The user would like to thank, e.g. спасибо.")
    advice: str = Field('', description="User asks for advice, e.g. что посоветуете.")
    interest: str = Field('', description="The user is interested in how the product can be purchased, e.g. способ купить, как приобрести, как сделать заказ. как оформить заявку")
    place: str = Field('', description="understand intuitively that the user wants to buy the product, e.g. готов купить, хочу купить, хорошо оставлю заявку, давайте оформим")
    fsl: str = Field('', description="User wrote his/her Surname First Name Second Name, e.g. Иванов Сергей Андреевич.")
    phone: str = Field('', description="The user wrote his phone number, e.g. +375257903263.")
    city: str = Field('', description="The user wrote his city, e.g. Минск.")
    cancel: str = Field('', description="User wants to cancel data collection, e.g. Отмена/Не сейчас.")


llm_with_tools = llm.bind_tools([GetProduct])

def is_similar_name(keyword, product_name):
    if keyword.lower() in product_name.lower():
        return True
    matcher = SequenceMatcher(None, keyword.lower(), product_name.lower())
    return matcher.ratio() > 0.5

def is_similar_color(keyword, product_color):
    if keyword.lower() == product_color.lower():
        return True
    matcher = SequenceMatcher(None, keyword.lower(), product_color.lower())
    return matcher.ratio() > 0.7

def is_similar_manufacturer(keyword, product_manufacturer):
    if keyword.lower() == product_manufacturer.lower():
        return True
    matcher = SequenceMatcher(None, keyword.lower(), product_manufacturer.lower())
    return matcher.ratio() > 0.5

def is_similar_country(keyword, product_country):
    if keyword.lower() == product_country.lower():
        return True
    matcher = SequenceMatcher(None, keyword.lower(), product_country.lower())
    return matcher.ratio() > 0.5

def is_similar_compression(keyword, compression_class):
    if keyword.lower() == compression_class.lower()[:2] or keyword.lower() == compression_class.lower()[3::]:
        return True
    matcher = SequenceMatcher(None, keyword.lower(), compression_class.lower())
    return matcher.ratio() > 0.8

def find_products_by_keywords(name=None, color=None, size=None, compression_class=None, country=None, manufacturer=None, price=None):
    matches = []
    for product in products:
        if name and not is_similar_name(name, product["name"]):
            continue
        if color and not is_similar_color(color, product["color"]):
            continue
        if size and size != product["size"]:
            continue
        if compression_class and not is_similar_compression(compression_class, product["compression_class"]):
            continue
        if country and not is_similar_country(country, product["country"]):
            continue
        if manufacturer and not is_similar_manufacturer(manufacturer, product["manufacturer"]):
            continue
        if price:
            try:
                price_float = float(price)
                lower_bound = price_float - 3
                upper_bound = price_float + 3
                if not (lower_bound <= float(product["price"]) <= upper_bound):
                    continue
            except ValueError:
                logging.warning(f"Invalid price format: {price}")
                continue
        matches.append(product)
    return matches

def format_product_info(product):
    index = product['name'].find(",")
    if index != -1:
        name = product['name'][:index].rstrip()
    else:
        name = product['name']

    stock_info = "\n".join([f"Магазин \"{store}\": {quantity} единиц" for store, quantity in product['stock'].items()])
    return (
        f"Наименование: {name}\n"
        f"Цена: {product['price']} BYN\n"
        f"Размер: {product['size']}\n"
        f"Компрессия: {product['compression_class']}\n"
        f"Цвет: {product['color']}\n"
        f"Магазины, где можно приобрести:\n{stock_info}"
    )

async def send_to_bitrix24(chat_id, lead_data):
    params = {
        'fields': {
            'TITLE': f"Заявка от клиента: {lead_data.get('last_name', '')} {lead_data.get('first_name', '')} {lead_data.get('middle_name', '')}",
            'NAME': lead_data.get('first_name', ''),
            'LAST_NAME': lead_data.get('last_name', ''),
            'SECOND_NAME': lead_data.get('middle_name', ''),
            'PHONE': [{'VALUE': lead_data.get('phone', ''), 'VALUE_TYPE': 'WORK'}],
            'CITY': lead_data.get('city', ''),
            'COMMENTS': f"ФИО: {lead_data.get('last_name', '')} {lead_data.get('first_name', '')} {lead_data.get('middle_name', '')}\nНазвание товара: {lead_data.get('name', '')}"
                        f"\nЦвет товара: {lead_data.get('color', '')}\nРазмер товара: {lead_data.get('size', '')}"
                        f"\nТелефон: {lead_data.get('phone', '')}\nГород: {lead_data.get('city', '')}"
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(BITRIX24_WEBHOOK_URL, json=params) as resp:
            if resp.status == 200:
                return {"status": "success", "message": "Ваша заявка успешно отправлена!"}
            else:
                return {"status": "error", "message": "Произошла ошибка при отправке заявки. Пожалуйста, попробуйте позже."}

# Маршрут обработки запросов
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    try:
        while True:
            user_text = await websocket.receive_text()
            response = await process_message(user_id, user_text)
            await websocket.send_text(response["message"])
    except WebSocketDisconnect:
        logging.info(f"WebSocket connection closed for user {user_id}")

async def process_message(user_id: str, user_text: str):
    user_state = user_states.get(user_id, "idle")

    if user_state == "place_order":
        ai_msg = llm_with_tools.invoke(user_text)
        tool_calls = ai_msg.tool_calls

        if tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
            args = tool_calls[0].get('args', {})
            cancel = args.get('cancel', '')
            if cancel != "":
                user_states[user_id] = "idle"
                return {"message": "Отмена оформления заказа. Вы можете продолжить поиск товаров."}

        if tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
            args = tool_calls[0].get('args', {})
            fsl = args.get('fsl', '')
            phone = args.get('phone', '')
            city = args.get('city', '')
            cancel = args.get('cancel', '')
            name = args.get('name', '')
            color = args.get('color', '')
            size = args.get('size', '')

            if cancel != "":
                user_states[user_id] = "idle"
                return {"message": "Отмена оформления заказа. Вы можете продолжить поиск товаров."}

            if 'last_name' not in leads[user_id] or 'first_name' not in leads[user_id] or 'middle_name' not in leads[
                user_id]:
                if fsl != "" and len(fsl.split()) == 3:
                    last_name, first_name, middle_name = fsl.split()
                    leads[user_id]['last_name'] = last_name.capitalize()
                    leads[user_id]['first_name'] = first_name.capitalize()
                    leads[user_id]['middle_name'] = middle_name.capitalize()
                    return {"message": "Пожалуйста, укажите ваш номер телефона и город."}
                else:
                    return {"message": "Недостающие данные, введите ваше ФИО"}

                # Проверка и обработка телефона и города
            if 'phone' not in leads[user_id] or 'city' not in leads[user_id]:
                if phone != "" and city != "":
                    leads[user_id]['phone'] = phone
                    leads[user_id]['city'] = city.capitalize()
                    return {"message": "Укажите, пожалуйста, товар, который Вы выбрали\nЦвет и размер."}
                else:
                    return {"message": "Недостающие данные, укажите ваш телефон и город"}

                # Проверка и обработка товара, цвета и размера
            if 'name' not in leads[user_id] or 'color' not in leads[user_id] or 'size' not in leads[user_id]:
                if name != "" and color != "" and size != "":
                    leads[user_id]['name'] = name.capitalize()
                    leads[user_id]['color'] = color.capitalize()
                    leads[user_id]['size'] = size.capitalize()
                    bitrix_response = await send_to_bitrix24(user_id, leads[user_id])
                    user_states[user_id] = "idle"
                    return {"message": bitrix_response['message']}
                else:
                    return {"message": "Недостающие данные, укажите товар, цвет и размер"}

            return {"message": "Все данные уже заполнены"}


    ai_msg = llm_with_tools.invoke(user_text)
    tool_calls = ai_msg.tool_calls

    logging.info(f"User text: {user_text}")
    logging.info(f"Tool calls: {tool_calls}")

    last_product = user_last_product.get(user_id, {
        'name': '',
        'color': '',
        'size': '',
        'compression_class': '',
        'country': '',
        'manufacturer': '',
        'price': ''
    })

    if tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
        args = tool_calls[0].get('args', {})
        name = args.get('name', last_product['name'])
        color = args.get('color', last_product['color'])
        size = args.get('size', last_product['size'])
        compression_class = args.get('compression_class', '')
        country = args.get('country', '')
        manufacturer = args.get('manufacturer', '')
        price = args.get('price', last_product['price'])
        greeting = args.get('greeting', '')
        contacts = args.get('contacts', '')
        thank = args.get('thank', '')
        advice = args.get('advice', '')
        interest = args.get('interest', '')
        place = args.get('place', '')
        fsl = args.get('fsl', '')
        phone = args.get('phone', '')
        city = args.get('city', '')
        cancel = args.get('cancel', '')

        if cancel != "":
            user_states[user_id] = "idle"
            return {"message": "Запрос отменен. Вы можете продолжить поиск товаров."}

        if greeting != "":
            return {"message": "Здравствуйте! Вы можете выбрать товар, напишите, что вас интересует?"}

        if contacts != "":
            user_last_product[user_id] = {
                'name': '',
                'color': '',
                'size': '',
                'compression_class': '',
                'country': '',
                'manufacturer': '',
                'price': ''
            }
            return {"message": "Вы можете связаться с нами по телефону +375257903263."}

        if thank != "":
            user_last_product[user_id] = {
                'name': '',
                'color': '',
                'size': '',
                'compression_class': '',
                'country': '',
                'manufacturer': '',
                'price': ''
            }
            return {"message": "Пожалуйста! Рад был помочь."}

        if advice != "":
            user_last_product[user_id] = {
                'name': '',
                'color': '',
                'size': '',
                'compression_class': '',
                'country': '',
                'manufacturer': '',
                'price': ''
            }
            return {"message": "У нас большой ассортимент товаров. Пожалуйста, уточните, что именно вы ищете."}

        if interest != "":
            return {"message": "Вы можете сделать заказ, предоставив мне свои контактные данные. Пожалуйста, напишите 'оформим заявку', если вы готовы продолжить."}

        if place != "":
            user_states[user_id] = "place_order"
            user_last_product[user_id] = {
                'name': '',
                'color': '',
                'size': '',
                'compression_class': '',
                'country': '',
                'manufacturer': '',
                'price': ''
            }
            leads[user_id] = {}

            return {"message": "Пожалуйста, предоставьте ваше ФИО."}



        if last_product['name'] != '' and name != last_product['name']:
            size = args['size'] if 'size' in args and args['size'] != '' else None
            color = args['color'] if 'color' in args and args['color'] != '' else None
            compression_class = args['compression_class'] if 'compression_class' in args and args[
                'compression_class'] != '' else None
            price = args['price'] if 'price' in args and args['price'] != '' else None
            country = ''
            manufacturer = ''
            print(f"last_product['name']: {args}, {sum(1 for value in args.values() if value)}")
            print(f"last_product: {last_product}")

        user_last_product[user_id] = {
            'name': name,
            'color': color,
            'size': size,
            'compression_class': compression_class,
            'country': country,
            'manufacturer': manufacturer,
            'price': price
        }

        product_data = user_last_product[user_id]

        matches = find_products_by_keywords(
            name=product_data['name'],
            color=product_data['color'],
            size=product_data['size'],
            compression_class=product_data['compression_class'],
            country=product_data['country'],
            manufacturer=product_data['manufacturer'],
            price=product_data['price']
        )

        if matches:
            response = f"Вот что мне удалось найти по вашему запросу:\n\n" + "\n\n".join([format_product_info(product) for product in matches[:3]])
            if len(matches) > 3:
                response += "\n\nЯ нашел больше товаров, чем вы запросили. Пожалуйста, уточните детали, чтобы показать все соответствующие."
            return {"message": response}
        else:
            return {"message": "Товары не найдены. Пожалуйста, уточните ваш запрос."}

    return {"message": "Извините, я не могу помочь с вашим запросом. Пожалуйста, попробуйте снова."}




def start():
    loop = asyncio.get_event_loop()
    loop.create_task(run_parsing_script_periodically())
    config = uvicorn.Config(app, host="0.0.0.0", port=8111, log_level="info")
    server = uvicorn.Server(config)
    loop.run_until_complete(server.serve())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start()

