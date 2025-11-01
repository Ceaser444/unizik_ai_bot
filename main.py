import os
from pymongo import MongoClient

client = MongoClient(os.getenv("MONGO_URI"))
db = client["unizik_ai"]
