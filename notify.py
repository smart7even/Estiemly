import asyncio
import os

from aiogram import Bot
from pymongo import MongoClient

client = MongoClient(os.getenv("DB_CONNECTION_STRING"))

db = client['aiogram_fsm']

collection = db['aiogram_data']

print('Aiogram data collection has ' + str(collection.count_documents({})) + " entries")

unique_users: set[int] = set()

for data in collection.find():
    unique_users.add(data["chat"])

print("Total number of users: " + str(len(unique_users)))

for user in unique_users:
    print(user)

API_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=API_TOKEN)


async def main():
    for user in unique_users:
        await bot.send_message(user,
                               text="Привет. У меня вышло обновление! 🆕🆕🆕\n\nЧтобы ничего не упустить нажми на /start\n\nВ менюшке появятся две новые команды: Стикерпак и Словарик. Посмотри, что там) 🦄")
    await bot.close()

asyncio.run(main())
