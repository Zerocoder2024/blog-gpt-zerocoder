import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import requests

app = FastAPI()

# Получаем API ключи из переменных окружения
openai.api_key = os.getenv("OPENAI_API_KEY")  # Устанавливаем ключ OpenAI из переменной окружения
currentsapi_key = os.getenv("CURRENTS_API_KEY")  # Устанавливаем ключ Currents API из переменной окружения

# Проверяем, что оба API ключа заданы, иначе выбрасываем ошибку
if not openai.api_key or not currentsapi_key:
    raise ValueError("Переменные окружения OPENAI_API_KEY и CURRENTS_API_KEY должны быть установлены")

class Topic(BaseModel):
    topic: str  # Модель данных для получения темы в запросе

# Функция для получения последних новостей на заданную тему
def get_recent_news(topic: str):
    url = "https://api.currentsapi.services/v1/latest-news"  # URL API для получения новостей
    params = {
        "language": "en",  # Задаем язык новостей
        "keywords": topic,  # Ключевые слова для поиска новостей
        "apiKey": currentsapi_key  # Передаем API ключ
    }
    response = requests.get(url, params=params)  # Выполняем GET-запрос к API
    if response.status_code != 200:
        # Если статус код не 200, выбрасываем исключение с подробностями ошибки
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных: {response.text}")
    
    # Извлекаем новости из ответа, если они есть
    news_data = response.json().get("news", [])
    if not news_data:
        return "Свежих новостей не найдено."  # Сообщение, если новости отсутствуют
    
    # Возвращаем заголовки первых 5 новостей, разделенных переносами строк
    return "\n".join([article["title"] for article in news_data[:5]])

# Функция для генерации контента на основе темы и новостей
def generate_content(topic: str):
    recent_news = get_recent_news(topic)  # Получаем последние новости по теме

    try:
        # Генерация заголовка для статьи
        title = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # Используем модель GPT-4o-mini
            messages=[{
                "role": "user", 
                "content": f"Придумайте привлекательный и точный заголовок для статьи на тему '{topic}', с учётом актуальных новостей:\n{recent_news}. Заголовок должен быть интересным и ясно передавать суть темы."
            }],
            max_tokens=60,  # Ограничиваем длину ответа
            temperature=0.5,  # Умеренная случайность
            stop=["\n"]  # Прерывание на новой строке
        ).choices[0].message.content.strip()

        # Генерация мета-описания для статьи
        meta_description = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user", 
                "content": f"Напишите мета-описание для статьи с заголовком: '{title}'. Оно должно быть полным, информативным и содержать основные ключевые слова."
            }],
            max_tokens=120,  # Увеличиваем лимит токенов для полного ответа
            temperature=0.5,
            stop=["."]
        ).choices[0].message.content.strip()

        # Генерация полного контента статьи
        post_content = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user", 
                "content": f"""Напишите подробную статью на тему '{topic}', используя последние новости:\n{recent_news}. 
                Статья должна быть:
                1. Информативной и логичной
                2. Содержать не менее 1500 символов
                3. Иметь четкую структуру с подзаголовками
                4. Включать анализ текущих трендов
                5. Иметь вступление, основную часть и заключение
                6. Включать примеры из актуальных новостей
                7. Каждый абзац должен быть не менее 3-4 предложений
                8. Текст должен быть легким для восприятия и содержательным"""
            }],
            max_tokens=1500,  # Лимит токенов для развернутого текста
            temperature=0.5,
            presence_penalty=0.6,  # Штраф за повторение фраз
            frequency_penalty=0.6
        ).choices[0].message.content.strip()

        # Возвращаем сгенерированный контент
        return {
            "title": title,
            "meta_description": meta_description,
            "post_content": post_content
        }
    
    except Exception as e:
        # Обрабатываем ошибки генерации
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации контента: {str(e)}")

@app.post("/generate-post")
async def generate_post_api(topic: Topic):
    # Обрабатываем запрос на генерацию поста
    return generate_content(topic.topic)

@app.get("/")
async def root():
    # Корневой эндпоинт для проверки работоспособности сервиса
    return {"message": "Service is running"}

@app.get("/heartbeat")
async def heartbeat_api():
    # Эндпоинт проверки состояния сервиса
    return {"status": "OK"}

if __name__ == "__main__":
    import uvicorn
    # Запуск приложения с указанием порта
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
