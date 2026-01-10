import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)

# -------------------------------------------------
# APP CONFIG
# -------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret")

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///buspass.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail (ENV only – Render compatible)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

# -------------------------------------------------
# EXTENSIONS
# -------------------------------------------------
db = SQLAlchemy(app)
mail = Mail(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# -------------------------------------------------
# MODELS
# -------------------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    regno = db.Column(db.String(20), unique=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(10), default='student')  # student / admin


class Route(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    route_no = db.Column(db.String(10))
    start_point = db.Column(db.String(50))
    end_point = db.Column(db.String(50))
    capacity = db.Column(db.Integer)


class BusPass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'))
    status = db.Column(db.String(20), default='Applied')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------------------------------
# ROUTES
# -------------------------------------------------
@app.route('/')
def home():
    return render_template('home.html')


# ---------------- USER AUTH ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(
            email=request.form['email'],
            role='student'
        ).first()

        if user and bcrypt.check_password_hash(
            user.password, request.form['password']
        ):
            login_user(user)
            return redirect(url_for('apply'))

        flash('Invalid user credentials')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        password = bcrypt.generate_password_hash(
            request.form['password']
        ).decode('utf-8')

        user = User(
            name=request.form['name'],
            email=request.form['email'],
            regno=request.form['regno'],
            password=password,
            role='student'
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful')
        return redirect(url_for('login'))

    return render_template('register.html')


# ---------------- ADMIN AUTH ----------------
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin = User.query.filter_by(
            email=request.form['email'],
            role='admin'
        ).first()

        if admin and bcrypt.check_password_hash(
            admin.password, request.form['password']
        ):
            login_user(admin)
            return redirect(url_for('admin_dashboard'))

        flash('Invalid admin credentials')

    return render_template('admin_login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


# ---------------- STUDENT ----------------
@app.route('/apply')
@login_required
def apply():
    if current_user.role != 'student':
        return redirect(url_for('admin_dashboard'))
    routes = Route.query.all()
    return render_template('apply.html', routes=routes)


# ---------------- ADMIN ----------------
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    applications = BusPass.query.all()
    routes = Route.query.all()
    return render_template(
        'admin_dashboard.html',
        applications=applications,
        routes=routes
    )

# -------------------------------------------------
# EMAIL (optional)
# -------------------------------------------------
def send_email():
    if not app.config['MAIL_USERNAME']:
        return
    msg = Message(
        "Bus Pass Update",
        sender=app.config['MAIL_USERNAME'],
        recipients=["test@example.com"]
    )
    msg.body = "Status updated"
    mail.send(msg)

# -------------------------------------------------
# DB INIT
# -------------------------------------------------
with app.app_context():
    db.create_all()

    # default admin
    if not User.query.filter_by(role='admin').first():
        admin = User(
            name="Admin",
            email="admin@gmail.com",
            regno="ADMIN01",
            role="admin",
            password=bcrypt.generate_password_hash("admin123").decode("utf-8")
        )
        db.session.add(admin)

    db.session.commit()

# -------------------------------------------------
# START
# -------------------------------------------------
if __name__ == "__main__":
    app.run()
