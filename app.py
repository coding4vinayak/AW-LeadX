from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_migrate import Migrate
from dotenv import load_dotenv
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_caching import Cache
from flask_session import Session
import os

# Load environment variables
load_dotenv()

# Ensure the instance folder exists before initializing the app
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
os.makedirs(instance_path, exist_ok=True)

app = Flask(__name__, instance_path=instance_path)

# Load the appropriate configuration
env = os.getenv('FLASK_ENV', 'development')
if env == 'production':
    app.config.from_object('config.ProductionConfig')
else:
    app.config.from_object('config.DevelopmentConfig')

# Initialize Simple Cache
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['SESSION_TYPE'] = 'filesystem'
cache = Cache(app)

# Initialize Flask-Session
Session(app)

# Initialize database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# User Model for MySQL
class MySQLUser(db.Model):
    __bind_key__ = 'leads'
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(120))
    role = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Lead Model
class Lead(db.Model):
    __bind_key__ = 'leads'
    __tablename__ = 'lead'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    stage = db.Column(db.String(50), default='New')
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    is_custom = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship('MySQLUser', foreign_keys=[created_by_id], backref=db.backref('created_leads', lazy=True, cascade='all, delete-orphan'))
    assigned_to = db.relationship('MySQLUser', foreign_keys=[assigned_to_id], backref=db.backref('assigned_leads', lazy=True))

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='client')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Initialize databases
with app.app_context():
    try:
        # Create tables for SQLite database (User model)
        db.create_all()
        print('SQLite database initialized successfully')

        # Create default admin user if it doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(username='admin', email='admin@example.com', role='admin')
            admin_user.set_password('admin')
            db.session.add(admin_user)
            db.session.commit()
            print('Default admin user created successfully')

        # Create tables for MySQL database (Lead and MySQLUser models)
        if 'leads' in app.config['SQLALCHEMY_BINDS']:
            try:
                leads_engine = db.engines['leads']
                # First create the user table in MySQL
                db.Table('user', db.metadata,
                    db.Column('id', db.Integer, primary_key=True),
                    db.Column('username', db.String(80)),
                    db.Column('email', db.String(120)),
                    db.Column('role', db.String(20)),
                    db.Column('created_at', db.DateTime, default=datetime.utcnow),
                    extend_existing=True
                ).create(bind=leads_engine, checkfirst=True)
                
                # Then create MySQLUser and Lead tables
                MySQLUser.__table__.create(bind=leads_engine, checkfirst=True)
                Lead.__table__.create(bind=leads_engine, checkfirst=True)
                print('MySQL database initialized successfully')
            except Exception as mysql_error:
                print(f'Error initializing MySQL database: {str(mysql_error)}')
                app.config['SQLALCHEMY_BINDS'] = {}
                print('Disabled MySQL bindings due to connection error...')
    except Exception as e:
        print(f'Error initializing database: {str(e)}')
        app.config['SQLALCHEMY_BINDS'] = {}
        print('Falling back to SQLite only mode...')


# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

# Routes
@app.route('/')
@login_required
def index():
    try:
        if current_user.role == 'admin':
            leads = Lead.query.order_by(Lead.created_at.desc()).all()
            users = User.query.filter_by(role='client').all()
        else:
            leads = Lead.query.filter_by(assigned_to_id=current_user.id).order_by(Lead.created_at.desc()).all()
            users = []
        return render_template('index.html', leads=leads, users=users)
    except Exception as e:
        print(f'Error accessing leads database: {str(e)}')
        flash('Unable to access leads database. Please try again later.', 'danger')
        return render_template('index.html', leads=[], users=[])

@app.route('/clients')
@login_required
def client_list():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    try:
        if not app.config['SQLALCHEMY_BINDS']:
            flash('Database connection is currently unavailable. Please try again later.', 'danger')
            return redirect(url_for('index'))
        clients = MySQLUser.query.filter_by(role='client').all()
        return render_template('client_list.html', clients=clients)
    except Exception as e:
        print(f'Error accessing client database: {str(e)}')
        flash('Unable to access client database. Please try again later.', 'danger')
        return redirect(url_for('index'))

@app.route('/api/unassigned_leads')
@login_required
def get_unassigned_leads():
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    leads = Lead.query.filter_by(assigned_to_id=None).all()
    return jsonify([{
        'id': lead.id,
        'name': lead.name,
        'company': lead.company
    } for lead in leads])

