import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    DB_NAME = os.getenv("DB_NAME", "ai_sales_chatbot")
    JWT_SECRET = os.getenv("JWT_SECRET")
    JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", 60))
    REFRESH_TOKEN_EXPIRY_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRY_DAYS", 7))
    BCRYPT_COST = int(os.getenv("BCRYPT_COST", 12))

    @classmethod
    def validate(cls):
        if not cls.JWT_SECRET:
            raise ValueError("JWT_SECRET environment variable is not set")

config = Config()
