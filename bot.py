
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from difflib import SequenceMatcher
import aiohttp
import subprocess

from files.products import products

BITRIX24_WEBHOOK_URL = 'my_webhook_url'


# Устанавливаем уровень логирования
logging.basicConfig(level=logging.INFO)

# Токен вашего Telegram-бота
BOT_TOKEN = 'my_bot_token'

# Инициализируем бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Функция автопарсинга
async def run_parsing_script_periodically():
    while True:
        try:
            subprocess.run(['python', 'pars.py'])
            logging.info("Pars.py script executed successfully.")
        except Exception as e:
            logging.error(f"Error running pars.py script: {e}")
        await asyncio.sleep(4000)  # задаем ожидание парсинга в секундах

# Настройка OpenAI
llm = ChatOpenAI(model="gpt-4", temperature=0, api_key="my_api_key")

# Хранение последнего упомянутого товара для каждого пользователя
user_last_product = {}

class GetProduct(BaseModel):
    name: str = Field('', description="which product the user has in mind, e.g. есть гольфы")
    color: str = Field('', description="what color the user has in mind, e.g. черный")
    size: str = Field('', description="what size the user has in mind, e.g. 4")
    compression_class: str = Field('', description="what compression class the user has in mind, for example, e.g. компрессия 22 - 27 мм")
    country: str = Field('', description="which country of manufacture the user is referring to, e.g. строана производитель Чехия")
    manufacturer: str = Field('', description="which manufacturer the user has in mind, e.g. фирма Calze")
    price: str = Field('', description="what price the user has in mind, e.g. цена 50р.")
    greeting: str = Field('', description="there is a greeting in the user proposal, e.g. здравствуйте.")
    contacts: str = Field('', description="The user is interested in contacts, e.g. позвонить.")
    thank: str = Field('', description="The user would like to thank, e.g. спасибо.")
    advice: str = Field('', description="User asks for advice, e.g. что посоветуете.")
    interest: str = Field('', description="The user is interested in how the product can be purchased, e.g. способ купить.")
    place: str = Field('', description="User is ready to place an order for the product, e.g. оставлю заявку, куплю.")
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

def find_products_by_keywords(name=None, color=None, size=None, compression_class=None, country=None, manufacturer=None, price=None):
    matches = []
    for product in products:
        # Проверяем каждый параметр и фильтруем соответствующие товары

        if name and not is_similar_name(name, product["name"]):
            continue

        if color and not is_similar_color(color, product["color"]):
            continue

        if size and size != product["size"]:
            continue

        if compression_class and compression_class.lower() != product["compression_class"].lower():
            continue

        if country and not is_similar_country(country, product["country"]):
            continue

        if manufacturer and not is_similar_manufacturer(manufacturer, product["manufacturer"]):
            continue

        if price:
            try:
                price_float = float(price)  # Преобразуем строку price в число
                if price_float >= float(product["price"]):
                    continue
            except ValueError:
                logging.warning(f"Invalid price format: {price}")

        matches.append(product)

    return matches


# Функция для формирования ответа с данными о товаре
def format_product_info(product):
    # Находим первое вхождение запятой
    index = product['name'].find(",")

    # Если запятая найдена, обрезаем строку до этого места и удаляем пробелы в конце строки
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


# Функция для отправки сообщений с учетом ограничения длины текста
async def send_long_message(chat_id, text):
    chunk_size = 4096
    for i in range(0, len(text), chunk_size):
        await bot.send_message(chat_id, text[i:i + chunk_size])


user_states = {}

@dp.message(Command(commands=['start']))
async def send_welcome(message: Message):
    user_states[message.from_user.id] = "idle"
    await message.reply(
        "Привет! Введите запрос о товаре, указав название, цвет, размер, класс компрессии, страну, производителя и цену (например, 'гольфы, синий, 1, I, Россия, Calze, 50').")


