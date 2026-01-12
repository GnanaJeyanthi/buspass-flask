from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = 'secretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///buspass.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ------------------ MAIL CONFIG -------------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'jeyanthi282005@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'efpk puwx zzrs wusp'          # Replace with your app password

db = SQLAlchemy(app)
mail = Mail(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ------------------ MODELS -------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    regno = db.Column(db.String(20), unique=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(10), default='student')  # student/admin
    buspasses = db.relationship('BusPass', backref='student')

class Route(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    route_no = db.Column(db.String(10))
    start_point = db.Column(db.String(50))
    end_point = db.Column(db.String(50))
    capacity = db.Column(db.Integer)
    buspasses = db.relationship('BusPass', backref='route')

class BusPass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'))
    status = db.Column(db.String(20), default='Applied')  # Applied, Assigned, Rejected

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------ HOME -------------------
@app.route('/')
def home():
    return render_template('home.html')

# ------------------ AUTH -------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        regno = request.form['regno']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        # Check if regno or email already exists
        existing_user = User.query.filter((User.regno == regno) | (User.email == email)).first()
        if existing_user:
            if existing_user.regno == regno:
                flash('Registration number already exists. Please use a different one.')
            else:
                flash('Email already exists. Please use a different one.')
            return redirect(url_for('register'))

        user = User(name=name, email=email, regno=regno, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('apply'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.')
    return redirect(url_for('home'))

# ------------------ STUDENT FEATURES -------------------
@app.route('/apply', methods=['GET', 'POST'])
@login_required
def apply():
    if current_user.role != 'student':
        return redirect(url_for('admin_dashboard'))
    routes = Route.query.all()
    if request.method == 'POST':
        route_id = request.form['route_id']
        existing = BusPass.query.filter_by(student_id=current_user.id).first()
        if existing:
            flash('You already applied for a bus pass!')
            return redirect(url_for('status'))
        buspass = BusPass(student_id=current_user.id, route_id=route_id)
        db.session.add(buspass)
        db.session.commit()
        flash('Bus pass applied successfully!')
        return redirect(url_for('status'))
    return render_template('apply.html', routes=routes)

@app.route('/status')
@login_required
def status():
    buspass = BusPass.query.filter_by(student_id=current_user.id).first()
    return render_template('status.html', buspass=buspass)

# ------------------ ADMIN FEATURES -------------------
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, role='admin').first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials!')
    return render_template('admin_login.html')

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    status_filter = request.args.get('status')
    search_query = request.args.get('search')
    query = BusPass.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if search_query:
        query = query.join(User).filter(
            (User.name.ilike(f'%{search_query}%')) | (User.regno.ilike(f'%{search_query}%'))
        )
    applications = query.all()
    routes = Route.query.all()
    return render_template('admin_dashboard.html', applications=applications, routes=routes, status_filter=status_filter, search_query=search_query)

@app.route('/add_route', methods=['GET', 'POST'])
@login_required
def add_route():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    if request.method == 'POST':
        route_no = request.form['route_no']
        start_point = request.form['start_point']
        end_point = request.form['end_point']
        capacity = int(request.form['capacity'])
        route = Route(route_no=route_no, start_point=start_point, end_point=end_point, capacity=capacity)
        db.session.add(route)
        db.session.commit()
        flash('Route added successfully!')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_route.html')

@app.route('/update_route/<int:route_id>', methods=['GET', 'POST'])
@login_required
def update_route(route_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    route = Route.query.get(route_id)
    if request.method == 'POST':
        route.route_no = request.form['route_no']
        route.start_point = request.form['start_point']
        route.end_point = request.form['end_point']
        route.capacity = int(request.form['capacity'])
        db.session.commit()
        flash('Route updated successfully!')
        return redirect(url_for('admin_dashboard'))
    return render_template('update_route.html', route=route)

@app.route('/delete_route/<int:route_id>')
@login_required
def delete_route(route_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    route = Route.query.get(route_id)
    if route:
        db.session.delete(route)
        db.session.commit()
        flash('Route deleted successfully!')
    else:
        flash('Route not found!')
    return redirect(url_for('admin_dashboard'))

@app.route('/approve/<int:pass_id>')
@login_required
def approve(pass_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))

    buspass = BusPass.query.get(pass_id)
    route = Route.query.get(buspass.route_id)

    # Count already assigned bus passes for this route
    assigned_count = BusPass.query.filter_by(route_id=route.id, status='Assigned').count()

    if assigned_count < route.capacity:
        buspass.status = 'Assigned'
        db.session.commit()
        send_email(buspass)
        flash('Bus pass approved and email sent!')
    else:
        flash(f'Cannot approve! Route {route.route_no} is full ({route.capacity} seats).')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/reject/<int:pass_id>')
@login_required
def reject(pass_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    buspass = BusPass.query.get(pass_id)
    buspass.status = 'Rejected'
    db.session.commit()
    send_email(buspass)
    flash('Application rejected and email sent.')
    return redirect(url_for('admin_dashboard'))

@app.route('/update_status/<int:pass_id>', methods=['GET', 'POST'])
@login_required
def update_status(pass_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    buspass = BusPass.query.get(pass_id)
    if request.method == 'POST':
        new_status = request.form['status']
        old_status = buspass.status
        buspass.status = new_status
        db.session.commit()
        if new_status != old_status:
            send_email(buspass)
            flash(f'Status updated to {new_status} and email sent.')
        else:
            flash(f'Status updated to {new_status}.')
        return redirect(url_for('admin_dashboard'))
    return render_template('update_status.html', buspass=buspass)

@app.route('/delete_pass/<int:pass_id>')
@login_required
def delete_pass(pass_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    buspass = BusPass.query.get(pass_id)
    if buspass:
        db.session.delete(buspass)
        db.session.commit()
        flash('Application deleted successfully.')
    else:
        flash('Application not found.')
    return redirect(url_for('admin_dashboard'))

# ------------------ EMAIL -------------------
def send_email(buspass):
    student = User.query.get(buspass.student_id)
    route = Route.query.get(buspass.route_id)
    status = 'Approved' if buspass.status == 'Assigned' else 'Rejected'
    msg = Message(f'Bus Pass {status}', sender=app.config['MAIL_USERNAME'], recipients=[student.email])
    msg.html = render_template('email_template.html', name=student.name, route_no=route.route_no, start_point=route.start_point, end_point=route.end_point, status=status)
    mail.send(msg)

# ------------------ DB SEED -------------------
def create_tables():
    db.create_all()
    if not Route.query.first():
        r1 = Route(route_no='R1', start_point='Chennai', end_point='Madurai', capacity=5)
        r2 = Route(route_no='R2', start_point='Chennai', end_point='Bangalore', capacity=5)
        db.session.add_all([r1, r2])
    if not User.query.filter_by(role='admin').first():
        admin = User(
            name='Admin',
            email='admin@gmail.com',
            password=bcrypt.generate_password_hash('admin123').decode('utf-8'),
            role='admin',
            regno='ADMIN01'
        )
        db.session.add(admin)
    db.session.commit()

# ------------------ APP INIT -------------------
with app.app_context():
    create_tables()
    print("✅ Tables created and default admin added (email: admin@gmail.com, password: admin123)")

if __name__ == "__main__":
    app.run(debug=True)
