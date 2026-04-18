import asyncio
import os
import zipfile
from aiogram import Bot, Dispatcher, types, F, filters
from PIL import Image, ImageOps
import numpy as np
import tensorflow as tf

# --- БЛОК АВТО-РАСПАКОВКИ ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
zip_path = os.path.join(BASE_DIR, "converted_keras (5).zip")

if os.path.exists(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(BASE_DIR)
        print("✅ Файлы модели успешно извлечены из архива!")

model_path = os.path.join(BASE_DIR, "keras_model.h5")
labels_path = os.path.join(BASE_DIR, "labels.txt")

model = tf.keras.models.load_model(model_path, compile=False)
with open(labels_path, "r", encoding="utf-8") as f:
    class_names = [line.strip().split(" ", 1)[-1].lower() for line in f.readlines()]

bot = Bot(token="8703096883:AAEt34PAms4QtFpyFcqJcHeAt2CWPk7eZd4")
dp = Dispatcher()

user_scores = {}

# --- ТВОИ СПИСКИ В ТВОЕМ ФОРМАТЕ ---
healthy_food = [
    "брокколи", "шпинат", "морковь", "яблоки", "авокадо", "чечевица", "гречка", "орехи",
    "яблоко", "банан", "огурец", "помидор", "томат", "салат", "капуста", "груша", 
    "перец", "болгарский перец", "лук", "чеснок", "баклажан", "кабачок", "цукини", 
    "зелень", "петрушка", "укроп", "имбирь", "редис", "цветная капуста", "картофель", 
    "сельдерей", "тыква", "фрукты", "овощи", "ягоды"
]

plastic_packaging = [
    "йогурт", "творог", "чипсы", "замороженные овощи", "растительное масло", "готовые салаты", 
    "бутылка", "пластик", "упаковка", "контейнер", "пакет", "сухарики", "кетчуп", 
    "майонеза", "пленка", "пэт", "соус", "вода", "пятилитровка", "канистра", 
    "лоток", "подложка", "зип-пакет", "блистер"
]

meat_products = [
    "говядина", "свинина", "стейк", "ребрышки", "мясо", "филе", "вырезка",
    "фарш", "баранина", "антрекот", "грудинка", "бекон", "колбаса", 
    "мясная нарезка", "хамон", "салями", "корейка"
]

sweets = [
    "конфеты", "шоколад", "печенье", "торт", "сахар", "пончик", "газировка", 
    "лимонад", "сироп", "десерт", "маффин", "выпечка", "мороженое", "пирожное", 
    "сладости", "карамель", "зефир", "мармелад", "леденец", "батончик", "фантик", 
    "упаковка", "сладкое", "шоколадка", "макарун", "тирамису"
]

local_produce = [
    "фермерский", "местный", "домашний", "рынок", "свежий", "деревенский", 
    "с грядки", "сезонный", "свое", "натуральный", "локальный", "огород", 
    "сад", "ферма", "ягоды", "клубника", "вишня", "черешня", "орехи", 
    "фундук", "миндаль", "грецкий орех", "семечки"
]


def predict_image(img_path):
    size = (224, 224)
    image = Image.open(img_path).convert("RGB")
    image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
    image_array = np.asarray(image)
    normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1
    
    data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
    data[0] = normalized_image_array
    
    prediction = model.predict(data)
    index = np.argmax(prediction)
    return class_names[index], float(prediction[0][index])


@dp.message(filters.Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    user_scores[user_id] = {"eco": 0}
    
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Отправь фото продукта,а я оценю его экологичность!"
    )


@dp.message(F.photo)
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_scores:
        user_scores[user_id] = {"eco": 0}

    file_path = os.path.join(BASE_DIR, f"img_{user_id}.jpg")
    
    try:
        await bot.download(message.photo[-1], destination=file_path)
        label, confidence = predict_image(file_path)
        label = label.lower() 

        is_eco = any(word in label for word in healthy_food) or "healthy_food" in label or \
                 any(word in label for word in local_produce) or "local_produce" in label

        if user_scores[user_id]["eco"] < 0 and not is_eco:
            await message.answer(f"⚠️ Твой баланс: {user_scores[user_id]['eco']}\nВы много вредите здоровью и природе! Исправляйтесь!")
            return

        response_text = f"🔍 Вижу на фото: {label} (уверенность: {confidence:.2%})\n\n"
        
        if any(word in label for word in healthy_food) or "healthy_food" in label:
            user_scores[user_id]["eco"] += 15  
            response_text += "🥗 +15 баллов! Растительная пища — это минимум ресурсов и максимум пользы."

        elif any(word in label for word in meat_products) or "meat" in label:
            user_scores[user_id]["eco"] -= 20 
            response_text += "🥩 -20 баллов. Животноводство требует ресурсов.\n💡 Совет: Добавь к мясу овощей!"

        elif any(word in label for word in plastic_packaging) or "plastic" in label:
            user_scores[user_id]["eco"] -= 15 
            response_text += "♻️ -15 баллов. Пластиковая упаковка отравляет планету."
            if "вода" in label or "бутылка" in label:
                response_text += "\n💡 Совет: Используй многоразовую бутылку!"

        elif any(word in label for word in local_produce) or "local_produce" in label: 
            user_scores[user_id]["eco"] += 10
            response_text += "🚜 +10 баллов! Локальные продукты снижают углеродный след."

        elif any(word in label for word in sweets) or "sweets" in label: 
            user_scores[user_id]["eco"] -= 10 
            response_text += "🍬 -10 баллов. Сахар и упаковка вредят природе."

        else:
            response_text += "Я распознал объект, но он не входит в категории."

        await message.answer(f"{response_text}\n\n🏆 Твой текущий эко-баланс: {user_scores[user_id]['eco']}")

    except Exception as e:
        print(f"Ошибка: {e}")
        await message.answer("Ошибка при анализе фото.")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
