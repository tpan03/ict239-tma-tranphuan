from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from book import Book
from user import User

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Required for session

# Initialize database collections
Book.initialize_collection()

@app.context_processor
def inject_user():
    """Make the current user available in all templates."""
    return dict(current_user=session.get("user"))

# ---------- HOME / BOOK TITLES ----------
@app.route('/')
def index():
    category = request.args.get('category', 'All')
    books = Book.get_books_by_category(category)
    count = len(books)

    client = MongoClient("mongodb://localhost:27017/")
    db = client["libraryDB"]
    categories = sorted(db["Book"].distinct("category"))
    client.close()

    return render_template(
        'index.html',
        books=books,
        categories=categories,
        selected_category=category,
        count=count
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
        else:
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
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid email or password")
    return render_template('login.html')

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

# ---------- BOOK DETAILS ----------
@app.route('/book/<string:title>')
def book_detail(title):
    client = MongoClient("mongodb://localhost:27017/")
    db = client["libraryDB"]
    book = db["Book"].find_one({"title": title}, {"_id": 0})
    client.close()
    return render_template('book_detail.html', book=book)

if __name__ == '__main__':
    app.run(debug=True)
