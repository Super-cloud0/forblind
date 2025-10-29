import os
import time
import pyttsx3
import requests
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
import google.generativeai as genai
import speech_recognition as sr

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("❌ Ошибка: API-ключ GEMINI_API_KEY не найден. Проверь .env")

genai.configure(api_key=GEMINI_API_KEY)

ESP32_IP = "http://192.168.137.99"
MODEL_NAME = "gemini-2.5-pro"
SYSTEM_INSTRUCTION = (
    "Ты — глаза незрячего человека. Опиши только важное для ориентации и безопасности. "
    "1) люди, 2) транспорт, 3) препятствия, 4) общее окружение. 5)если есть текст прочитай его Кратко — 1–2 предложения."
)
TEMPERATURE = 0.3
def capture_image():
    print("📸 Захватываю кадр с ESP32-CAM...")
    response = requests.get(f"{ESP32_IP}/capture", timeout=15)
    response.raise_for_status()
    img = Image.open(BytesIO(response.content))
    img.save("last_capture.jpg")
    print("✅ Сохранён кадр: last_capture.jpg")
    return img


def describe_image(image: Image.Image) -> str:
    print("🤖 Отправляю в Gemini AI...")
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_INSTRUCTION
    )
    response = model.generate_content(["Опиши эту сцену.", image])
    if hasattr(response, "text"):
        return response.text
    return str(response)


def speak(text, lang_hint="ru"):
    """
    Инициализируем pyttsx3 прямо перед каждым воспроизведением.
    Добавляем маленькую паузу перед воспроизведением, чтобы ОС успела освободить аудио-устройство
    после работы с микрофоном.
    """
    try:
        if not text:
            return
        time.sleep(0.15)
        engine = pyttsx3.init()
        
        engine.setProperty("rate", 170)
        engine.setProperty("volume", 1.0)
     
        engine.say(text)
        engine.runAndWait()
   
        try:
            engine.stop()
        except Exception:
            pass
    except Exception as e:
        print("⚠️ Ошибка при TTS:", e)


def listen_for_command():
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("🎧 Слушаю команду... (скажи: 'опиши что вокруг меня' или 'стоп' для выхода)")
            # Можно настроить recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=6, phrase_time_limit=6)
    except sr.WaitTimeoutError:
        print("⏱ Таймаут ожидания команды.")
        return ""
    try:
        command = recognizer.recognize_google(audio, language="ru-RU").lower()
        print(f"🗣 Ты сказал: {command}")
        return command
    except sr.UnknownValueError:
        print("❓ Не понял команду.")
        return ""
    except sr.RequestError as e:
        print(f"⚠️ Ошибка сервиса распознавания: {e}")
        return ""



print("🤖 Ассистент для незрячих запущен. Готов слушать команды.")
speak("Я готов. Скажи: опиши что вокруг меня, чтобы я рассказал, что вижу.")

while True:
    command = listen_for_command()


    if "стоп" in command or "выключись" in command or "выход" in command:
        speak("Хорошо, завершаю работу. Пока.")
        break

    if "опиши" in command and "вокруг" in command:
        try:

            time.sleep(0.1)
            img = capture_image()
            description = describe_image(img)
            print("\n--- ОПИСАНИЕ ---\n", description, "\n----------------")
            speak(description)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            speak("Произошла ошибка при описании сцены.")
    elif command:
        speak("Команда не распознана. Повтори, пожалуйста.")
 
