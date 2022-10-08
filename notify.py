import os

from pymongo import MongoClient

client = MongoClient(os.getenv("DB_CONNECTION_STRING"))

db = client['aiogram_fsm']

collection = db['aiogram_data']

print('Aiogram data collection has ' + str(collection.count_documents({})) + " entries")

unique_users: set[int] = set()

for data in collection.find():
    unique_users.add(data["chat"])

for user in unique_users:
    print(user)

print("Total number of users: " + str(len(unique_users)))

