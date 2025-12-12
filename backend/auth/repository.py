from pymongo.collection import Collection
from bson.objectid import ObjectId
from datetime import datetime
from backend.auth.models import UserCreate, UserInDB
from backend.auth.utils import get_password_hash

class UserRepository:
    def __init__(self, collection: Collection):
        self.collection = collection

    def get_by_email(self, email: str):
        user_doc = self.collection.find_one({"email": email})
        if user_doc:
            user_doc["id"] = str(user_doc["_id"])
            return user_doc
        return None

    def get_by_id(self, user_id: str):
        try:
            oid = ObjectId(user_id)
        except:
            return None
        user_doc = self.collection.find_one({"_id": oid})
        if user_doc:
            user_doc["id"] = str(user_doc["_id"])
            return user_doc
        return None

    def create(self, user: UserCreate):
        user_dict = user.model_dump()
        password = user_dict.pop("password")
        user_dict["password_hash"] = get_password_hash(password)
        user_dict["created_at"] = datetime.now()
        user_dict["updated_at"] = datetime.now()
        user_dict["jwt_tokens"] = []
        
        result = self.collection.insert_one(user_dict)
        user_dict["id"] = str(result.inserted_id)
        return user_dict

    def add_token(self, user_id: str, token: str):
        self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$push": {"jwt_tokens": {"token": token, "created_at": datetime.now(), "revoked": False}}}
        )

    def revoke_token(self, user_id: str, token: str):
        self.collection.update_one(
            {"_id": ObjectId(user_id), "jwt_tokens.token": token},
            {"$set": {"jwt_tokens.$.revoked": True}}
        )

    def is_token_revoked(self, user_id: str, token: str):
        user = self.collection.find_one(
            {"_id": ObjectId(user_id), "jwt_tokens": {"$elemMatch": {"token": token, "revoked": True}}}
        )
        return user is not None
