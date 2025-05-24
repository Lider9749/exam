from app import app, db, User, Role
from werkzeug.security import generate_password_hash

def add_admin():
    with app.app_context():
        # Проверяем существование роли администратора
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='Администратор')
            db.session.add(admin_role)
            db.session.commit()
            print("Роль администратора создана")

        # Проверяем существование пользователя admin
        admin = User.query.filter_by(login='admin').first()
        if not admin:
            admin = User(
                login='admin',
                password_hash=generate_password_hash('admin123'),
                first_name='Администратор',
                last_name='Системы',
                role=admin_role
            )
            db.session.add(admin)
            db.session.commit()
            print("Пользователь admin создан успешно!")
        else:
            print("Пользователь admin уже существует!")

if __name__ == '__main__':
    add_admin() 