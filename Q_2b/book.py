from pymongo import MongoClient
from typing import List
from books import all_books


class Book:
    def __init__(self, genres: List[str], title: str, category: str, url: str,
                 description: List[str], authors: List[str],
                 pages: int, available: int, copies: int):
        self.genres = genres
        self.title = title
        self.category = category
        self.url = url
        self.description = description
        self.authors = authors
        self.pages = pages
        self.available = available
        self.copies = copies

    def to_dict(self):
        return {
            "genres": self.genres,
            "title": self.title,
            "category": self.category,
            "url": self.url,
            "description": self.description,
            "authors": self.authors,
            "pages": self.pages,
            "available": self.available,
            "copies": self.copies
        }

    @classmethod
    def initialize_collection(cls):
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        col = db["books"]

        if col.count_documents({}) == 0:
            print("Book collection empty — populating...")
            for b in all_books:
                new_book = Book(
                    genres=b.get("genres", []),
                    title=b.get("title", ""),
                    category=b.get("category", ""),
                    url=b.get("url", ""),
                    description=b.get("description", []),
                    authors=b.get("authors", []),
                    pages=b.get("pages", 0),
                    available=b.get("available", 0),
                    copies=b.get("copies", 0)
                )
                col.insert_one(new_book.to_dict())
            print("✅ Collection populated.")
        else:
            print("✅ Collection already populated.")
        client.close()

    @classmethod
    def get_books_by_category(cls, category: str):
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        col = db["books"]

        if category == "All":
            results = list(col.find({}, {"_id": 0}))
        else:
            results = list(col.find({"category": category}, {"_id": 0}))

        client.close()
        return results

    @classmethod
    def update_availability(cls, title: str, change: int):
        """Increase or decrease 'available' count by 'change'."""
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        col = db["books"]
        col.update_one({"title": title}, {"$inc": {"available": change}})
        client.close()