@app.route('/api/leads/<int:lead_id>/assign', methods=['POST'])
@login_required
def assign_lead(lead_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    if not data or 'user_id' not in data:
        return jsonify({'error': 'User ID is required'}), 400
    
    lead = Lead.query.get_or_404(lead_id)
    user = MySQLUser.query.get_or_404(data['user_id'])
    
    if user.role != 'client':
        return jsonify({'error': 'Can only assign leads to clients'}), 400
    
    lead.assigned_to_id = user.id
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/lead/new', methods=['GET', 'POST'])
@login_required
def new_lead():
    if request.method == 'POST':
        lead = Lead(
            name=request.form['name'],
            company=request.form['company'],
            email=request.form['email'],
            phone=request.form['phone'],
            notes=request.form['notes'],
            created_by_id=current_user.id,
            assigned_to_id=current_user.id if current_user.role == 'client' else None,
            is_custom=current_user.role == 'client'
        )
        db.session.add(lead)
        db.session.commit()
        flash('Lead added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('new_lead.html')

@app.route('/lead/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_lead(id):
    lead = Lead.query.get_or_404(id)
    if request.method == 'POST':
        lead.name = request.form['name']
        lead.company = request.form['company']
        lead.email = request.form['email']
        lead.phone = request.form['phone']
        lead.notes = request.form['notes']
        db.session.commit()
        flash('Lead updated successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('edit_lead.html', lead=lead)

@app.route('/lead/<int:id>/stage', methods=['POST'])
@login_required
def update_stage(id):
    lead = Lead.query.get_or_404(id)
    lead.stage = request.form['stage']
    db.session.commit()
    flash('Lead stage updated successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    return render_template('dashboard.html', tables=tables)

@app.route('/dashboard/<table_name>')
@login_required
def view_table(table_name):
    if not current_user.role == 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    try:
        # Handle user table from SQLite database
        if table_name == 'user':
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
        # Handle tables from MySQL database
        elif 'leads' in app.config['SQLALCHEMY_BINDS']:
            inspector = db.inspect(db.engines['leads'])
            tables = inspector.get_table_names()
        else:
            flash('Database connection error', 'error')
            return redirect(url_for('dashboard'))

        if table_name not in tables:
            flash('Table not found', 'error')
            return redirect(url_for('dashboard'))
        
        # Get table columns and data
        if table_name == 'user':
            table = db.Table(table_name, db.metadata, autoload_with=db.engine)
        else:
            table = db.Table(table_name, db.metadata, autoload_with=db.engines['leads'])
            
        columns = [col.name for col in table.columns]
        
        # Execute select query
        result = db.session.execute(db.select(table))
        rows = [dict(row) for row in result]
    except Exception as e:
        flash(f'Error accessing database: {str(e)}', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('dashboard.html', 
                          tables=tables,
                          current_table=table_name,
                          columns=columns,
                          rows=rows)

@app.route('/dashboard/<table_name>/add', methods=['POST'])
def add_row(table_name):
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    if table_name not in tables:
        flash('Table not found', 'error')
        return redirect(url_for('dashboard'))
    
    table = db.Table(table_name, db.metadata, autoload_with=db.engine)
    data = {key: value for key, value in request.form.items() if key != 'id'}
    
    try:
        db.session.execute(table.insert().values(**data))
        db.session.commit()
        flash('Row added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding row: {str(e)}', 'error')
    
    return redirect(url_for('view_table', table_name=table_name))

@app.route('/dashboard/<table_name>/delete/<int:id>', methods=['POST'])
def delete_row(table_name, id):
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    if table_name not in tables:
        flash('Table not found', 'error')
        return redirect(url_for('dashboard'))
    
    table = db.Table(table_name, db.metadata, autoload_with=db.engine)
    try:
        db.session.execute(table.delete().where(table.c.id == id))
        db.session.commit()
        flash('Row deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting row: {str(e)}', 'error')
    
    return redirect(url_for('view_table', table_name=table_name))

# API Routes
@app.route('/api/leads', methods=['GET'])
@login_required
def get_leads():
    try:
        leads = Lead.query.order_by(Lead.created_at.desc()).all()
        return jsonify([{
            'id': lead.id,
            'name': lead.name,
            'company': lead.company,
            'email': lead.email,
            'phone': lead.phone,
            'stage': lead.stage,
            'notes': lead.notes,
            'created_at': lead.created_at.isoformat(),
            'updated_at': lead.updated_at.isoformat()
        } for lead in leads])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/leads/<int:id>', methods=['GET'])
@login_required
def get_lead(id):
    try:
        lead = Lead.query.get_or_404(id)
        return jsonify({
            'id': lead.id,
            'name': lead.name,
            'company': lead.company,
            'email': lead.email,
            'phone': lead.phone,
            'stage': lead.stage,
            'notes': lead.notes,
            'created_at': lead.created_at.isoformat(),
            'updated_at': lead.updated_at.isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/leads', methods=['POST'])
@login_required
def create_lead():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.get_json()
    
    if 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    
    try:
        lead = Lead(
            name=data.get('name'),
            company=data.get('company'),
            email=data.get('email'),
            phone=data.get('phone'),
            notes=data.get('notes'),
            stage=data.get('stage', 'New'),
            created_by_id=current_user.id,
            assigned_to_id=current_user.id if current_user.role == 'client' else None,
            is_custom=current_user.role == 'client'
        )
        
        db.session.add(lead)
        db.session.commit()
        return jsonify({
            'id': lead.id,
            'name': lead.name,
            'company': lead.company,
            'email': lead.email,
            'phone': lead.phone,
            'stage': lead.stage,
            'notes': lead.notes,
            'created_at': lead.created_at.isoformat(),
            'updated_at': lead.updated_at.isoformat()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/leads/<int:id>', methods=['PUT'])
def update_lead_api(id):
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    lead = Lead.query.get_or_404(id)
    data = request.get_json()
    
    try:
        if 'name' in data:
            lead.name = data['name']
        if 'company' in data:
            lead.company = data['company']
        if 'email' in data:
            lead.email = data['email']
        if 'phone' in data:
            lead.phone = data['phone']
        if 'notes' in data:
            lead.notes = data['notes']
        if 'stage' in data:
            lead.stage = data['stage']
        
        db.session.commit()
        return jsonify({
            'id': lead.id,
            'name': lead.name,
            'company': lead.company,
            'email': lead.email,
            'phone': lead.phone,
            'stage': lead.stage,
            'notes': lead.notes,
            'created_at': lead.created_at.isoformat(),
            'updated_at': lead.updated_at.isoformat()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/leads/<int:id>', methods=['DELETE'])
def delete_lead_api(id):
    lead = Lead.query.get_or_404(id)
    try:
        db.session.delete(lead)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('index'))
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = 'remember' in request.form
        
        user = User.query.filter_by(username=username, role='admin').first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        
        flash('Invalid administrator credentials', 'danger')
    return render_template('admin_login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = 'remember' in request.form
        
        user = User.query.filter_by(username=username, role='client').first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Only allow admin users to access the registration page
    if not current_user.is_authenticated or current_user.role != 'admin':
        flash('Only administrators can register new users', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form.get('role', 'client')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('register.html')
        
        try:
            # Create SQLite user for authentication
            user = User(username=username, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            
            # Create MySQL user for lead relationships
            mysql_user = MySQLUser(username=username, email=email, role=role)
            db.session.add(mysql_user)
            
            db.session.commit()
            
            flash('User registration successful!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Registration failed: {str(e)}', 'danger')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        try:
            # Create tables for SQLite database (User model)
            db.create_all()
            print('SQLite database initialized successfully')
            
            # Create tables for MySQL database (Lead model)
            if 'leads' in app.config['SQLALCHEMY_BINDS']:
                try:
                    leads_engine = db.engines['leads']
                    MySQLUser.__table__.create(bind=leads_engine, checkfirst=True)
                    Lead.__table__.create(bind=leads_engine, checkfirst=True)
                    print('MySQL database initialized successfully')
                except Exception as mysql_error:
                    print(f'Error initializing MySQL database: {str(mysql_error)}')
                    print('Continuing with SQLite database only...')
        except Exception as e:
            print(f'Error initializing database: {str(e)}')
            if 'SQLite' in str(e):
                print('Error with SQLite database initialization')
            elif 'MySQL' in str(e):
                print('Error with MySQL database initialization')
                print('Continuing with SQLite database only...')
            else:
                print('Unknown database error occurred')

    app.run(debug=True)