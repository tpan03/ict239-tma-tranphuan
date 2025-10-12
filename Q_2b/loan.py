from pymongo import MongoClient
from datetime import datetime
from typing import Optional
from book import Book  # to update available count


class Loan:
    def __init__(self, member_email: str, book_title: str, borrowDate: datetime,
                 returnDate: Optional[datetime] = None, renewCount: int = 0):
        self.member_email = member_email
        self.book_title = book_title
        self.borrowDate = borrowDate
        self.returnDate = returnDate
        self.renewCount = renewCount

    def to_dict(self):
        """Convert the Loan object to a MongoDB-storable dictionary."""
        return {
            "member_email": self.member_email,
            "book_title": self.book_title,
            "borrowDate": self.borrowDate,
            "returnDate": self.returnDate,
            "renewCount": self.renewCount
        }

    # ---------- CREATE ----------
    @classmethod
    def create_loan(cls, member_email: str, book_title: str):
        """
        Create a new loan if the user does not have an active loan for this book.
        Decrease the book's available count if successful.
        """
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        loan_col = db["Loan"]

        # Check for existing unreturned loan
        existing = loan_col.find_one({
            "member_email": member_email,
            "book_title": book_title,
            "returnDate": None
        })
        if existing:
            print(f"⚠️ Loan already exists for '{book_title}' and not yet returned.")
            client.close()
            return False

        # Check book availability
        all_books = db["Book"]
        book = all_books.find_one({"title": book_title})
        if not book or book["available"] <= 0:
            print(f"❌ No available copies for '{book_title}'.")
            client.close()
            return False

        # Decrease available count and create loan
        Book.borrow_book(book_title)

        new_loan = Loan(member_email, book_title, datetime.now())
        loan_col.insert_one(new_loan.to_dict())
        print(f"✅ Loan created for '{book_title}' by {member_email}.")
        client.close()
        return True

    # ---------- RETRIEVE ----------
    @classmethod
    def get_all_loans_for_user(cls, member_email: str):
        """Retrieve all loan records for a specific user."""
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        loans = list(db["Loan"].find({"member_email": member_email}, {"_id": 0}))
        client.close()
        return loans

    @classmethod
    def get_loan(cls, member_email: str, book_title: str):
        """Retrieve a specific loan record."""
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        loan = db["Loan"].find_one(
            {"member_email": member_email, "book_title": book_title}, {"_id": 0})
        client.close()
        return loan

    # ---------- UPDATE ----------
    @classmethod
    def renew_loan(cls, member_email: str, book_title: str):
        """
        Renew a loan — only if not returned yet.
        Updates borrowDate and increases renewCount.
        """
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        loan_col = db["Loan"]

        loan = loan_col.find_one({
            "member_email": member_email,
            "book_title": book_title,
            "returnDate": None
        })
        if not loan:
            print(f"❌ No active loan found for '{book_title}'.")
            client.close()
            return False

        new_count = loan["renewCount"] + 1
        loan_col.update_one(
            {"_id": loan["_id"]},
            {"$set": {"renewCount": new_count, "borrowDate": datetime.now()}}
        )
        print(f"✅ Loan for '{book_title}' renewed. Renew count: {new_count}.")
        client.close()
        return True

    @classmethod
    def return_loan(cls, member_email: str, book_title: str):
        """
        Return a loan — updates returnDate and increases book availability.
        """
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        loan_col = db["Loan"]

        loan = loan_col.find_one({
            "member_email": member_email,
            "book_title": book_title,
            "returnDate": None
        })
        if not loan:
            print(f"⚠️ No unreturned loan found for '{book_title}'.")
            client.close()
            return False

        # Mark loan as returned
        loan_col.update_one(
            {"_id": loan["_id"]},
            {"$set": {"returnDate": datetime.now()}}
        )

        # Increase available copies
        Book.return_book(book_title)

        print(f"✅ '{book_title}' has been returned by {member_email}.")
        client.close()
        return True

    # ---------- DELETE ----------
    @classmethod
    def delete_loan(cls, member_email: str, book_title: str):
        """
        Delete a returned loan record (only allowed if already returned).
        """
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        loan_col = db["Loan"]

        loan = loan_col.find_one({
            "member_email": member_email,
            "book_title": book_title
        })

        if not loan:
            print(f"❌ Loan not found for '{book_title}'.")
            client.close()
            return False

        if not loan.get("returnDate"):
            print(f"⚠️ Cannot delete active loan for '{book_title}'. Must be returned first.")
            client.close()
            return False

        loan_col.delete_one({"_id": loan["_id"]})
        print(f"🗑️ Loan for '{book_title}' deleted successfully.")
        client.close()
        return True
