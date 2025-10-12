from pymongo import MongoClient
from datetime import datetime, timedelta
import random
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
            "borrowDate": self.borrowDate.strftime("%Y-%m-%d"),
            "returnDate": self.returnDate.strftime("%Y-%m-%d") if self.returnDate else None,
            "renewCount": self.renewCount
        }

    # ---------- CREATE ----------
    @classmethod
    def create_loan(cls, member_email: str, book_title: str, borrow_date: datetime):
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        loan_col = db["Loan"]

        existing = loan_col.find_one({
            "member_email": member_email,
            "book_title": book_title,
            "returnDate": None
        })
        if existing:
            client.close()
            return False

        # Check availability
        book_col = db["books"] if "books" in db.list_collection_names() else db["Book"]
        book = book_col.find_one({"title": book_title})
        if not book or book["available"] <= 0:
            client.close()
            return False

        Book.borrow_book(book_title)

        new_loan = Loan(member_email, book_title, borrow_date)
        loan_col.insert_one(new_loan.to_dict())
        client.close()
        return True

    # ---------- RETRIEVE ----------
    @classmethod
    def get_all_loans_for_user(cls, member_email: str):
        """
        Retrieve all loan records for a specific user,
        including cover URLs from either 'books' or 'Book' collection.
        """
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]

        loan_col = db["Loan"]
        loans = list(loan_col.find({"member_email": member_email}, {"_id": 0}))

        book_col = db["books"] if "books" in db.list_collection_names() else db["Book"]

        # Attach book covers (supports both 'url' and 'cover_url')
        for loan in loans:
            book = book_col.find_one(
                {"title": loan["book_title"]},
                {"url": 1, "cover_url": 1, "_id": 0}
            )
            if book:
                if "url" in book:
                    loan["cover"] = book["url"]
                elif "cover_url" in book:
                    loan["cover"] = book["cover_url"]
                else:
                    loan["cover"] = ""
            else:
                loan["cover"] = ""

        client.close()

        # Sort by borrowDate descending
        try:
            loans.sort(
                key=lambda x: datetime.strptime(x["borrowDate"], "%Y-%m-%d"),
                reverse=True
            )
        except Exception:
            pass

        return loans

    @classmethod
    def get_loan(cls, member_email: str, book_title: str):
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        loan = db["Loan"].find_one(
            {"member_email": member_email, "book_title": book_title},
            {"_id": 0}
        )
        client.close()
        return loan

    # ---------- UPDATE ----------
    @classmethod
    def renew_loan(cls, member_email: str, book_title: str):
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        loan_col = db["Loan"]

        loan = loan_col.find_one({
            "member_email": member_email,
            "book_title": book_title,
            "returnDate": None
        })
        if not loan:
            client.close()
            return "not_found"

        borrow_date = datetime.strptime(loan["borrowDate"], "%Y-%m-%d")
        due_date = borrow_date + timedelta(days=14)

        if datetime.now() > due_date or loan["renewCount"] >= 2:
            client.close()
            return "maxed"

        new_borrow_date = borrow_date + timedelta(days=random.randint(10, 20))
        new_borrow_date = min(new_borrow_date, datetime.now())

        loan_col.update_one(
            {"member_email": member_email, "book_title": book_title},
            {
                "$set": {"borrowDate": new_borrow_date.strftime("%Y-%m-%d")},
                "$inc": {"renewCount": 1}
            }
        )
        client.close()
        return "success"

    @classmethod
    def return_loan(cls, member_email: str, book_title: str):
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        loan_col = db["Loan"]

        loan = loan_col.find_one({
            "member_email": member_email,
            "book_title": book_title,
            "returnDate": None
        })
        if not loan:
            client.close()
            return False

        borrow_date = datetime.strptime(loan["borrowDate"], "%Y-%m-%d")
        new_return_date = borrow_date + timedelta(days=random.randint(10, 20))
        new_return_date = min(new_return_date, datetime.now())

        loan_col.update_one(
            {"member_email": member_email, "book_title": book_title},
            {"$set": {"returnDate": new_return_date.strftime("%Y-%m-%d")}}
        )

        Book.return_book(book_title)
        client.close()
        return True

    # ---------- DELETE ----------
    @classmethod
    def delete_loan(cls, member_email: str, book_title: str):
        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        loan_col = db["Loan"]

        loan = loan_col.find_one({
            "member_email": member_email,
            "book_title": book_title
        })

        if not loan or not loan.get("returnDate"):
            client.close()
            return False

        loan_col.delete_one({"member_email": member_email, "book_title": book_title})
        client.close()
        return True
