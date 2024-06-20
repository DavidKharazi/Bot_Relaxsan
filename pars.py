import requests
import zipfile
import os
import xml.etree.ElementTree as ET

# Функция для скачивания файла с Яндекс.Диска по публичному URL
def download_file_from_yandex_disk(public_url, local_filename):
    base_url = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
    response = requests.get(base_url, params={'public_key': public_url})
    download_url = response.json().get('href')
    if not download_url:
        raise Exception("Не удалось получить ссылку на скачивание")
    with requests.get(download_url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

# Функция для распаковки zip-файла
def unzip_file(zip_filepath, extract_to):
    with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"Файлы распакованы в директорию: {extract_to}")
    print(f"Список файлов: {os.listdir(extract_to)}")

# Функция для поиска файла в директории и поддиректориях
def find_file_in_directory(directory, filename):
    for root, dirs, files in os.walk(directory):
        if filename in files:
            return os.path.join(root, filename)
    return None

# Функция для экранирования кавычек внутри строк
def escape_quotes(value):
    return value.replace('"', '\\"')

# Функция для парсинга XML-файла и извлечения данных
def parse_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Словарь для хранения информации о складах
    warehouses = {}
    for warehouse in root.findall('.//Склад'):
        warehouse_id = warehouse.find('Ид').text
        warehouse_name = warehouse.find('Наименование').text
        warehouses[warehouse_id] = warehouse_name

    products = []
    for item in root.findall('.//Товар'):
        product = {
            "id": item.find('Ид').text if item.find('Ид') is not None else "",
            "name": item.find('Наименование').text if item.find('Наименование') is not None else "",
            "article": item.find('Артикул').text if item.find('Артикул') is not None else "",
            "color": item.find('Цвет').text if item.find('Цвет') is not None else "",
            "size": item.find('Размер').text if item.find('Размер') is not None else "",
            "compression_class": item.find('КлассКомпрессии').text if item.find('КлассКомпрессии') is not None else "",
            "country": item.find('СтранаПроизводитель').text if item.find('СтранаПроизводитель') is not None else "",
            "manufacturer": item.find('Производитель').text if item.find('Производитель') is not None else "",
            "price": float(item.find('Цена').text) if item.find('Цена') is not None else 0.0,
            "stock": {}
        }

        # Обработка остатков
        for stock in item.findall('.//Остаток'):
            stock_id = stock.find('ИдСклада').text if stock.find('ИдСклада') is not None else ""
            quantity = int(stock.find('Количество').text) if stock.find('Количество') is not None else 0
            warehouse_name = warehouses.get(stock_id, "Неизвестный склад")
            product["stock"][warehouse_name] = quantity

        # Экранирование кавычек внутри строк
        for key, value in product.items():
            if isinstance(value, str):
                product[key] = escape_quotes(value)

        products.append(product)

    return products

# Функция для записи данных в Python файл в указанном формате
def write_to_file(data, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("products = [\n")
        for product in data:
            f.write("    {\n")
            f.write(f'        "id": "{product["id"]}",\n')
            f.write(f'        "name": "{product["name"]}",\n')
            f.write(f'        "article": "{product["article"]}",\n')
            f.write(f'        "color": "{product["color"]}",\n')
            f.write(f'        "size": "{product["size"]}",\n')
            f.write(f'        "compression_class": "{product["compression_class"]}",\n')
            f.write(f'        "country": "{product["country"]}",\n')
            f.write(f'        "manufacturer": "{product["manufacturer"]}",\n')
            f.write(f'        "price": {product["price"]},\n')
            f.write('        "stock": {\n')
            for stock_key, stock_value in product["stock"].items():
                f.write(f'            "{stock_key}": {stock_value},\n')
            f.write("        }\n")
            f.write("    },\n")
        f.write("]\n")

# Основная часть скрипта
if __name__ == "__main__":
    # URL общего доступа к файлу на Яндекс.Диске
    yandex_disk_url = "https://disk.yandex.ru/d/t_m-lxPlt314FA"
    local_zip_file = os.path.join("files", "import.zip")
    extract_to = os.path.join("files", "extracted_files")
    local_xml_file = "import.xml"
    output_file = os.path.join("files", "products.py")

    # Создаем директорию для файлов, если она не существует
    os.makedirs("files", exist_ok=True)

    # Скачиваем файл
    download_file_from_yandex_disk(yandex_disk_url, local_zip_file)

    # Распаковываем zip-файл
    unzip_file(local_zip_file, extract_to)

    # Поиск файла import.xml в распакованной директории
    xml_file_path = find_file_in_directory(extract_to, local_xml_file)
    if not xml_file_path:
        print(f"Файл {local_xml_file} не найден. Проверьте распакованные файлы.")
        exit(1)

    # Парсим XML-файл и записываем данные
    data = parse_xml(xml_file_path)
    write_to_file(data, output_file)

    print(f"Данные успешно записаны в файл {output_file}")
