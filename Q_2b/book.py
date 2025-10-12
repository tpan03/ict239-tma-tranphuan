from pymongo import MongoClient
from typing import List
from books import all_books  # provided file with book data


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
        """Convert the Book object into a MongoDB-storable dictionary."""
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
        """Populate MongoDB 'books' collection from all_books if empty."""
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        book_col = db["books"]

        if book_col.count_documents({}) == 0:
            print("Book collection empty — populating from all_books...")
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
                book_col.insert_one(new_book.to_dict())
            print("✅ Book collection successfully created and populated.")
        else:
            print("✅ Book collection already contains data.")

        client.close()

    @classmethod
    def get_all_books(cls):
        """Retrieve all book documents from MongoDB."""
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        book_col = db["books"]
        books = list(book_col.find({}, {"_id": 0}))
        client.close()
        return books

    @classmethod
    def get_books_by_category(cls, category: str):
        """Retrieve books filtered by category."""
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        book_col = db["books"]

        if category == "All":
            results = list(book_col.find({}, {"_id": 0}))
        else:
            results = list(book_col.find({"category": category}, {"_id": 0}))

        client.close()
        return results
