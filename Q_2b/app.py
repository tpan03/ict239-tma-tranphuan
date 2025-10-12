from flask import Flask, render_template, request, redirect, url_for, session, flash
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
    categories = sorted(db["books"].distinct("category"))  # ✅ lowercase
    client.close()

    return render_template(
        'index.html',
        books=books,
        categories=categories,
        selected_category=category,
        total=count
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
    book = db["books"].find_one({"title": title}, {"_id": 0})  # ✅ lowercase
    client.close()
    return render_template('book_detail.html', book=book)

# ---------- ADD NEW BOOK (ADMIN ONLY) ----------
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
        db.books.insert_one({                      # ✅ lowercase collection
            'title': title,
            'category': category,
            'url': cover_url,                      # ✅ consistent with index.html
            'description': [description],          # ✅ stored as list
            'pages': int(pages),
            'copies': int(copies),
            'available': int(copies),
            'genres': genres,
            'authors': [a['name'] for a in authors]  # ✅ same format as all_books
        })
        client.close()

        flash(f'"{title}" has been successfully added!', 'success')
        return redirect(url_for('new_book'))

    return render_template('new_book.html', genres=genres_list)

if __name__ == '__main__':
    app.run(debug=True)
