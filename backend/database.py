from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None


db = Database()


async def connect_to_mongo():
    """Connect to MongoDB"""
    try:
        db.client = AsyncIOMotorClient(
            settings.mongodb_url,
            maxPoolSize=10,
            minPoolSize=1,
            serverSelectionTimeoutMS=5000
        )
        # Verify connection
        await db.client.admin.command('ping')
        db.db = db.client[settings.mongodb_db_name]
        logger.info(f"Connected to MongoDB: {settings.mongodb_db_name}")
        
        # Create indexes
        await create_indexes()
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()
        logger.info("Closed MongoDB connection")


async def create_indexes():
    """Create database indexes"""
    # Users collection
    await db.db.users.create_index("email", unique=True)
    await db.db.users.create_index("username", unique=True)
    
    # Products collection
    await db.db.products.create_index("name")
    await db.db.products.create_index("category")
    await db.db.products.create_index("brand")
    await db.db.products.create_index([("name", "text"), ("description", "text")])
    
    # Orders collection
    await db.db.orders.create_index("user_id")
    await db.db.orders.create_index("created_at")
    
    # Cart collection
    await db.db.carts.create_index("user_id", unique=True)
    
    # Sessions collection (for chat)
    await db.db.channel_sessions.create_index("session_id", unique=True)
    await db.db.channel_sessions.create_index("user_id")
    await db.db.channel_sessions.create_index("created_at", expireAfterSeconds=2592000)  # 30 days TTL
    
    # Tokens collection (for JWT blacklist)
    await db.db.revoked_tokens.create_index("token", unique=True)
    await db.db.revoked_tokens.create_index("expires_at", expireAfterSeconds=0)
    
    logger.info("Database indexes created")


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance"""
    return db.db
