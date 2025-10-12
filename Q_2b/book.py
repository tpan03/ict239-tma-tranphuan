from pymongo import MongoClient
from typing import List
from books import all_books  # provided data file


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

    # ---------- INITIALIZE COLLECTION ----------
    @classmethod
    def initialize_collection(cls):
        """Populate MongoDB 'Book' collection from all_books if empty."""
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

    # ---------- RETRIEVAL ----------
    @classmethod
    def get_all_books(cls):
        """Retrieve all book documents from MongoDB."""
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        books = list(db["books"].find({}, {"_id": 0}))
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

    # ---------- NEW: BORROW BOOK ----------
    @classmethod
    def borrow_book(cls, title: str) -> bool:
        """
        Borrow a book (decrease available count by 1) if available.
        Returns True if successful, False otherwise.
        """
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        book_col = db["books"]

        book = book_col.find_one({"title": title})
        if not book:
            print(f"❌ Book '{title}' not found.")
            client.close()
            return False

        if book["available"] <= 0:
            print(f"⚠️ No available copies left for '{title}'.")
            client.close()
            return False

        # Decrease available count
        book_col.update_one({"title": title}, {"$inc": {"available": -1}})
        print(f"✅ '{title}' has been borrowed. Remaining available: {book['available'] - 1}")
        client.close()
        return True

    # ---------- NEW: RETURN BOOK ----------
    @classmethod
    def return_book(cls, title: str) -> bool:
        """
        Return a borrowed book (increase available count by 1).
        Ensures available does not exceed total copies.
        """
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        book_col = db["books"]

        book = book_col.find_one({"title": title})
        if not book:
            print(f"❌ Book '{title}' not found.")
            client.close()
            return False

        if book["available"] >= book["copies"]:
            print(f"⚠️ All copies of '{title}' are already returned.")
            client.close()
            return False

        # Increase available count
        book_col.update_one({"title": title}, {"$inc": {"available": 1}})
        print(f"✅ '{title}' has been returned. Available now: {book['available'] + 1}")
        client.close()
        return True
