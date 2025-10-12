from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    @staticmethod
    def get_collection():
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        return db["User"], client

    @classmethod
    def register(cls, email, password, name):
        """Register a new user if the email is not already used."""
        user_col, client = cls.get_collection()
        if user_col.find_one({"email": email}):
            client.close()
            return False  # Email already exists
        hashed_pw = generate_password_hash(password)
        user_col.insert_one({
            "email": email,
            "password": hashed_pw,
            "name": name,
            "is_admin": False
        })
        client.close()
        return True

    @classmethod
    def authenticate(cls, email, password):
        """Authenticate an existing user by email and password."""
        user_col, client = cls.get_collection()
        user = user_col.find_one({"email": email})
        client.close()
        if user and check_password_hash(user["password"], password):
            return user
        return None
