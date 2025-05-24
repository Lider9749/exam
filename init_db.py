from app import app, db, User, Role, Book, Genre, ReviewStatus
from werkzeug.security import generate_password_hash
from datetime import datetime

def init_db():
    with app.app_context():
        # Создаем таблицы
        db.create_all()

        # Создаем роли
        roles = {
            'Администратор': 'Полный доступ к системе',
            'Модератор': 'Может редактировать книги и модерировать рецензии',
            'Пользователь': 'Может оставлять рецензии'
        }
        
        for name, description in roles.items():
            if not Role.query.filter_by(name=name).first():
                role = Role(name=name, description=description)
                db.session.add(role)
        
        # Создаем статусы рецензий
        statuses = ['На рассмотрении', 'Одобрено', 'Отклонено']
        for status in statuses:
            if not ReviewStatus.query.filter_by(name=status).first():
                review_status = ReviewStatus(name=status)
                db.session.add(review_status)

        # Создаем администратора
        if not User.query.filter_by(login='admin').first():
            admin = User(
                login='admin',
                password_hash=generate_password_hash('admin123'),
                last_name='Администратор',
                first_name='Системный',
                role=Role.query.filter_by(name='Администратор').first()
            )
            db.session.add(admin)

        # Создаем жанры
        genres = [
            'Программирование',
            'Базы данных',
            'Сети',
            'Безопасность',
            'Искусственный интеллект',
            'Веб-разработка',
            'Мобильная разработка',
            'DevOps',
            'Тестирование',
            'Управление проектами'
        ]
        
        for genre_name in genres:
            if not Genre.query.filter_by(name=genre_name).first():
                genre = Genre(name=genre_name)
                db.session.add(genre)

        # Создаем тестовые книги
        books = [
            {
                'title': 'Как я перестал бояться и полюбил баг',
                'description': 'Захватывающая история о том, как один разработчик научился жить в гармонии с ошибками в коде. От отчаяния до принятия - путь длиною в тысячу багов.',
                'year': 2023,
                'publisher': 'Издательство "Нет багов"',
                'author': 'Джон Бугхантер',
                'pages': 420,
                'genres': ['Программирование', 'Тестирование']
            },
            {
                'title': 'Git: Путь самурая',
                'description': 'Древние секреты управления версиями, переданные от мастера к ученику. Как правильно делать коммиты, чтобы не прослыть варваром в мире разработки.',
                'year': 2022,
                'publisher': 'Издательство "Версионный контроль"',
                'author': 'Мастер Гит',
                'pages': 666,
                'genres': ['DevOps', 'Управление проектами']
            },
            {
                'title': 'SQL: Искусство запросов',
                'description': 'Как заставить базу данных танцевать под вашу дудку. От простых SELECT до сложных JOIN - путь к просветлению в мире данных.',
                'year': 2023,
                'publisher': 'Издательство "База знаний"',
                'author': 'Алиса в стране баз данных',
                'pages': 333,
                'genres': ['Базы данных']
            },
            {
                'title': 'Python: Змеиный клуб',
                'description': 'История о том, как один язык программирования покорил мир. От простых скриптов до искусственного интеллекта - путь Python к славе.',
                'year': 2022,
                'publisher': 'Издательство "Питон"',
                'author': 'Гвидо ван Россум',
                'pages': 999,
                'genres': ['Программирование', 'Искусственный интеллект']
            },
            {
                'title': 'JavaScript: Танцы с браузером',
                'description': 'Как заставить браузер делать то, что вы хотите, а не то, что он хочет. От простых анимаций до сложных SPA - путь к мастерству.',
                'year': 2023,
                'publisher': 'Издательство "Веб-магия"',
                'author': 'Брендан Эйх',
                'pages': 777,
                'genres': ['Веб-разработка', 'Программирование']
            },
            {
                'title': 'Docker: Контейнеры для чайников',
                'description': 'Как упаковать ваше приложение в контейнер и не сойти с ума. От простых образов до оркестрации - путь к контейнеризации.',
                'year': 2023,
                'publisher': 'Издательство "Контейнеры"',
                'author': 'Капитан Докер',
                'pages': 444,
                'genres': ['DevOps']
            },
            {
                'title': 'React: Путь джедая',
                'description': 'Как освоить силу компонентов и не поддаться темной стороне пропсов. От простых компонентов до сложных хуков - путь к мастерству.',
                'year': 2023,
                'publisher': 'Издательство "Фронтенд"',
                'author': 'Люк Скайуокер',
                'pages': 888,
                'genres': ['Веб-разработка']
            },
            {
                'title': 'Алгоритмы: Танцы с данными',
                'description': 'Как заставить данные танцевать под вашу дудку. От простых сортировок до сложных графов - путь к алгоритмическому просветлению.',
                'year': 2022,
                'publisher': 'Издательство "Алгоритмы"',
                'author': 'Дональд Кнут',
                'pages': 1111,
                'genres': ['Программирование']
            },
            {
                'title': 'Безопасность: Искусство защиты',
                'description': 'Как защитить свой код от злоумышленников и не сойти с ума. От простых паролей до сложных шифрований - путь к безопасности.',
                'year': 2023,
                'publisher': 'Издательство "Безопасность"',
                'author': 'Алан Тьюринг',
                'pages': 555,
                'genres': ['Безопасность']
            },
            {
                'title': 'ИИ: Когда роботы захватят мир',
                'description': 'Юмористический взгляд на будущее искусственного интеллекта. От простых нейросетей до сложных алгоритмов - путь к сингулярности.',
                'year': 2023,
                'publisher': 'Издательство "Роботы"',
                'author': 'Илон Маск',
                'pages': 666,
                'genres': ['Искусственный интеллект']
            }
        ]

        for book_data in books:
            if not Book.query.filter_by(title=book_data['title']).first():
                book = Book(
                    title=book_data['title'],
                    description=book_data['description'],
                    year=book_data['year'],
                    publisher=book_data['publisher'],
                    author=book_data['author'],
                    pages=book_data['pages']
                )
                for genre_name in book_data['genres']:
                    genre = Genre.query.filter_by(name=genre_name).first()
                    if genre:
                        book.genres.append(genre)
                db.session.add(book)

        # Сохраняем изменения
        db.session.commit()

if __name__ == '__main__':
    init_db()
    print("База данных успешно инициализирована!") 