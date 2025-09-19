import logging
import operator
import os

from aiogram import executor
from aiogram.contrib.fsm_storage.mongo import MongoStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, ParseMode, ReplyKeyboardMarkup
from aiogram.utils.executor import start_webhook
from aiogram_dialog import DialogManager, DialogRegistry, Dialog, Window, StartMode
from aiogram_dialog.widgets.kbd import Button, Multiselect, Row
from aiogram_dialog.widgets.media import StaticMedia
from aiogram_dialog.widgets.text import Format, Const
from dotenv import load_dotenv
import hashlib
from aiogram.contrib.fsm_storage.files import JSONStorage

from aiogram import Bot, Dispatcher, types

from faq_catalog import download_faq

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
USE_FILE_STORAGE = os.getenv("USE_FILE_STORAGE", "false").lower() == "true"

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
PREVENT_SLEEP_HEROKU_PING_INTERVAL_IN_SECONDS = 60 * 5

m = hashlib.sha256()
m.update(bytes(API_TOKEN, encoding="utf8"))
server_endpoint = m.hexdigest()
print(server_endpoint)
WEBHOOK_PATH = f'/bot/{server_endpoint}'

WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = os.getenv("PORT", 5000)

logging.basicConfig(level=logging.INFO)
logging.info(f"Starting webhook at {WEBHOOK_URL}")
logging.info(f"App port {WEBAPP_PORT}")


class DialogSG(StatesGroup):
    initial = State()
    merch = State()
    greeting = State()
    question_details = State()
    stickerpack = State()
    vocabulary = State()


async def get_data(dialog_manager: DialogManager, **kwargs):
    return {
        "stack": dialog_manager.current_stack(),
        "context": dialog_manager.current_context(),
        "counter": dialog_manager.current_context().dialog_data.get("counter", 0),
        "question": dialog_manager.current_context().dialog_data.get("question", "Oops something went wrong"),
        "answer": dialog_manager.current_context().dialog_data.get("answer", "Try again pls"),
    }


async def name_handler(m: Message, dialog: Dialog, manager: DialogManager):
    await m.answer(f"Nice to meet you, {m.text}")


async def on_click(c: CallbackQuery, button: Button, manager: DialogManager):
    counter = manager.current_context().dialog_data.get("counter", 0)
    manager.current_context().dialog_data["counter"] = counter + 1


multi = Multiselect(
    Format("✓ {item[0]}"),  # E.g `✓ Apple`
    Format("{item[0]}"),
    id="check",
    item_id_getter=operator.itemgetter(1),
    items="fruits",
)


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    # loop = asyncio.get_event_loop()
    # loop.create_task(periodic())


async def on_shutdown(dp):
    logging.warning('Shutting down..')
    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()
    logging.warning('Bye!')


async def go_back(c: CallbackQuery, button: Button, manager: DialogManager):
    await manager.dialog().back()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # storage = RedisStorage(host='localhost', port=6379)
    storage = None

    if USE_FILE_STORAGE:
        storage = JSONStorage(path="fsm_storage")
    else:
        storage = MongoStorage()
        storage._uri = os.getenv("DB_CONNECTION_STRING")
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(bot, storage=storage)
    dp.middleware.setup(LoggingMiddleware())
    registry = DialogRegistry(dp)

    questions = download_faq("assets/texts/faq.txt")

    @dp.message_handler(commands=['start'])
    async def cmd_start(message: types.Message, dialog_manager: DialogManager):
        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True, selective=True)
        markup.add("Merch", "Вопросы к LR", "Стикерпак", "Словарик")

        await bot.send_message(message.chat.id,
                               text="Привет. Я Estiemly. Сейчас у тебя внизу появятся кнопки, посмотри что там",
                               reply_markup=markup)

    @dp.message_handler(lambda message: message.text in ["Merch", "Вопросы к LR", "Стикерпак", "Словарик"])
    async def initial_start(message: types.Message, dialog_manager: DialogManager):
        if message.text == "Merch":
            await dialog_manager.start(DialogSG.merch, mode=StartMode.NEW_STACK)
        elif message.text == "Вопросы к LR":
            await dialog_manager.start(DialogSG.greeting, mode=StartMode.NEW_STACK)
        elif message.text == "Стикерпак":
            await dialog_manager.start(DialogSG.stickerpack, mode=StartMode.NEW_STACK)
        elif message.text == "Словарик":
            await dialog_manager.start(DialogSG.vocabulary, mode=StartMode.NEW_STACK)

    async def on_question_click(c: CallbackQuery, button: Button, manager: DialogManager):
        print(button.widget_id)
        question = questions[int(button.widget_id)]
        manager.current_context().dialog_data["question"] = question.question
        manager.current_context().dialog_data["answer"] = question.answer
        await c.answer()
        print(manager.current_context().dialog_data)
        await manager.dialog().switch_to(DialogSG.question_details)

    merch_text_file = open("assets/texts/merch.txt")
    merch_text = merch_text_file.read()
    merch_text_file.close()

    questions_dialog = Dialog(
        Window(
            Format(merch_text),
            StaticMedia(path="assets/merch2.jpg"),
            state=DialogSG.merch,
        ),

        Window(
            Format("Привет! Олеся Гладкоскок (Local Responsible LG Spb) подготовила для тебя ответы на частые "
                   "вопросы.\nWatch it to stay tuned 🤟"),
            *[Button(Const(f"{questions[i].question}"), id=f"{i}", on_click=on_question_click) for i in
              range(len(questions))],
            state=DialogSG.greeting,
            getter=get_data,
        ),
        Window(
            Format("<b>{question}</b>"),
            Format("{answer}"),
            Row(
                Button(Const("Back"), id="back2", on_click=go_back),
            ),
            state=DialogSG.question_details,
            getter=get_data,
            parse_mode=ParseMode.HTML
        ),
        Window(
            Format("<b>Стикерпак</b>"),
            Format("У нас есть классные стикеры только для тебя!\n"),
            Format("Забирай по тапу сюда: https://t.me/addstickers/ESTIckers2021"),
            state=DialogSG.stickerpack,
            getter=get_data,
            parse_mode=ParseMode.HTML
        ),
        Window(
            Format("<b>Словарик</b>"),
            Format(
                "А еще у нас есть мини-словарик со специальной лексикой для начинающего ESTIEM’eра!\n"),
            Format(
                "Забирай по тапу сюда: https://drive.google.com/file/d/1mP-Pb_IxGBTbKd6Zyw3Q9IsIPCxRKW8L/view?usp=sharing"),
            state=DialogSG.vocabulary,
            getter=get_data,
            parse_mode=ParseMode.HTML
        ),
    )

    registry.register_start_handler(DialogSG.initial)
    registry.register(questions_dialog)

    if os.getenv('USE_WEBHOOK') == "true":
        start_webhook(
            dispatcher=dp,
            webhook_path=WEBHOOK_PATH,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            skip_updates=True,
            host=WEBAPP_HOST,
            port=WEBAPP_PORT,
        )
    else:
        executor.start_polling(dp, skip_updates=True)
