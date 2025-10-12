from flask import Flask, render_template, request
from pymongo import MongoClient
from book import Book  # import Book class

app = Flask(__name__)

# Initialize MongoDB data
Book.initialize_collection()

# --------------------------
# Home Page – Book Listings
# --------------------------
@app.route('/', methods=['GET'])
def index():
    """Displays all books or filters by category."""
    selected_category = request.args.get('category', 'All')

    # Fetch books based on selected category
    books = Book.get_books_by_category(selected_category)
    count = len(books)

    # Retrieve all distinct categories for dropdown
    client = MongoClient("mongodb://localhost:27017/")
    db = client["libraryDB"]
    book_col = db["Book"]
    categories = sorted(book_col.distinct("category"))
    client.close()

    return render_template(
        'index.html',
        books=books,
        categories=categories,
        selected_category=selected_category,
        count=count
    )


# --------------------------
# Book Detail Page
# --------------------------
@app.route('/book/<string:title>')
def book_detail(title):
    """Displays detailed info for a single book."""
    client = MongoClient("mongodb://localhost:27017/")
    db = client["libraryDB"]
    book_col = db["Book"]
    book = book_col.find_one({"title": title}, {"_id": 0})
    client.close()

    if book:
        return render_template('book_detail.html', book=book)
    else:
        return "<h2>Book not found.</h2>", 404


# --------------------------
# Run Flask App
# --------------------------
if __name__ == '__main__':
    app.run(debug=True)
