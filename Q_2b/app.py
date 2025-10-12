from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from datetime import datetime, timedelta
import random
from book import Book
from user import User
from loan import Loan  # ✅ You'll need your Loan class defined for Part (c)

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------- INITIALIZE ----------
Book.initialize_collection()

@app.context_processor
def inject_user():
    """
    Makes `current_user` always available in templates.
    If no one is logged in, returns a dummy guest object with is_admin=False.
    """
    user = session.get("user")
    if user is None:
        user = {"email": None, "name": "Guest", "is_admin": False}
    return dict(current_user=user)


# ---------- HOME / BOOK TITLES ----------
@app.route('/')
def index():
    category = request.args.get('category', 'All')
    books = Book.get_books_by_category(category)
    total = len(books)

    client = MongoClient("mongodb://localhost:27017/")
    db = client["libraryDB"]
    categories = sorted(db["books"].distinct("category"))
    client.close()

    return render_template(
        'index.html',
        books=books,
        categories=categories,
        selected_category=category,
        total=total
    )


# ---------- REGISTER ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        if User.register(email, password, name):
            return redirect(url_for('login'))
        return render_template('register.html', error="Email already registered")
    return render_template('register.html')


# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.authenticate(email, password)
        if user:
            session['user'] = {
                'email': user['email'],
                'name': user['name'],
                'is_admin': user.get('is_admin', False)
            }
            flash(f"Welcome, {user['name']}!", 'success')
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid email or password")
    return render_template('login.html')


# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("You have logged out successfully.", "info")
    return redirect(url_for('index'))


# ---------- BOOK DETAILS ----------
@app.route('/book/<string:title>')
def book_detail(title):
    client = MongoClient("mongodb://localhost:27017/")
    db = client["libraryDB"]
    book = db["books"].find_one({"title": title}, {"_id": 0})
    client.close()
    return render_template('book_detail.html', book=book)


# ---------- ADD NEW BOOK (ADMIN) ----------
@app.route('/new_book', methods=['GET', 'POST'])
def new_book():
    if 'user' not in session or not session['user']['is_admin']:
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('index'))

    genres_list = [
        "Animals", "Business", "Comics", "Communication", "Dark Academia", "Emotion",
        "Fantasy", "Fiction", "Friendship", "Graphic Novels", "Grief", "Historical Fiction",
        "Indigenous", "Inspirational", "Magic", "Mental Health", "Nonfiction", "Personal Development",
        "Philosophy", "Picture Books", "Poetry", "Productivity", "Psychology", "Romance",
        "School", "Self Help"
    ]

    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        cover_url = request.form.get('cover_url')
        description = request.form.get('description')
        pages = request.form.get('pages')
        copies = request.form.get('copies')
        genres = request.form.getlist('genres')

        authors = []
        for i in range(1, 6):
            author_name = request.form.get(f'author{i}')
            is_illustrator = f'illustrator{i}' in request.form
            if author_name:
                authors.append({'name': author_name, 'illustrator': is_illustrator})

        client = MongoClient("mongodb://localhost:27017/")
        db = client["libraryDB"]
        db.books.insert_one({
            'title': title,
            'category': category,
            'url': cover_url,
            'description': [description],
            'pages': int(pages),
            'copies': int(copies),
            'available': int(copies),
            'genres': genres,
            'authors': [a['name'] for a in authors]
        })
        client.close()

        flash(f'"{title}" added successfully!', 'success')
        return redirect(url_for('new_book'))

    return render_template('new_book.html', genres=genres_list)


# ---------- MAKE A LOAN ----------
@app.route('/make_loan/<string:title>')
def make_loan(title):
    """
    Handles the Make a Loan function.
    Shows flash messages for login prompts, duplicate loans, and success.
    """

    # ✅ 1. Check login
    if 'user' not in session:
        flash('Please login or register first to get an account.', 'warning')
        return redirect(url_for('login'))

    # ✅ 2. Block admin from borrowing
    if session['user'].get('is_admin', False):
        flash('Admins cannot make loans.', 'danger')
        return redirect(url_for('book_detail', title=title))

    user_email = session['user']['email']

    # ✅ 3. Random borrow date (10–20 days before today)
    borrow_date = datetime.now() - timedelta(days=random.randint(10, 20))

    # ✅ 4. Check existing active loan
    loan_exists = Loan.get_loan(user_email, title)
    if loan_exists and loan_exists.get('returnDate') is None:
        flash(f'You already have an active loan for "{title}".', 'danger')
        return redirect(url_for('book_detail', title=title))

    # ✅ 5. Check availability
    client = MongoClient("mongodb://localhost:27017/")
    db = client["libraryDB"]
    book = db.books.find_one({'title': title})

    if not book or book['available'] <= 0:
        flash(f'"{title}" is currently not available for loan.', 'danger')
        client.close()
        return redirect(url_for('book_detail', title=title))

    # ✅ 6. Create Loan document
    Loan.create_loan(user_email, title, borrow_date)

    # ✅ 7. Decrease available count
    db.books.update_one({'title': title}, {'$inc': {'available': -1}})
    client.close()

    flash(f'Successfully borrowed "{title}" on {borrow_date.strftime("%Y-%m-%d")}.', 'success')
    return redirect(url_for('book_detail', title=title))


# ---------- MAIN ----------
if __name__ == '__main__':
    app.run(debug=True)
