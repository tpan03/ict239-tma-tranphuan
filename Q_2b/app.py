from flask import Flask, render_template, request
from books import all_books as books

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    category = request.form.get('category', 'All')
    if category == 'All':
        filtered = sorted(books, key=lambda x: x['title'])
    else:
        filtered = sorted(
            [b for b in books if b['category'] == category],
            key=lambda x: x['title']
        )
    return render_template('index.html',
                           books=filtered,
                           total=len(filtered),
                           category=category)

@app.route('/book/<title>')
def book_detail(title):
    book = next((b for b in books if b['title'] == title), None)
    return render_template('book_detail.html', book=book)

if __name__ == '__main__':
    app.run(debug=True)