async def send_to_bitrix24(chat_id, lead_data):
    params = {
        'fields': {
            'TITLE': f"Заявка от клиента: {lead_data.get('last_name', '')} {lead_data.get('first_name', '')} {lead_data.get('middle_name', '')}",
            'NAME': lead_data.get('first_name', ''),
            'LAST_NAME': lead_data.get('last_name', ''),
            'SECOND_NAME': lead_data.get('middle_name', ''),
            'PHONE': [{'VALUE': lead_data.get('phone', ''), 'VALUE_TYPE': 'WORK'}],
            'CITY': lead_data.get('city', ''),
            'COMMENTS': f"ФИО: {lead_data.get('last_name', '')} {lead_data.get('first_name', '')} {lead_data.get('middle_name', '')}\nНазвание товара: {lead_data.get('product_name', '')}"
                        f"\nЦвет товара: {lead_data.get('product_color', '')}\nРазмер товара: {lead_data.get('product_size', '')}"
                        f"\nТелефон: {lead_data.get('phone', '')}\nГород: {lead_data.get('city', '')}"
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(BITRIX24_WEBHOOK_URL, json=params) as resp:
            if resp.status == 200:
                await bot.send_message(chat_id, "Ваша заявка успешно отправлена!")
            else:
                await bot.send_message(chat_id, "Произошла ошибка при отправке заявки. Пожалуйста, попробуйте позже.")


@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_text = message.text.lower()

    # Получаем текущее состояние пользователя
    user_state = user_states.get(user_id, "idle")


    if user_state == "place_order":
        ai_msg = llm_with_tools.invoke(user_text)
        tool_calls = ai_msg.tool_calls


        if tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
            args = tool_calls[0].get('args', {})
            cancel = args.get('cancel', '')
            # Проверка на команду отмены
            if cancel != "":
                user_states[user_id] = "idle"
                await send_long_message(message.chat.id,
                                        "Отмена оформления заказа. Вы можете продолжить поиск товаров.")
                return

        if tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
            args = tool_calls[0].get('args', {})
            fsl = args.get('fsl', '')
            phone = args.get('phone', '')
            city = args.get('city', '')
            name = args.get('name', '')
            color = args.get('color', '')
            size = args.get('size', '')

            if fsl != "" and phone != "" and city != "" and name != "" and color != "" and size != "":
                # Формируем данные для отправки в Битрикс24
                lead_data = {
                    'first_name': fsl.split()[1],
                    'last_name': fsl.split()[0],
                    'middle_name': fsl.split()[2] if len(fsl.split()) > 2 else '',
                    'phone': phone,
                    'city': city,
                    'product_name': name,
                    'product_color': color,
                    'product_size': size
                }

                # Отправляем данные в Битрикс24
                await send_to_bitrix24(message.chat.id, lead_data)

                # Сбрасываем состояние пользователя
                user_states[user_id] = "idle"
                return
            else:
                # Отправляем сообщение о том, что не все данные были предоставлены
                await send_long_message(message.chat.id,
                                        "Не удалось собрать все необходимые данные для оформления заказа.\n"
                                        "Пожалуйста, укажите недостающие данные:\n"
                                        "- ФИО\n"
                                        "- Телефон\n"
                                        "- Город\n"
                                        "- Наименование товара\n"
                                        "- Цвет товара\n"
                                        "- Размер товара")
                return

    else:
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
            size = args.get('size', '')
            compression_class = args.get('compression_class', '')
            country = args.get('country', '')
            manufacturer = args.get('manufacturer', '')
            price = args.get('price', '')
            greeting = args.get('greeting', '')
            contacts = args.get('contacts', '')
            thank = args.get('thank', '')
            advice = args.get('advice', '')
            interest = args.get('interest', '')
            place = args.get('place', '')

            if place != "":
                await send_long_message(message.chat.id,
                                        "Для оформления заказа, пожалуйста напишите:\n- Наименование товара, размер, цвет."
                                        "\n- Ваши ФИО, телефон и город.")
                # Устанавливаем состояние пользователя в "place_order"
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
                return

            if interest != "":
                await send_long_message(message.chat.id,
                                        "Чтобы приобрести товар, Вы можете оставить заявку на него. Для этого потребуются:\nФИО, телефон и город проживания.")
                return

            if advice != "" and name == "":
                await send_long_message(message.chat.id,
                                        "Мы рады предложить Вам широкий ассортимент качественных, комфортных и практичных ортопедических изделий от ведущих мировых производителей. В нашем салоне также в наличии — корректирующее белье, обувь и стельки, корректоры осанки и многое другое. Все товары, которые можно приобрести в ортопедическом салоне, отличаются высокой надежностью, превосходно зарекомендовали себя в эксплуатации и пользуются неизменно высоким спросом среди покупателей. Ортопедические изделия будут полезны тем, кто проходит реабилитацию после травм и операций, страдает от болевого синдрома или просто заботится о своем здоровье. При формировании ассортимента салона мы учитываем мнение ведущих врачей-ортопедов, неврологов, сосудистых хирургов и в случае необходимости консультируемся с ними. Поэтому Вы можете быть уверены, что все представленные изделия в ортопедическом магазине соответствуют самым жестким медицинским стандартам качества.")
                return

            if thank != "":
                await send_long_message(message.chat.id,
                                        "Благодарим Вас за обращение!\nНапишите, если Вас интересуют еще какие-то вопросы.")
                return

            if contacts != "":
                await send_long_message(message.chat.id,
                                        "Вы можете позвонить нашим менеджерам по телефону +375 (29) 5629049\nТак же предоставляем наши адреса магазинов:"
                                        "\nМинск, пр-т Мира, 1, пом.1058 (вход со стороны двора)"
                                        "\nМинск, ул. Петра Мстиславца 2"
                                        "\nМинск, ул.Притыцкого, 29, ТЦ Тивали пав. 355, 3 этаж (ст. м. Спортивная).")
                return

            if greeting != "":
                await send_long_message(message.chat.id,
                                        "Здравствуйте! Мы рады видеть вас в компании Relaxsan.\nНапишите, какой товар вас интересует.")
                return

            if name != last_product['name']:
                size = ''
                color = ''

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
                response = f"Вот что мне удалось найти по Вашему запросу:\n\n" + "\n\n".join([format_product_info(product) for product in matches[:3]])
                if len(matches) > 3:
                    response += f"\n\nНайдено более 3 товаров. Пожалуйста, уточните ваш запрос, чтобы увидеть остальные."
            else:
                response = "Товары не найдены. Пожалуйста, уточните ваш запрос."
        else:
            response = "Не удалось распознать запрос. Пожалуйста, укажите название, цвет и размер."

        await send_long_message(message.chat.id, response)


async def main():
    # Запускаем парсинг при старте
    asyncio.create_task(run_parsing_script_periodically())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())


