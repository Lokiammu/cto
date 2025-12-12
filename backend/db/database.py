from pymongo import MongoClient
from backend.config import config

class Database:
    client: MongoClient = None

    def connect(self):
        self.client = MongoClient(config.MONGO_URI)
        print("Connected to MongoDB")

    def close(self):
        if self.client:
            self.client.close()
            print("Disconnected from MongoDB")

    def get_db(self):
        return self.client[config.DB_NAME]

db = Database()
