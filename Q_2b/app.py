from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from datetime import datetime, timedelta
import random
from book import Book
from user import User
from loan import Loan

app = Flask(__name__)
app.secret_key = "supersecretkey"


# ---------- INITIALIZE ----------
Book.initialize_collection()


# ---------- CONTEXT PROCESSORS ----------
@app.context_processor
def inject_globals():
    """Make 'now' and 'timedelta' available in all templates."""
    return {
        'now': datetime.now(),
        'timedelta': timedelta
    }


@app.context_processor
def inject_user():
    """Make current_user always available in templates."""
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
    if 'user' not in session:
        flash('Please login or register first to make a loan.', 'warning')
        return redirect(url_for('login'))

    if session['user'].get('is_admin', False):
        flash('Admins cannot make loans.', 'danger')
        return redirect(url_for('book_detail', title=title))

    user_email = session['user']['email']
    borrow_date = datetime.now()

    loan_exists = Loan.get_loan(user_email, title)
    if loan_exists and loan_exists.get('returnDate') is None:
        flash(f'You already have an active loan for "{title}".', 'danger')
        return redirect(url_for('book_detail', title=title))

    success = Loan.create_loan(user_email, title, borrow_date)
    if not success:
        flash(f'"{title}" is currently not available for loan.', 'danger')
        return redirect(url_for('book_detail', title=title))

    flash(f'Successfully borrowed "{title}"!', 'success')
    return redirect(url_for('book_detail', title=title))


# ---------- VIEW LOANS ----------
@app.route('/loans')
def view_loans():
    if 'user' not in session:
        flash('Please login to view your loans.', 'warning')
        return redirect(url_for('login'))

    if session['user'].get('is_admin', False):
        flash('Admins do not have personal loans.', 'info')
        return redirect(url_for('index'))

    user_email = session['user']['email']
    loans = Loan.get_all_loans_for_user(user_email)

    # ✅ Convert string dates to datetime safely
    for loan in loans:
        try:
            if isinstance(loan.get('borrowDate'), str):
                loan['borrowDate'] = datetime.strptime(loan['borrowDate'], '%Y-%m-%d')
            if isinstance(loan.get('returnDate'), str) and loan.get('returnDate'):
                loan['returnDate'] = datetime.strptime(loan['returnDate'], '%Y-%m-%d')
        except Exception:
            pass

    loans.sort(key=lambda x: x['borrowDate'], reverse=True)
    return render_template('loan.html', loans=loans)


# ---------- RENEW LOAN ----------
@app.route('/renew_loan/<string:title>')
def renew_loan(title):
    if 'user' not in session:
        flash('Please login to renew a loan.', 'warning')
        return redirect(url_for('login'))

    user_email = session['user']['email']
    result = Loan.renew_loan(user_email, title)

    if result == "maxed":
        flash('Maximum renewal limit reached (2 times).', 'danger')
    elif result == "not_found":
        flash('No active loan found to renew.', 'danger')
    else:
        flash(f'Loan for "{title}" successfully renewed.', 'success')

    return redirect(url_for('view_loans'))


# ---------- RETURN LOAN ----------
@app.route('/return_loan/<string:title>')
def return_loan(title):
    if 'user' not in session:
        flash('Please login to return a book.', 'warning')
        return redirect(url_for('login'))

    user_email = session['user']['email']
    result = Loan.return_loan(user_email, title)

    if result:
        flash(f'"{title}" returned successfully!', 'success')
    else:
        flash(f'Unable to return "{title}".', 'danger')

    return redirect(url_for('view_loans'))


# ---------- DELETE LOAN ----------
@app.route('/delete_loan/<string:title>')
def delete_loan(title):
    if 'user' not in session:
        flash('Please login to delete loan history.', 'warning')
        return redirect(url_for('login'))

    user_email = session['user']['email']
    result = Loan.delete_loan(user_email, title)

    if result:
        flash(f'Loan record for "{title}" deleted.', 'info')
    else:
        flash(f'No loan record found for "{title}".', 'danger')

    return redirect(url_for('view_loans'))


# ---------- MAIN ----------
if __name__ == '__main__':
    app.run(debug=True)
