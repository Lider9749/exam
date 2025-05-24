from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import hashlib
from dotenv import load_dotenv
import bleach
import csv
from io import StringIO

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql+psycopg2://user:password@localhost/library')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Инициализация расширений
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Модели данных
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    role = db.relationship('Role')
    reviews = db.relationship('Review', backref='user', lazy=True)
    visits = db.relationship('Visit', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.Text)
    users = db.relationship('User', backref='role_backref', lazy=True)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    publisher = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    pages = db.Column(db.Integer, nullable=False)
    cover_id = db.Column(db.Integer, db.ForeignKey('cover.id'))
    reviews = db.relationship('Review', backref='book', lazy=True)
    genres = db.relationship('Genre', secondary='book_genre', backref='books')
    visits = db.relationship('Visit', backref='book', lazy=True)

class Genre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

class Cover(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    md5_hash = db.Column(db.String(32), nullable=False)
    book = db.relationship('Book', backref='cover', uselist=False)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status_id = db.Column(db.Integer, db.ForeignKey('review_status.id'), nullable=False, default=1)
    status = db.relationship('ReviewStatus', backref='reviews')

class ReviewStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    visited_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# Связующая таблица для связи многие-ко-многим между книгами и жанрами
book_genre = db.Table('book_genre',
    db.Column('book_id', db.Integer, db.ForeignKey('book.id'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('genre.id'), primary_key=True)
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def get_file_hash(file):
    """Вычисляет MD5-хэш файла"""
    md5_hash = hashlib.md5()
    for chunk in iter(lambda: file.read(4096), b""):
        md5_hash.update(chunk)
    file.seek(0)  # Возвращаем указатель в начало файла
    return md5_hash.hexdigest()

# Маршруты
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    
    # Получаем параметры поиска
    title = request.args.get('title', '')
    author = request.args.get('author', '')
    genres = request.args.getlist('genres')
    years = request.args.getlist('year')
    pages_from = request.args.get('pages_from', type=int)
    pages_to = request.args.get('pages_to', type=int)
    
    # Базовый запрос
    query = Book.query
    
    # Применяем фильтры
    if title:
        query = query.filter(Book.title.ilike(f'%{title}%'))
    if author:
        query = query.filter(Book.author.ilike(f'%{author}%'))
    if genres:
        query = query.filter(Book.genres.any(Genre.id.in_(genres)))
    if years:
        query = query.filter(Book.year.in_(years))
    if pages_from is not None:
        query = query.filter(Book.pages >= pages_from)
    if pages_to is not None:
        query = query.filter(Book.pages <= pages_to)
    
    # Получаем уникальные годы для фильтра
    years = db.session.query(Book.year).distinct().order_by(Book.year.desc()).all()
    years = [year[0] for year in years]
    
    # Получаем все жанры для фильтра
    genres = Genre.query.all()
    
    # Сортируем и пагинируем результаты
    books = query.order_by(Book.year.desc()).paginate(page=page, per_page=10)
    
    return render_template('index.html', books=books, genres=genres, years=years)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(login=login).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            return redirect(url_for('index'))
        
        flash('Невозможно аутентифицироваться с указанными логином и паролем')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/book/<int:book_id>')
def view_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    # Записываем посещение
    if current_user.is_authenticated:
        # Проверяем количество посещений за сегодня
        today = datetime.utcnow().date()
        visits_today = Visit.query.filter(
            Visit.book_id == book_id,
            Visit.user_id == current_user.id,
            db.func.date(Visit.visited_at) == today
        ).count()
        
        if visits_today < 10:
            visit = Visit(book_id=book_id, user_id=current_user.id)
            db.session.add(visit)
            db.session.commit()
    else:
        visit = Visit(book_id=book_id)
        db.session.add(visit)
        db.session.commit()
    
    # Проверяем, есть ли у текущего пользователя рецензия на эту книгу
    current_user_review = None
    if current_user.is_authenticated:
        current_user_review = Review.query.filter_by(
            book_id=book_id,
            user_id=current_user.id
        ).first()
    
    return render_template('view_book.html', book=book, current_user_review=current_user_review)

@app.route('/book/add', methods=['GET', 'POST'])
@login_required
def add_book():
    if current_user.role.name not in ['Администратор', 'Модератор']:
        flash('У вас недостаточно прав для выполнения данного действия')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            # Получаем данные формы
            title = request.form['title']
            description = bleach.clean(request.form['description'])
            year = int(request.form['year'])
            publisher = request.form['publisher']
            author = request.form['author']
            pages = int(request.form['pages'])
            genre_ids = request.form.getlist('genres')
            
            # Проверяем файл обложки
            if 'cover' not in request.files:
                flash('Необходимо загрузить обложку')
                return redirect(request.url)
            
            file = request.files['cover']
            if file.filename == '':
                flash('Не выбран файл обложки')
                return redirect(request.url)
            
            if not allowed_file(file.filename):
                flash('Недопустимый формат файла')
                return redirect(request.url)
            
            # Вычисляем MD5-хэш файла
            file_hash = get_file_hash(file)
            
            # Проверяем, есть ли уже такой файл
            existing_cover = Cover.query.filter_by(md5_hash=file_hash).first()
            if existing_cover:
                cover = existing_cover
            else:
                # Сохраняем файл
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                
                # Создаем запись в базе данных
                cover = Cover(
                    filename=filename,
                    mime_type=file.content_type,
                    md5_hash=file_hash
                )
                db.session.add(cover)
                db.session.flush()  # Получаем ID обложки
            
            # Создаем книгу
            book = Book(
                title=title,
                description=description,
                year=year,
                publisher=publisher,
                author=author,
                pages=pages,
                cover_id=cover.id
            )
            db.session.add(book)
            db.session.flush()  # Получаем ID книги
            
            # Добавляем жанры
            for genre_id in genre_ids:
                genre = Genre.query.get(genre_id)
                if genre:
                    book.genres.append(genre)
            
            db.session.commit()
            flash('Книга успешно добавлена')
            return redirect(url_for('view_book', book_id=book.id))
            
        except Exception as e:
            db.session.rollback()
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.')
            return redirect(request.url)
    
    genres = Genre.query.all()
    return render_template('book_form.html', genres=genres)

@app.route('/book/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    if current_user.role.name not in ['Администратор', 'Модератор']:
        flash('У вас недостаточно прав для выполнения данного действия')
        return redirect(url_for('index'))
    
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        try:
            # Получаем данные формы
            book.title = request.form['title']
            book.description = bleach.clean(request.form['description'])
            book.year = int(request.form['year'])
            book.publisher = request.form['publisher']
            book.author = request.form['author']
            book.pages = int(request.form['pages'])
            
            # Обновляем жанры
            book.genres = []
            for genre_id in request.form.getlist('genres'):
                genre = Genre.query.get(genre_id)
                if genre:
                    book.genres.append(genre)
            
            db.session.commit()
            flash('Книга успешно обновлена')
            return redirect(url_for('view_book', book_id=book.id))
            
        except Exception as e:
            db.session.rollback()
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.')
            return redirect(request.url)
    
    genres = Genre.query.all()
    return render_template('book_form.html', book=book, genres=genres)

@app.route('/book/<int:book_id>/delete', methods=['POST'])
@login_required
def delete_book(book_id):
    if current_user.role.name != 'Администратор':
        flash('У вас недостаточно прав для выполнения данного действия')
        return redirect(url_for('index'))
    
    book = Book.query.get_or_404(book_id)
    
    try:
        # Удаляем файл обложки
        if book.cover:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], book.cover.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Удаляем книгу (все связанные записи удалятся автоматически благодаря ON DELETE CASCADE)
        db.session.delete(book)
        db.session.commit()
        flash('Книга успешно удалена')
    except Exception as e:
        db.session.rollback()
        flash('При удалении книги возникла ошибка')
    
    return redirect(url_for('index'))

@app.route('/book/<int:book_id>/review/add', methods=['GET', 'POST'])
@login_required
def add_review(book_id):
    # Проверяем роль пользователя по id
    if current_user.role_id not in [4, 5, 6]:  # Администратор, Модератор, Пользователь
        flash('У вас недостаточно прав для выполнения данного действия')
        return redirect(url_for('index'))
    
    book = Book.query.get_or_404(book_id)
    
    # Проверяем, есть ли уже рецензия от этого пользователя
    existing_review = Review.query.filter_by(
        book_id=book_id,
        user_id=current_user.id
    ).first()
    
    if existing_review:
        flash('Вы уже оставили рецензию на эту книгу')
        return redirect(url_for('view_book', book_id=book_id))
    
    if request.method == 'POST':
        try:
            rating = int(request.form['rating'])
            text = bleach.clean(request.form['text'])
            
            # Получаем статус "На рассмотрении"
            status = ReviewStatus.query.filter_by(name='На рассмотрении').first()
            if not status:
                flash('Ошибка: статус рецензии не найден')
                return redirect(url_for('view_book', book_id=book_id))
            
            review = Review(
                book_id=book_id,
                user_id=current_user.id,
                rating=rating,
                text=text,
                status_id=status.id  # Устанавливаем начальный статус
            )
            db.session.add(review)
            db.session.commit()
            
            flash('Рецензия успешно добавлена и ожидает проверки модератором')
            return redirect(url_for('view_book', book_id=book_id))
            
        except Exception as e:
            db.session.rollback()
            flash('При сохранении рецензии возникла ошибка')
            return redirect(request.url)
    
    return render_template('add_review.html', book=book)

@app.route('/my-reviews')
@login_required
def my_reviews():
    # Проверяем роль пользователя по id
    if current_user.role_id != 6:  # Пользователь
        flash('У вас недостаточно прав для выполнения данного действия')
        return redirect(url_for('index'))
    
    try:
        reviews = Review.query.filter_by(user_id=current_user.id).order_by(Review.created_at.desc()).all()
        return render_template('my_reviews.html', reviews=reviews)
    except Exception as e:
        flash('При получении рецензий возникла ошибка')
        return redirect(url_for('index'))

@app.route('/moderate-reviews')
@login_required
def moderate_reviews():
    if current_user.role.name != 'Модератор':
        flash('У вас недостаточно прав для выполнения данного действия')
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)
    reviews = Review.query.filter_by(status_id=1).order_by(Review.created_at.desc()).paginate(page=page, per_page=10)
    return render_template('moderate_reviews.html', reviews=reviews)

@app.route('/review/<int:review_id>/moderate', methods=['POST'])
@login_required
def moderate_review(review_id):
    if current_user.role.name != 'Модератор':
        flash('У вас недостаточно прав для выполнения данного действия')
        return redirect(url_for('index'))
    
    review = Review.query.get_or_404(review_id)
    action = request.form.get('action')
    
    if action == 'approve':
        review.status_id = 2  # Одобрено
    elif action == 'reject':
        review.status_id = 3  # Отклонено
    
    db.session.commit()
    flash('Статус рецензии обновлен')
    return redirect(url_for('moderate_reviews'))

@app.route('/statistics')
@login_required
def statistics():
    # Проверяем роль пользователя по id
    if current_user.role_id != 4:  # Администратор
        flash('У вас недостаточно прав для выполнения данного действия')
        return redirect(url_for('index'))
    
    try:
        # Получаем параметры фильтрации
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Базовый запрос для статистики просмотров
        query = db.session.query(
            Book,
            db.func.count(Visit.id).label('visit_count')
        ).join(Visit)
        
        # Применяем фильтры по дате
        if date_from:
            query = query.filter(Visit.visited_at >= datetime.strptime(date_from, '%Y-%m-%d'))
        if date_to:
            query = query.filter(Visit.visited_at <= datetime.strptime(date_to, '%Y-%m-%d'))
        
        # Группируем и сортируем
        query = query.group_by(Book.id).order_by(db.desc('visit_count'))
        
        # Получаем результаты с пагинацией
        page = request.args.get('page', 1, type=int)
        stats = query.paginate(page=page, per_page=10)
        
        # Получаем журнал действий пользователей
        user_actions = db.session.query(
            Visit,
            User,
            Book
        ).join(
            Book, Visit.book_id == Book.id
        ).outerjoin(
            User, Visit.user_id == User.id
        ).order_by(
            Visit.visited_at.desc()
        ).paginate(page=page, per_page=10)
        
        return render_template('statistics.html', stats=stats, user_actions=user_actions)
    except Exception as e:
        flash(f'При получении статистики возникла ошибка: {str(e)}')
        return redirect(url_for('index'))

@app.route('/export/statistics')
@login_required
def export_statistics():
    if current_user.role.name != 'Администратор':
        flash('У вас недостаточно прав для выполнения данного действия')
        return redirect(url_for('index'))
    
    # Получаем параметры фильтрации
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Базовый запрос для статистики просмотров
    query = db.session.query(
        Book,
        db.func.count(Visit.id).label('visit_count')
    ).join(Visit)
    
    # Применяем фильтры по дате
    if date_from:
        query = query.filter(Visit.visited_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(Visit.visited_at <= datetime.strptime(date_to, '%Y-%m-%d'))
    
    # Группируем и сортируем
    query = query.group_by(Book.id).order_by(db.desc('visit_count'))
    
    # Создаем CSV
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Название книги', 'Количество просмотров'])
    
    for book, count in query.all():
        cw.writerow([book.title, count])
    
    output = si.getvalue()
    si.close()
    
    # Отправляем файл
    return send_file(
        StringIO(output),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'statistics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/export/user-actions')
@login_required
def export_user_actions():
    if current_user.role.name != 'Администратор':
        flash('У вас недостаточно прав для выполнения данного действия')
        return redirect(url_for('index'))
    
    # Получаем все действия пользователей
    actions = db.session.query(
        Visit,
        User,
        Book
    ).join(
        Book, Visit.book_id == Book.id
    ).outerjoin(
        User, Visit.user_id == User.id
    ).order_by(
        Visit.visited_at.desc()
    ).all()
    
    # Создаем CSV
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['№', 'Пользователь', 'Книга', 'Дата и время'])
    
    for i, (visit, user, book) in enumerate(actions, 1):
        user_name = f"{user.last_name} {user.first_name}" if user else "Неаутентифицированный пользователь"
        cw.writerow([i, user_name, book.title, visit.visited_at.strftime('%d.%m.%Y %H:%M:%S')])
    
    output = si.getvalue()
    si.close()
    
    # Отправляем файл
    return send_file(
        StringIO(output),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'user_actions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            login = request.form['login']
            password = request.form['password']
            last_name = request.form['last_name']
            first_name = request.form['first_name']
            middle_name = request.form.get('middle_name')
            
            # Проверяем, не занят ли логин
            if User.query.filter_by(login=login).first():
                flash('Пользователь с таким логином уже существует')
                return redirect(url_for('register'))
            
            # Создаем нового пользователя
            user = User(
                login=login,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                role=Role.query.filter_by(name='Пользователь').first()
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            flash('Регистрация успешна. Теперь вы можете войти в систему.')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash('При регистрации возникла ошибка')
            return redirect(url_for('register'))
    
    return render_template('register.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 