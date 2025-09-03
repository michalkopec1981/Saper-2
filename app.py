from gevent import monkey
monkey.patch_all()

import os
import random
from flask import Flask, render_template, request, jsonify, url_for, session, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

# Inicjalizacja
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'bardzo-tajny-klucz-super-bezpieczny')
app.config['UPLOAD_FOLDER'] = 'static/uploads/logos'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 # 2MB limit

# Tworzenie folderów na pliki
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
funny_folder = app.config['UPLOAD_FOLDER'].replace('logos', 'funny')
if not os.path.exists(funny_folder):
    os.makedirs(funny_folder)

# Konfiguracja Bazy Danych
database_url = os.environ.get('DATABASE_URL')
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace("postgres://", "postgresql://", 1)
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Konfiguracja SocketIO
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*", manage_session=True)

# --- Modele Danych ---

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True, nullable=False, default='admin')
    password_hash = db.Column(db.String(256), nullable=False)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="Nowy Event")
    login = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    password_plain = db.Column(db.String(100), nullable=True) # Dodana linia
    is_superhost = db.Column(db.Boolean, default=False)
    event_date = db.Column(db.Date, nullable=True)
    logo_url = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    score = db.Column(db.Integer, default=0)
    warnings = db.Column(db.Integer, default=0)
    revealed_letters = db.Column(db.String(100), default='')
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)

class PlayerAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)
    option_a = db.Column(db.String(100))
    option_b = db.Column(db.String(100))
    option_c = db.Column(db.String(100))
    correct_answer = db.Column(db.String(1), nullable=False)
    letter_to_reveal = db.Column(db.String(1), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    category = db.Column(db.String(50), nullable=False, default='company')

class QRCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code_identifier = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(20), nullable=False, default='white')
    claimed_by_player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)

class PlayerScan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id', ondelete='CASCADE'), nullable=False)
    qrcode_id = db.Column(db.Integer, db.ForeignKey('qr_code.id', ondelete='CASCADE'), nullable=False)
    scan_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    color_category = db.Column(db.String(20), nullable=True)

class FunnyPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id', ondelete='CASCADE'), nullable=False)
    player_name = db.Column(db.String(80), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class GameState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    key = db.Column(db.String(50), nullable=False)
    value = db.Column(db.String(255), nullable=False)
    __table_args__ = (db.UniqueConstraint('event_id', 'key', name='_event_key_uc'),)

# Inicjalizacja bazy danych przy starcie aplikacji
with app.app_context():
    try:
        # Najpierw spróbuj utworzyć tabele
        db.create_all()
        
        # Następnie sprawdź czy kolumna password_plain istnieje i dodaj ją jeśli nie
        from sqlalchemy import text
        
        # Sprawdź typ bazy danych
        database_url = os.environ.get('DATABASE_URL')
        if database_url and 'postgresql' in database_url:
            # PostgreSQL
            try:
                result = db.session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='event' AND column_name='password_plain'
                """))
                
                if result.fetchone() is None:
                    print("Dodawanie kolumny password_plain do tabeli event...")
                    db.session.execute(text("ALTER TABLE event ADD COLUMN password_plain VARCHAR(100)"))
                    db.session.commit()
                    print("Kolumna password_plain została dodana.")
            except Exception as e:
                print(f"Błąd podczas dodawania kolumny password_plain: {e}")
        else:
            # SQLite
            try:
                result = db.session.execute(text("PRAGMA table_info(event)"))
                columns = [row[1] for row in result]
                
                if 'password_plain' not in columns:
                    print("Dodawanie kolumny password_plain do tabeli event...")
                    db.session.execute(text("ALTER TABLE event ADD COLUMN password_plain VARCHAR(100)"))
                    db.session.commit()
                    print("Kolumna password_plain została dodana.")
            except Exception as e:
                print(f"Błąd podczas dodawania kolumny password_plain: {e}")
        
        # Sprawdzenie i dodanie domyślnego admina/eventu, jeśli baza jest pusta
        if not Admin.query.first():
            admin = Admin(login='admin')
            admin.set_password('admin')
            db.session.add(admin)
            print("Default admin created.")
        
        if not Event.query.first():
            event = Event(id=1, login='host1', name='Event #1', password_plain='password1')
            event.set_password('password1')
            db.session.add(event)
            print("Default event created.")
        
        db.session.commit()
        print("Database tables checked/created successfully.")
    except Exception as e:
        print(f"Database initialization error: {e}")
        db.session.rollback()

# --- Dekoratory Autoryzacji ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Brak autoryzacji'}), 401
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def host_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'host_event_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Brak autoryzacji'}), 401
            return redirect(url_for('host_login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Inicjalizacja Bazy Danych (CLI) ---
@app.cli.command("init-db")
def init_db_command():
    """Tworzy tabele w bazie danych i domyślne wpisy, jeśli nie istnieją."""
    db.create_all()
    if not Admin.query.first():
        admin = Admin(login='admin')
        admin.set_password('admin')
        db.session.add(admin)
    if not Event.query.first():
        event = Event(id=1, login='host1', name='Event #1')
        event.set_password('password1')
        db.session.add(event)
    db.session.commit()
    print("Database initialized.")


# --- Funkcje Pomocnicze ---
def get_game_state(event_id, key, default=None):
    state = GameState.query.filter_by(event_id=event_id, key=key).first()
    return state.value if state else default

def set_game_state(event_id, key, value):
    state = GameState.query.filter_by(event_id=event_id, key=key).first()
    if state: state.value = str(value)
    else: db.session.add(GameState(event_id=event_id, key=key, value=str(value)))
    db.session.commit()

def get_full_game_state(event_id):
    state_keys = [
        'game_active', 'is_timer_running', 'game_end_time', 'time_left_on_pause',
        'game_start_time', 'total_paused_duration', 'bonus_multiplier', 'time_speed',
        'language_player', 'language_host', 'initial_game_duration'
    ]
    state_data = {key: get_game_state(event_id, key) for key in state_keys}

    is_active = state_data.get('game_active') == 'True'
    is_timer_running = state_data.get('is_timer_running') == 'True'
    
    bonus_val = state_data.get('bonus_multiplier')
    bonus_multiplier = int(bonus_val) if bonus_val is not None else 1
    
    speed_val = state_data.get('time_speed')
    time_speed = int(speed_val) if speed_val is not None else 1
    
    time_left_on_pause_val = state_data.get('time_left_on_pause')
    time_left_on_pause = float(time_left_on_pause_val) if time_left_on_pause_val is not None else 0

    total_paused_duration_val = state_data.get('total_paused_duration')
    total_paused_duration = float(total_paused_duration_val) if total_paused_duration_val is not None else 0

    initial_game_duration_val = state_data.get('initial_game_duration')
    initial_game_duration = float(initial_game_duration_val) if initial_game_duration_val is not None else 0

    time_left = 0
    if is_active and is_timer_running and state_data.get('game_end_time'):
        end_time = datetime.fromisoformat(state_data['game_end_time'])
        time_left = max(0, (end_time - datetime.utcnow()).total_seconds())
    elif is_active and not is_timer_running:
        time_left = time_left_on_pause

    time_elapsed = 0
    time_elapsed_with_pauses = 0
    if state_data.get('game_start_time'):
        start_time = datetime.fromisoformat(state_data['game_start_time'])
        if is_active:
            time_elapsed_with_pauses = (datetime.utcnow() - start_time).total_seconds()
            time_elapsed = time_elapsed_with_pauses - total_paused_duration
        else:
            time_elapsed = initial_game_duration - time_left_on_pause
            time_elapsed_with_pauses = time_elapsed + total_paused_duration

    player_count = Player.query.filter_by(event_id=event_id).count()
    try:
        correct_answers = PlayerAnswer.query.filter_by(event_id=event_id).count()
    except Exception:
        correct_answers = 0

    password_value = "SAPEREVENT"
    revealed_letters = "".join(p.revealed_letters for p in Player.query.filter_by(event_id=event_id).all())
    displayed_password = "".join([char if char in revealed_letters.upper() else "_" for char in password_value.upper()])
    
    return {
        'game_active': is_active,
        'is_timer_running': is_timer_running,
        'time_left': time_left,
        'password': displayed_password,
        'player_count': player_count,
        'correct_answers': correct_answers,
        'time_elapsed': time_elapsed,
        'time_elapsed_with_pauses': time_elapsed_with_pauses,
        'language_player': state_data.get('language_player') or 'pl',
        'language_host': state_data.get('language_host') or 'pl',
        'bonus_multiplier': bonus_multiplier,
        'time_speed': time_speed
    }

def event_to_dict(event):
    return {
        'id': event.id, 'name': event.name, 'login': event.login,
        'password': event.password_plain or '', # Dodana linia
        'is_superhost': event.is_superhost,
        'event_date': event.event_date.isoformat() if event.event_date else '',
        'logo_url': event.logo_url, 'notes': event.notes
    }

def delete_logo_file(event):
    if event and event.logo_url:
        try:
            filepath = os.path.join(app.root_path, event.logo_url.lstrip('/'))
            if os.path.exists(filepath): os.remove(filepath)
            event.logo_url = None
        except Exception as e:
            print(f"Błąd podczas usuwania pliku logo: {e}")

# --- Główne Ścieżki ---
@app.route('/')
def index(): 
    return redirect(url_for('host_login'))

# --- ADMIN ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        login, password = request.form['login'], request.form['password']
        admin = Admin.query.filter_by(login=login).first()
        if admin and admin.check_password(password):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        return render_template('admin_login.html', error="Nieprawidłowe dane")
    return render_template('admin_login.html')

@app.route('/admin')
@admin_required
def admin_panel(): 
    return render_template('admin.html')

@app.route('/admin/qrcodes/<int:event_id>')
@admin_required
def admin_qrcodes_view(event_id):
    event = db.session.get(Event, event_id)
    if not event: return "Nie znaleziono eventu", 404
    counts = {
        'red': QRCode.query.filter_by(event_id=event_id, color='red').count(),
        'white_trap': QRCode.query.filter_by(event_id=event_id, color='white_trap').count(),
        'green': QRCode.query.filter_by(event_id=event_id, color='green').count(),
        'pink': QRCode.query.filter_by(event_id=event_id, color='pink').count()
    }
    return render_template('admin_qrcodes.html', event=event, counts=counts)

@app.route('/admin/impersonate/<int:event_id>')
@admin_required
def impersonate_host(event_id):
    session['host_event_id'] = event_id
    session['impersonated_by_admin'] = True
    return redirect(url_for('host_panel'))


# --- HOST ---
@app.route('/host/login', methods=['GET', 'POST'])
def host_login():
    if request.method == 'POST':
        login = request.form['login'].strip()
        password = request.form['password'].strip()
        event = Event.query.filter_by(login=login).first()
        if event and event.check_password(password):
            session['host_event_id'] = event.id
            session.pop('impersonated_by_admin', None)
            return redirect(url_for('host_panel'))
        return render_template('host_login.html', error="Nieprawidłowe dane")
    return render_template('host_login.html')


@app.route('/host')
@host_required
def host_panel():
    event = db.session.get(Event, session['host_event_id'])
    is_impersonated = session.get('impersonated_by_admin', False)
    return render_template('host.html', event=event, is_impersonated=is_impersonated)

@app.route('/host/logout_impersonate')
def logout_impersonate():
    session.pop('host_event_id', None)
    session.pop('impersonated_by_admin', None)
    return redirect(url_for('admin_panel'))

# --- PLAYER & DISPLAY ---
@app.route('/player/<int:event_id>/<qr_code>')
def player_view(event_id, qr_code): 
    return render_template('player.html', qr_code=qr_code, event_id=event_id)

@app.route('/display/<int:event_id>')
def display(event_id):
    event = db.session.get(Event, event_id)
    return render_template('display.html', event=event)

@app.route('/qrcodes/<int:event_id>')
def list_qrcodes_public(event_id):
    is_admin = session.get('admin_logged_in', False)
    is_host = session.get('host_event_id') == event_id
    if not (is_admin or is_host): return "Brak autoryzacji", 401
    qrcodes = QRCode.query.filter_by(event_id=event_id).all()
    return render_template('qrcodes.html', qrcodes=qrcodes, event_id=event_id)

# ===================================================================
# --- API Endpoints ---
# ===================================================================

# --- API: ADMIN ---
@app.route('/api/admin/events', methods=['GET', 'POST'])
@admin_required
def manage_events():
    if request.method == 'POST':
        new_id = (db.session.query(db.func.max(Event.id)).scalar() or 0) + 1
        login = f'host{new_id}'
        password = f'password{new_id}'
        new_event = Event(id=new_id, name=f'Nowy Event #{new_id}', login=login, password_plain=password) # Zmieniona linia
        new_event.set_password(password)
        db.session.add(new_event)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Błąd podczas tworzenia eventu'}), 500
        return jsonify(event_to_dict(new_event))
    events = Event.query.order_by(Event.id).all()
    return jsonify([event_to_dict(e) for e in events])

@app.route('/api/admin/event/<int:event_id>', methods=['PUT', 'DELETE'])
@admin_required
def update_or_delete_event(event_id):
    event = db.session.get(Event, event_id)
    if not event: return jsonify({'error': 'Nie znaleziono eventu'}), 404

    if request.method == 'PUT':
        data = request.json
        event.name = data.get('name', event.name).strip()
        new_login = data.get('login', event.login).strip()
        if new_login:
            event.login = new_login
        event.is_superhost = data.get('is_superhost', event.is_superhost)
        event.notes = data.get('notes', event.notes).strip()
           new_password = data.get('password')
        if new_password and new_password.strip():
            event.set_password(new_password.strip())
            event.password_plain = new_password.strip()
        elif new_password == '':
    # Jeśli przesłano pusty string, wyczyść hasło
        event.password_plain = ''
        date_str = data.get('event_date')
        event.event_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
        try:
            db.session.commit()
            return jsonify(event_to_dict(event))
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Błąd zapisu: {e}'}), 500

    if request.method == 'DELETE':
        if event_id <= 1: return jsonify({'error': 'Nie można usunąć pierwszego eventu.'}), 403
        delete_logo_file(event)
        db.session.delete(event)
        db.session.commit()
        return jsonify({'message': f'Event {event_id} został pomyślnie usunięty.'})

@app.route('/api/admin/event/<int:event_id>/upload_logo', methods=['POST'])
@admin_required
def upload_logo(event_id):
    event = db.session.get(Event, event_id)
    if not event: return jsonify({'error': 'Nie znaleziono eventu'}), 404
    if 'logo' not in request.files: return jsonify({'error': 'Brak pliku logo'}), 400
    file = request.files['logo']
    if file.filename == '': return jsonify({'error': 'Nie wybrano pliku'}), 400
    if file:
        delete_logo_file(event)
        filename = secure_filename(f"event_{event_id}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        event.logo_url = f"/{filepath}"
        db.session.commit()
        return jsonify({'message': 'Logo wgrane pomyślnie', 'logo_url': event.logo_url})
    return jsonify({'error': 'Nie udało się wgrać pliku'}), 500

@app.route('/api/admin/event/<int:event_id>/delete_logo', methods=['POST'])
@admin_required
def delete_logo(event_id):
    event = db.session.get(Event, event_id)
    if not event: return jsonify({'error': 'Nie znaleziono eventu'}), 404
    delete_logo_file(event)
    db.session.commit()
    return jsonify({'message': 'Logo usunięte pomyślnie.'})


@app.route('/api/admin/event/<int:event_id>/reset', methods=['POST'])
@admin_required
def reset_event(event_id):
    try:
        event = db.session.get(Event, event_id)
        if not event: return jsonify({'message': 'Nie znaleziono eventu'}), 404
        delete_logo_file(event)
        Player.query.filter_by(event_id=event_id).delete()
        Question.query.filter_by(event_id=event_id).delete()
        QRCode.query.filter_by(event_id=event_id).delete()
        PlayerScan.query.filter_by(event_id=event_id).delete()
        PlayerAnswer.query.filter_by(event_id=event_id).delete()
        FunnyPhoto.query.filter_by(event_id=event_id).delete()
        GameState.query.filter_by(event_id=event_id).delete()
        db.session.commit()
        room = f'event_{event_id}'
        emit_leaderboard_update(room)
        emit_password_update(room)
        emit_full_state_update(room)
        return jsonify({'message': f'Gra dla eventu {event_id} została zresetowana.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Błąd serwera: {str(e)}'}), 500

@app.route('/api/admin/qrcodes/generate', methods=['POST'])
@admin_required
def admin_generate_qr_codes():
    data = request.json
    event_id = data.get('event_id')
    if get_game_state(event_id, 'game_active', 'False') == 'True':
        return jsonify({'message': 'Nie można zmieniać kodów podczas aktywnej gry.'}), 403
    QRCode.query.filter_by(event_id=event_id).delete()
    db.session.add(QRCode(code_identifier='bialy', color='white', event_id=event_id))
    db.session.add(QRCode(code_identifier='zolty', color='yellow', event_id=event_id))
    counts = data.get('counts', {})
    one_time_codes = {'red': 'czerwony', 'white_trap': 'pulapka', 'green': 'zielony', 'pink': 'rozowy'}
    for color, prefix in one_time_codes.items():
        for i in range(1, int(counts.get(color, 0)) + 1):
            db.session.add(QRCode(code_identifier=f"{prefix}{i}", color=color, event_id=event_id))
    db.session.commit()
    return jsonify({'message': 'Kody QR zostały wygenerowane.'})

# --- API: HOST ---
@app.route('/api/host/state', methods=['GET'])
@host_required
def get_host_game_state(): 
    return jsonify(get_full_game_state(session['host_event_id']))

@app.route('/api/host/start_game', methods=['POST'])
@host_required
def start_game():
    event_id = session['host_event_id']
    Player.query.filter_by(event_id=event_id).delete()
    PlayerScan.query.filter_by(event_id=event_id).delete()
    PlayerAnswer.query.filter_by(event_id=event_id).delete()
    FunnyPhoto.query.filter_by(event_id=event_id).delete()
    QRCode.query.filter(QRCode.event_id == event_id, QRCode.claimed_by_player_id.isnot(None)).update({QRCode.claimed_by_player_id: None})
    
    set_game_state(event_id, 'game_active', 'True')
    set_game_state(event_id, 'is_timer_running', 'True')
    set_game_state(event_id, 'game_start_time', datetime.utcnow().isoformat())
    set_game_state(event_id, 'total_paused_duration', 0)
    set_game_state(event_id, 'bonus_multiplier', 1)
    set_game_state(event_id, 'time_speed', 1)
    
    minutes = int(request.json.get('minutes', 30))
    duration_seconds = minutes * 60
    set_game_state(event_id, 'initial_game_duration', duration_seconds)
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    set_game_state(event_id, 'game_end_time', end_time.isoformat())
    
    db.session.commit()
    
    room = f'event_{event_id}'
    emit_full_state_update(room)
    emit_leaderboard_update(room)
    return jsonify({'message': f'Gra rozpoczęta na {minutes} minut.'})

@app.route('/api/host/stop_game', methods=['POST'])
@host_required
def stop_game():
    event_id = session['host_event_id']
    data = request.json
    password = data.get('password')
    
    event = db.session.get(Event, event_id)
    if not event or not password:
        return jsonify({'error': 'Brak danych uwierzytelniających'}), 400
        
    if not event.check_password(password):
        return jsonify({'error': 'Nieprawidłowe hasło!'}), 401

    set_game_state(event_id, 'game_active', 'False')
    set_game_state(event_id, 'is_timer_running', 'False')
    emit_full_state_update(f'event_{event_id}')
    return jsonify({'message': 'Gra została zatrzymana.'})


@app.route('/api/host/game_control', methods=['POST'])
@host_required
def game_control():
    event_id = session['host_event_id']
    data = request.json
    control = data.get('control')
    value = data.get('value')
    
    is_running = get_game_state(event_id, 'is_timer_running', 'True') == 'True'

    if control == 'pause':
        if is_running:
            set_game_state(event_id, 'is_timer_running', 'False')
            set_game_state(event_id, 'pause_start_time', datetime.utcnow().isoformat())
            end_time_str = get_game_state(event_id, 'game_end_time')
            if end_time_str:
                time_left = (datetime.fromisoformat(end_time_str) - datetime.utcnow()).total_seconds()
                set_game_state(event_id, 'time_left_on_pause', time_left)
        else: # Unpausing
            pause_start_str = get_game_state(event_id, 'pause_start_time')
            if pause_start_str:
                paused_duration = (datetime.utcnow() - datetime.fromisoformat(pause_start_str)).total_seconds()
                total_paused = float(get_game_state(event_id, 'total_paused_duration', 0))
                set_game_state(event_id, 'total_paused_duration', total_paused + paused_duration)
            
            time_left = float(get_game_state(event_id, 'time_left_on_pause', 0))
            time_speed = int(get_game_state(event_id, 'time_speed', 1))
            new_end_time = datetime.utcnow() + timedelta(seconds=time_left / time_speed)
            set_game_state(event_id, 'game_end_time', new_end_time.isoformat())
            set_game_state(event_id, 'is_timer_running', 'True')

    elif control == 'force_win':
        set_game_state(event_id, 'game_active', 'False')
        set_game_state(event_id, 'is_timer_running', 'False')
        socketio.emit('game_forced_win', {'message': 'Zadanie wykonane! Gra zakończona!'}, room=f'event_{event_id}')

    elif control == 'bonus':
        current_val = get_game_state(event_id, 'bonus_multiplier', '1')
        new_val = value if current_val != str(value) else '1'
        set_game_state(event_id, 'bonus_multiplier', new_val)
        
    elif control == 'speed':
        current_val = get_game_state(event_id, 'time_speed', '1')
        new_val = value if current_val != str(value) else '1'
        set_game_state(event_id, 'time_speed', new_val)
        
    elif control == 'language_player':
        set_game_state(event_id, 'language_player', value)

    elif control == 'language_host':
        set_game_state(event_id, 'language_host', value)
    
    emit_full_state_update(f'event_{event_id}')
    return jsonify(get_full_game_state(event_id))

# --- API: HOST Players & Questions ---
@app.route('/api/host/players', methods=['GET'])
@host_required
def get_players():
    players = Player.query.filter_by(event_id=session['host_event_id']).order_by(Player.score.desc()).all()
    return jsonify([{'id': p.id, 'name': p.name, 'score': p.score, 'warnings': p.warnings} for p in players])

@app.route('/api/host/player/<int:player_id>/warn', methods=['POST'])
@host_required
def warn_player(player_id):
    player = db.session.get(Player, player_id)
    if player and player.event_id == session['host_event_id']:
        player.warnings += 1; db.session.commit()
        return jsonify({'warnings': player.warnings})
    return jsonify({'error': 'Nie znaleziono gracza'}), 404

@app.route('/api/host/player/<int:player_id>', methods=['DELETE'])
@host_required
def delete_player(player_id):
    player = db.session.get(Player, player_id)
    if player and player.event_id == session['host_event_id']:
        db.session.delete(player)
        db.session.commit()
        emit_leaderboard_update(f'event_{session["host_event_id"]}')
        return jsonify({'message': 'Gracz usunięty'})
    return jsonify({'error': 'Nie znaleziono gracza'}), 404

@app.route('/api/host/questions', methods=['GET', 'POST'])
@host_required
def host_questions():
    event_id = session['host_event_id']
    if request.method == 'POST':
        data = request.json
        new_q = Question(
            text=data['text'],
            option_a=data['answers'][0], option_b=data['answers'][1], option_c=data['answers'][2],
            correct_answer=data['correctAnswer'], letter_to_reveal=data.get('letterToReveal', 'X').upper(),
            category=data.get('category', 'company'), event_id=event_id
        )
        db.session.add(new_q); db.session.commit()
        return jsonify({'id': new_q.id})
    questions = Question.query.filter_by(event_id=event_id).all()
    return jsonify([{'id': q.id, 'text': q.text, 'answers': [q.option_a, q.option_b, q.option_c], 'correctAnswer': q.correct_answer, 'letterToReveal': q.letter_to_reveal, 'category': q.category} for q in questions])

@app.route('/api/host/question/<int:question_id>', methods=['DELETE'])
@host_required
def delete_question(question_id):
    q = db.session.get(Question, question_id)
    if q and q.event_id == session['host_event_id']:
        db.session.delete(q); db.session.commit()
        return jsonify({'message': 'Pytanie usunięte'})
    return jsonify({'error': 'Nie znaleziono pytania'}), 404

# --- API: PLAYER ---
@app.route('/api/player/register', methods=['POST'])
def register_player():
    data = request.json
    name, event_id = data.get('name'), data.get('event_id')
    if Player.query.filter_by(name=name, event_id=event_id).first():
        return jsonify({'error': 'Ta nazwa jest już zajęta.'}), 409
    new_player = Player(name=name, event_id=event_id)
    db.session.add(new_player); db.session.commit()
    emit_leaderboard_update(f'event_{event_id}')
    return jsonify({'id': new_player.id, 'name': new_player.name, 'score': 0})

@app.route('/api/player/scan_qr', methods=['POST'])
def scan_qr():
    data = request.json
    player_id, qr_id, event_id = data.get('player_id'), data.get('qr_code'), data.get('event_id')
    player = db.session.get(Player, player_id)
    qr_code = QRCode.query.filter_by(code_identifier=qr_id, event_id=event_id).first()

    if not player or not qr_code: return jsonify({'message': 'Nieprawidłowe dane.'}), 404
    if get_game_state(event_id, 'game_active', 'False') != 'True': return jsonify({'message': 'Gra nie jest aktywna.'}), 403

    if qr_code.color in ['white', 'yellow']:
        last_scan = PlayerScan.query.filter_by(player_id=player_id, color_category=qr_code.color).order_by(PlayerScan.scan_time.desc()).first()
        if last_scan and datetime.utcnow() < last_scan.scan_time + timedelta(minutes=5):
            wait_time = (last_scan.scan_time + timedelta(minutes=5) - datetime.utcnow()).seconds
            return jsonify({'status': 'wait', 'message': f'Odczekaj jeszcze {wait_time // 60}m {wait_time % 60}s.'}), 429
        
        db.session.add(PlayerScan(player_id=player_id, qrcode_id=qr_code.id, event_id=event_id, color_category=qr_code.color))
        quiz_category = 'company' if qr_code.color == 'white' else 'world'
        answered_ids = [ans.question_id for ans in PlayerAnswer.query.filter_by(player_id=player_id).all()]
        question = Question.query.filter(Question.id.notin_(answered_ids), Question.event_id==event_id, Question.category==quiz_category).order_by(db.func.random()).first()
        if not question: return jsonify({'status': 'info', 'message': 'Odpowiedziałeś na wszystkie pytania z tej kategorii!'})
        return jsonify({'status': 'question', 'question': {'id': question.id, 'text': question.text, 'option_a': question.option_a, 'option_b': question.option_b, 'option_c': question.option_c}})
    else:
        if qr_code.claimed_by_player_id: return jsonify({'status': 'error', 'message': 'Ten kod został już wykorzystany.'}), 403
        qr_code.claimed_by_player_id = player_id
        if qr_code.color == 'red': player.score += 50; message = 'Kod specjalny! Zdobywasz 50 punktów!'
        elif qr_code.color == 'white_trap': player.score = max(0, player.score - 25); message = 'Pułapka! Tracisz 25 punktów.'
        elif qr_code.color == 'green': db.session.commit(); return jsonify({'status': 'minigame', 'game': 'tetris', 'message': 'Minigra odblokowana!'})
        elif qr_code.color == 'pink': db.session.commit(); return jsonify({'status': 'photo_challenge'})
        else: message = "Niezidentyfikowany kod."
        db.session.commit()
        emit_leaderboard_update(f'event_{event_id}')
        return jsonify({'status': 'info', 'message': message, 'score': player.score})

@app.route('/api/player/answer', methods=['POST'])
def process_answer():
    data = request.json
    player_id, question_id, answer = data.get('player_id'), data.get('question_id'), data.get('answer')
    player, question = db.session.get(Player, player_id), db.session.get(Question, question_id)
    if not player or not question: return jsonify({'error': 'Invalid data'}), 404
    
    db.session.add(PlayerAnswer(player_id=player_id, question_id=question_id, event_id=player.event_id))
    bonus = int(get_game_state(player.event_id, 'bonus_multiplier', 1))
    
    if answer == question.correct_answer:
        points = 10 * bonus
        player.score += points
        player.revealed_letters += question.letter_to_reveal
        db.session.commit()
        emit_password_update(f'event_{player.event_id}')
        emit_leaderboard_update(f'event_{player.event_id}')
        return jsonify({'correct': True, 'letter': question.letter_to_reveal, 'score': player.score})
    else:
        player.score = max(0, player.score - 5)
        db.session.commit()
        emit_leaderboard_update(f'event_{player.event_id}')
        return jsonify({'correct': False, 'score': player.score})

@app.route('/api/player/upload_photo', methods=['POST'])
def upload_photo():
    if 'photo' not in request.files: return jsonify({'error': 'Brak pliku'}), 400
    file = request.files['photo']
    player_id = request.form.get('player_id')
    player = db.session.get(Player, player_id)
    if file.filename == '' or not player: return jsonify({'error': 'Brak pliku lub gracza'}), 400
    
    filename = f"event_{player.event_id}_player_{player.id}_{int(datetime.utcnow().timestamp())}.jpg"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'].replace('logos','funny'), filename)
    if not os.path.exists(os.path.dirname(filepath)): os.makedirs(os.path.dirname(filepath))
    file.save(filepath)
    image_url = f"/{filepath}"
    
    photo = FunnyPhoto(player_id=player.id, player_name=player.name, image_url=image_url, event_id=player.event_id)
    player.score += 15
    db.session.add(photo); db.session.commit()
    
    room = f'event_{player.event_id}'
    socketio.emit('new_photo', {'url': image_url, 'player': player.name}, room=room)
    emit_leaderboard_update(room)
    return jsonify({'message': 'Zdjęcie dodane! Otrzymujesz 15 punktów.', 'score': player.score})

# ===================================================================
# --- Gniazda (SocketIO) ---
# ===================================================================
def emit_full_state_update(room):
    event_id = int(room.split('_')[1])
    socketio.emit('game_state_update', get_full_game_state(event_id), room=room)

def emit_leaderboard_update(room):
    event_id = int(room.split('_')[1])
    with app.app_context():
        players = Player.query.filter_by(event_id=event_id).order_by(Player.score.desc()).all()
        socketio.emit('leaderboard_update', [{'name': p.name, 'score': p.score} for p in players], room=room)

def emit_password_update(room):
     event_id = int(room.split('_')[1])
     with app.app_context():
        socketio.emit('password_update', get_full_game_state(event_id)['password'], room=room)

def update_timers():
    while True:
        try:
            with app.app_context():
                active_events = db.session.query(GameState.event_id).filter_by(key='game_active', value='True').distinct().all()
                event_ids = [e[0] for e in active_events]
                
                for event_id in event_ids:
                    if get_game_state(event_id, 'is_timer_running', 'False') == 'True':
                        state = get_full_game_state(event_id)
                        room_name = f'event_{event_id}'
                        socketio.emit('timer_tick', {
                            'time_left': state['time_left'],
                            'time_elapsed': state['time_elapsed'],
                            'time_elapsed_with_pauses': state['time_elapsed_with_pauses']
                        }, room=room_name)
                        
                        if state['time_left'] <= 0:
                            set_game_state(event_id, 'game_active', 'False')
                            set_game_state(event_id, 'is_timer_running', 'False')
                            emit_full_state_update(room_name)
                            socketio.emit('game_over', {}, room=room_name)
        except Exception as e:
            print(f"Błąd w update_timers: {e}")
        socketio.sleep(1)


@socketio.on('join')
def on_join(data):
    event_id = data.get('event_id')
    if event_id:
        room = f'event_{event_id}'
        join_room(room)
        # Send initial state only to the client that just joined
        emit('game_state_update', get_full_game_state(event_id), room=request.sid)
        # Send leaderboard to everyone in the room to reflect new player count if applicable
        emit_leaderboard_update(room)

# Uruchomienie Aplikacji
if __name__ == '__main__':
    socketio.start_background_task(target=update_timers)
    port = int(os.environ.get('PORT', 5000))
    # Użyj debug=False przy wdrażaniu na produkcję
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    socketio.run(app, host='0.0.0.0', port=port, debug=debug_mode, allow_unsafe_werkzeug=True)




