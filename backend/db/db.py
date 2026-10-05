import os

from pymongo import AsyncMongoClient


mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
mongodb_db_name = os.getenv("MONGODB_DB_NAME", "error_log_analyzer")
mongo_client = AsyncMongoClient(mongodb_uri)
database = mongo_client[mongodb_db_name]
