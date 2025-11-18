from gevent import monkey
monkey.patch_all()

# Załaduj zmienne środowiskowe z pliku .env
from dotenv import load_dotenv
load_dotenv()

import os
import random
import json
import uuid
from flask import Flask, render_template, render_template_string, request, jsonify, url_for, session, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

# Import dla Claude API (używany do generowania pytań AI i Wróżki AI)
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️  anthropic package not installed. AI features (question generation, Fortune Teller) will not work.")

# Import dla rozpoznawania obrazów AR
try:
    import cv2
    import numpy as np
    from PIL import Image
    import base64
    import io
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("⚠️  opencv-python not installed. AR features will be limited.")

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
socketio = SocketIO(app, 
                    async_mode='gevent', 
                    cors_allowed_origins="*", 
                    manage_session=True,
                    engineio_logger=False,
                    logger=True,
                    ping_timeout=60,
                    ping_interval=25)


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
    password_plain = db.Column(db.String(100), nullable=True)
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
    difficulty = db.Column(db.String(20), nullable=False, default='easy')
    round = db.Column(db.Integer, nullable=False, default=1)
    times_shown = db.Column(db.Integer, default=0)
    times_correct = db.Column(db.Integer, default=0)

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
    votes = db.Column(db.Integer, default=0)

class PhotoVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    photo_id = db.Column(db.Integer, db.ForeignKey('funny_photo.id', ondelete='CASCADE'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id', ondelete='CASCADE'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('photo_id', 'player_id', name='_photo_player_vote_uc'),)

class GameState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    key = db.Column(db.String(50), nullable=False)
    value = db.Column(db.String(255), nullable=False)
    __table_args__ = (db.UniqueConstraint('event_id', 'key', name='_event_key_uc'),)

class AICategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    is_custom = db.Column(db.Boolean, default=False)
    difficulty_level = db.Column(db.String(20), default='easy')
    __table_args__ = (db.UniqueConstraint('event_id', 'name', name='_event_category_uc'),)

class AIQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('ai_category.id', ondelete='CASCADE'), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)
    source = db.Column(db.String(20), default='generated')
    times_shown = db.Column(db.Integer, default=0)
    times_correct = db.Column(db.Integer, default=0)

class AIPlayerAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('ai_question.id', ondelete='CASCADE'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    __table_args__ = (db.UniqueConstraint('player_id', 'question_id', name='_player_ai_question_uc'),)

class ARObject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    object_name = db.Column(db.String(100), nullable=False)
    image_data = db.Column(db.Text, nullable=False)  # Base64 zakodowany obraz
    image_features = db.Column(db.Text, nullable=True)  # JSON z cechami obrazu dla rozpoznawania
    game_type = db.Column(db.String(50), nullable=False)  # 'snake', 'quiz', 'tetris', 'arkanoid'
    is_active = db.Column(db.Boolean, default=True)
    sensitivity = db.Column(db.Integer, default=50)  # Czułość wykrywania (5-500)
    scan_interval = db.Column(db.Integer, default=2)  # Interwał skanowania w sekundach (1-10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LiveSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    button_count = db.Column(db.Integer, default=3)  # 2, 3, lub 4 przyciski (A,B) (A,B,C) lub (A,B,C,D)
    qr_code = db.Column(db.String(50), nullable=True)  # Kod QR dla graczy
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LiveQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('live_session.id', ondelete='CASCADE'), nullable=False)
    question_text = db.Column(db.String(500), nullable=True)  # Opcjonalne - może być puste jeśli host czyta
    option_a = db.Column(db.String(200), nullable=True)
    option_b = db.Column(db.String(200), nullable=True)
    option_c = db.Column(db.String(200), nullable=True)
    option_d = db.Column(db.String(200), nullable=True)
    correct_answer = db.Column(db.String(1), nullable=True)  # 'A', 'B', 'C', lub 'D' - null dopóki host nie ujawni
    is_active = db.Column(db.Boolean, default=False)  # Czy pytanie jest aktualnie aktywne
    is_revealed = db.Column(db.Boolean, default=False)  # Czy poprawna odpowiedź została ujawniona
    time_limit = db.Column(db.Integer, default=30)  # Limit czasu w sekundach
    started_at = db.Column(db.DateTime, nullable=True)  # Kiedy pytanie zostało uruchomione
    revealed_at = db.Column(db.DateTime, nullable=True)  # Kiedy odpowiedź została ujawniona
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LivePlayerAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('live_question.id', ondelete='CASCADE'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    answer = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', lub 'D'
    is_correct = db.Column(db.Boolean, nullable=True)  # Wyznaczane po ujawnieniu poprawnej odpowiedzi
    points_awarded = db.Column(db.Integer, default=0)  # Punkty przyznane za odpowiedź
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('player_id', 'question_id', name='_player_live_question_uc'),)

# Inicjalizacja bazy danych przy starcie aplikacji
with app.app_context():
    try:
        db.create_all()

        # Automatyczna migracja: Dodaj kolumnę 'round' do tabeli 'question' jeśli nie istnieje
        try:
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'question'
            """))
            existing_columns = [row[0] for row in result]

            if 'round' not in existing_columns:
                db.session.execute(text("ALTER TABLE question ADD COLUMN round INTEGER DEFAULT 1"))
                db.session.commit()
                print("✓ Database migration: Added 'round' column to question table.")
        except Exception as migration_error:
            # Może to być SQLite, spróbujmy innej składni
            try:
                # SQLite używa PRAGMA zamiast information_schema
                db.session.execute(text("ALTER TABLE question ADD COLUMN round INTEGER DEFAULT 1"))
                db.session.commit()
                print("✓ Database migration: Added 'round' column to question table (SQLite).")
            except Exception as e:
                # Kolumna prawdopodobnie już istnieje
                db.session.rollback()

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
def init_default_ai_categories(event_id):
    """Inicjalizuje domyślne 10 kategorii AI dla eventu"""
    default_categories = [
        'Historia powszechna',
        'Geografia',
        'Znane postaci',
        'Muzyka',
        'Literatura',
        'Kuchnia',
        'Film',
        'Nauki ścisłe',
        'Historia Polski',
        'Sport'
    ]

    for cat_name in default_categories:
        existing = AICategory.query.filter_by(event_id=event_id, name=cat_name).first()
        if not existing:
            category = AICategory(
                event_id=event_id,
                name=cat_name,
                is_enabled=True,
                is_custom=False,
                difficulty_level='easy'
            )
            db.session.add(category)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing AI categories: {e}")

def generate_ai_questions_with_claude(category_name, difficulty_level='easy', count=10):
    """Generuje pytania AI przy użyciu Claude API"""
    print(f"🤖 Attempting to generate {count} AI questions for category: {category_name}")

    if not ANTHROPIC_AVAILABLE:
        error_msg = 'Claude API nie jest dostępne. Zainstaluj pakiet anthropic.'
        print(f"❌ {error_msg}")
        return {'error': error_msg}

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        error_msg = 'Brak klucza API dla Claude. Ustaw zmienną środowiskową ANTHROPIC_API_KEY w konfiguracji serwera.'
        print(f"❌ {error_msg}")
        print(f"ℹ️  Dostępne zmienne środowiskowe: {', '.join([k for k in os.environ.keys() if 'ANTHROPIC' in k.upper() or 'API' in k.upper()])}")
        return {'error': error_msg}

    print(f"✅ API key found (length: {len(api_key)}, starts with: {api_key[:10]}...)")

    difficulty_mapping = {
        'easy': 'łatwy (podstawowa wiedza ogólna)',
        'medium': 'średni (wymaga pewnej wiedzy specjalistycznej)',
        'advanced': 'zaawansowany (wymaga głębokiej wiedzy specjalistycznej)'
    }

    difficulty_desc = difficulty_mapping.get(difficulty_level, 'łatwy')

    prompt = f"""Wygeneruj dokładnie {count} pytań testowych z kategorii "{category_name}" na poziomie trudności: {difficulty_desc}.

Każde pytanie powinno:
- Mieć treść pytania (maksymalnie 200 znaków)
- Mieć 3 odpowiedzi (A, B, C) - każda maksymalnie 100 znaków
- Mieć jedną poprawną odpowiedź (A, B lub C)

Zwróć odpowiedź w formacie JSON (tylko czysty JSON, bez żadnego dodatkowego tekstu):
[
  {{
    "text": "Treść pytania?",
    "option_a": "Odpowiedź A",
    "option_b": "Odpowiedź B",
    "option_c": "Odpowiedź C",
    "correct_answer": "A"
  }},
  ...
]

WAŻNE: Pytania muszą być w języku polskim i odpowiednie do poziomu trudności."""

    try:
        print(f"📡 Connecting to Claude API...")
        client = anthropic.Anthropic(api_key=api_key)

        print(f"🔄 Sending request to Claude API...")
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        print(f"✅ Received response from Claude API")

        # Wyciągnij treść odpowiedzi
        response_text = message.content[0].text.strip()

        # Usuń ewentualne markdown backticks
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]

        response_text = response_text.strip()

        # Parse JSON
        questions = json.loads(response_text)

        print(f"✅ Successfully generated {len(questions)} questions")
        return {'success': True, 'questions': questions}

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"❌ Error generating AI questions [{error_type}]: {error_msg}")
        import traceback
        traceback.print_exc()
        return {'error': f'Błąd podczas generowania pytań: {error_msg}'}

def get_game_state(event_id, key, default=None):
    state = GameState.query.filter_by(event_id=event_id, key=key).first()
    return state.value if state else default

def set_game_state(event_id, key, value):
    state = GameState.query.filter_by(event_id=event_id, key=key).first()
    if state: state.value = str(value)
    else: db.session.add(GameState(event_id=event_id, key=key, value=str(value)))
    db.session.commit()

def get_full_game_state(event_id):
    # Pobierz podstawowe dane o stanie gry
    is_active = get_game_state(event_id, 'game_active', 'False') == 'True'
    is_timer_running = get_game_state(event_id, 'is_timer_running', 'False') == 'True'
    
    # Oblicz pozostały czas
    time_left = 0
    if is_active:
        end_time_str = get_game_state(event_id, 'game_end_time')
        if end_time_str:
            try:
                end_time = datetime.fromisoformat(end_time_str)
                time_left = max(0, (end_time - datetime.utcnow()).total_seconds())
            except (ValueError, AttributeError):
                time_left = 0
    
    # Oblicz czas gry (netto i brutto)
    time_elapsed = 0
    time_elapsed_with_pauses = 0
    
    start_time_str = get_game_state(event_id, 'game_start_time')
    if start_time_str:
        try:
            start_time = datetime.fromisoformat(start_time_str)
            time_elapsed_with_pauses = (datetime.utcnow() - start_time).total_seconds()
            
            # Odejmij czas pauz dla czasu netto
            total_paused = float(get_game_state(event_id, 'total_paused_duration', 0))
            time_elapsed = time_elapsed_with_pauses - total_paused
            
            # Jeśli aktualnie w pauzie, dodaj czas od rozpoczęcia pauzy
            if is_active and not is_timer_running:
                pause_start_str = get_game_state(event_id, 'pause_start_time')
                if pause_start_str:
                    pause_start = datetime.fromisoformat(pause_start_str)
                    current_pause_duration = (datetime.utcnow() - pause_start).total_seconds()
                    time_elapsed = time_elapsed_with_pauses - total_paused - current_pause_duration
        except (ValueError, AttributeError):
            time_elapsed = 0
            time_elapsed_with_pauses = 0
    
    # Liczba graczy
    player_count = Player.query.filter_by(event_id=event_id).count()
    
    # Procent ukończenia
    total_questions = Question.query.filter_by(event_id=event_id).count()
    answered_questions = PlayerAnswer.query.filter_by(event_id=event_id).distinct(PlayerAnswer.question_id).count()
    completion_percentage = int((answered_questions / total_questions * 100)) if total_questions > 0 else 0
    
    # Liczba poprawnych odpowiedzi
    correct_answers = PlayerAnswer.query.filter_by(event_id=event_id).count()
    
    # Status gry
    game_status = 'waiting'
    if is_active:
        if is_timer_running:
            game_status = 'active'
        else:
            game_status = 'paused'
    elif start_time_str:
        game_status = 'stopped'
    
    # Język
    language_player = get_game_state(event_id, 'language_player', 'pl')
    language_host = get_game_state(event_id, 'language_host', 'pl')
    
    # Bonus i prędkość
    bonus_multiplier = int(get_game_state(event_id, 'bonus_multiplier', 1))
    time_speed = float(get_game_state(event_id, 'time_speed', 1))
    
    # ✅ Generowanie hasła na podstawie indeksów
    password_value = get_game_state(event_id, 'game_password', 'SAPEREVENT')
    revealed_indices_str = get_game_state(event_id, 'revealed_password_indices', '')
    
    # Parsuj indeksy
    revealed_indices = set()
    if revealed_indices_str:
        try:
            revealed_indices = set(map(int, revealed_indices_str.split(',')))
        except (ValueError, AttributeError):
            revealed_indices = set()
    
    # Generuj displayed_password
    displayed_password = ""
    for i, char in enumerate(password_value):
        if char == ' ':
            displayed_password += '  '
        elif i in revealed_indices:
            displayed_password += char
        else:
            displayed_password += '_'
    
    return {
        'game_active': is_active,
        'is_timer_running': is_timer_running,
        'time_left': time_left,
        'password': displayed_password,
        'player_count': player_count,
        'correct_answers': correct_answers,
        'completion_percentage': completion_percentage,
        'game_status': game_status,
        'time_elapsed': time_elapsed,
        'time_elapsed_with_pauses': time_elapsed_with_pauses,
        'language_player': language_player,
        'language_host': language_host,
        'bonus_multiplier': bonus_multiplier,
        'time_speed': time_speed
    }

def event_to_dict(event):
    return {
        'id': event.id, 'name': event.name, 'login': event.login,
        'password': event.password_plain or '',
        'is_superhost': event.is_superhost,
        'event_date': event.event_date.isoformat() if event.event_date else '',
        'logo_url': event.logo_url, 'notes': event.notes
    }

def get_event_with_status(event):
    event_data = event_to_dict(event)
    game_state_full = get_full_game_state(event.id)

    status_text = "Przygotowanie"
    game_has_started = get_game_state(event.id, 'game_start_time') is not None
    
    if game_state_full.get('game_active'):
        if game_state_full.get('is_timer_running'):
            status_text = "Start"
        else:
            status_text = "Pauza"
    elif game_has_started:
            status_text = "Koniec"

    event_data['game_status'] = {
        'status_text': status_text
    }
    return event_data

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
    is_superhost = event.is_superhost if event else False
    return render_template('host.html', event=event, is_impersonated=is_impersonated, is_superhost=is_superhost)


@app.route('/host/logout_impersonate')
def logout_impersonate():
    session.pop('host_event_id', None)
    session.pop('impersonated_by_admin', None)
    return redirect(url_for('admin_panel'))

# --- PLAYER & DISPLAY ---
@app.route('/player/<int:event_id>/<qr_code>')
def player_view(event_id, qr_code):
    return render_template('player.html', qr_code=qr_code, event_id=event_id)

@app.route('/player_dashboard/<int:event_id>/<int:player_id>')
def player_dashboard(event_id, player_id):
    """Panel gracza z informacjami o grze w czasie rzeczywistym"""
    player = db.session.get(Player, player_id)
    event = db.session.get(Event, event_id)

    if not player or player.event_id != event_id:
        return "Nie znaleziono gracza lub nieprawidłowy event", 404

    if not event:
        return "Nie znaleziono eventu", 404

    return render_template('player_dashboard.html',
                         player_id=player_id,
                         player_name=player.name,
                         event_id=event_id,
                         event_name=event.name)

@app.route('/player_register/<int:event_id>')
def player_register(event_id):
    """Strona rejestracji gracza - dostępna przez skan kodu QR"""
    event = db.session.get(Event, event_id)

    if not event:
        return "Nie znaleziono eventu", 404

    return render_template('player_register.html',
                         event_id=event_id,
                         event_name=event.name)

@app.route('/player_qr_preview/<int:event_id>')
def player_qr_preview(event_id):
    """Podgląd i druk kodu QR do rejestracji graczy"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Nie znaleziono eventu", 404

    # URL do rejestracji gracza
    register_url = url_for('player_register', event_id=event_id, _external=True)

    return render_template('player_qr_preview.html',
                         event=event,
                         register_url=register_url,
                         event_id=event_id)

@app.route('/display/<int:event_id>')
def display(event_id):
    event = db.session.get(Event, event_id)
    return render_template('display.html', event=event)

@app.route('/display2/<int:event_id>')
def display2(event_id):
    """Drugi ekran - ranking, zdjęcia i kod QR dla graczy"""
    event = db.session.get(Event, event_id)
    return render_template('display2.html', event=event)

@app.route('/display4/<int:event_id>')
def display4(event_id):
    """Czwarty ekran - przedmioty AR do znalezienia i kod gracza"""
    event = db.session.get(Event, event_id)
    return render_template('display4.html', event=event)

@app.route('/qrcodes/<int:event_id>')
def list_qrcodes_public(event_id):
    is_admin = session.get('admin_logged_in', False)
    is_host = session.get('host_event_id') == event_id
    if not (is_admin or is_host): return "Brak autoryzacji", 401
    qrcodes = QRCode.query.filter_by(event_id=event_id).all()
    return render_template('qrcodes.html', qrcodes=qrcodes, event_id=event_id)

@app.route('/player_qrcodes/<int:event_id>')
@host_required
def player_qrcodes(event_id):
    """Wyświetla kody QR dla wszystkich graczy do ich dashboard'ów"""
    # Sprawdź czy host ma dostęp do tego eventu
    if session.get('host_event_id') != event_id:
        return "Brak autoryzacji", 401

    event = db.session.get(Event, event_id)
    if not event:
        return "Nie znaleziono eventu", 404

    # Pobierz wszystkich graczy
    players = Player.query.filter_by(event_id=event_id).order_by(Player.name).all()

    # Generuj dane dla kodów QR (URL do dashboard każdego gracza)
    player_data = []
    for player in players:
        # URL do dashboard gracza
        dashboard_url = url_for('player_dashboard', event_id=event_id, player_id=player.id, _external=True)
        player_data.append({
            'id': player.id,
            'name': player.name,
            'score': player.score,
            'dashboard_url': dashboard_url
        })

    return render_template('player_qrcodes.html',
                         event=event,
                         players=player_data,
                         event_id=event_id)

@app.route('/ar-scanner/<int:event_id>')
def ar_scanner(event_id):
    """Strona AR Scanner dla graczy"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Event nie znaleziony", 404
    return render_template('ar_scanner.html', event=event)

@app.route('/ar_qr_preview/<int:event_id>')
def ar_qr_preview(event_id):
    """Podgląd i druk kodu QR do AR Scanner"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Nie znaleziono eventu", 404

    # URL do AR Scannera
    ar_scanner_url = url_for('ar_scanner', event_id=event_id, _external=True)

    return render_template('ar_qr_preview.html',
                         event=event,
                         ar_scanner_url=ar_scanner_url,
                         event_id=event_id)

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
        new_event = Event(id=new_id, name=f'Nowy Event #{new_id}', login=login, password_plain=password)
        new_event.set_password(password)
        db.session.add(new_event)
        try:
            db.session.commit()
            # Inicjalizuj domyślne kategorie AI dla nowego eventu
            init_default_ai_categories(new_id)
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Błąd podczas tworzenia eventu'}), 500
        return jsonify(get_event_with_status(new_event))
    events = Event.query.order_by(Event.id).all()
    return jsonify([get_event_with_status(e) for e in events])

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
        date_str = data.get('event_date')
        event.event_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
        try:
            db.session.commit()
            return jsonify(get_event_with_status(event))
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
        PhotoVote.query.filter_by(event_id=event_id).delete()
        GameState.query.filter_by(event_id=event_id).delete()
        AIQuestion.query.filter_by(event_id=event_id).delete()
        AIPlayerAnswer.query.filter_by(event_id=event_id).delete()
        AICategory.query.filter_by(event_id=event_id).delete()
        db.session.commit()

        # Po resecie nie ma kategorii AI - użytkownik może dodać własne

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

# --- API: ADMIN AI Questions Management ---
@app.route('/api/admin/ai/categories/<int:event_id>', methods=['GET'])
@admin_required
def get_admin_ai_categories(event_id):
    """Pobierz wszystkie kategorie AI dla eventu (Admin)"""
    categories = AICategory.query.filter_by(event_id=event_id).all()
    result = []

    for cat in categories:
        question_count = AIQuestion.query.filter_by(category_id=cat.id).count()
        result.append({
            'id': cat.id,
            'name': cat.name,
            'is_enabled': cat.is_enabled,
            'is_custom': cat.is_custom,
            'difficulty_level': cat.difficulty_level,
            'question_count': question_count
        })

    return jsonify(result)

@app.route('/api/admin/ai/questions/<int:category_id>', methods=['GET'])
@admin_required
def get_admin_ai_questions(category_id):
    """Pobierz wszystkie pytania AI dla kategorii (Admin)"""
    questions = AIQuestion.query.filter_by(category_id=category_id).all()
    return jsonify([{
        'id': q.id,
        'text': q.text,
        'option_a': q.option_a,
        'option_b': q.option_b,
        'option_c': q.option_c,
        'correct_answer': q.correct_answer,
        'source': q.source,
        'times_shown': q.times_shown,
        'times_correct': q.times_correct
    } for q in questions])

@app.route('/api/admin/ai/question/<int:question_id>', methods=['PUT', 'DELETE'])
@admin_required
def update_or_delete_ai_question(question_id):
    """Edytuj lub usuń pytanie AI (Admin)"""
    question = db.session.get(AIQuestion, question_id)

    if not question:
        return jsonify({'error': 'Nie znaleziono pytania'}), 404

    if request.method == 'PUT':
        data = request.json
        question.text = data.get('text', question.text)
        question.option_a = data.get('option_a', question.option_a)
        question.option_b = data.get('option_b', question.option_b)
        question.option_c = data.get('option_c', question.option_c)
        question.correct_answer = data.get('correct_answer', question.correct_answer)
        question.source = 'edited'
        db.session.commit()

        return jsonify({'message': 'Pytanie zaktualizowane'})

    if request.method == 'DELETE':
        db.session.delete(question)
        db.session.commit()
        return jsonify({'message': 'Pytanie usunięte'})

@app.route('/api/host/qrcodes', methods=['GET'])
@host_required
def get_host_qrcodes():
    """Zwraca wszystkie kody QR dla eventu, jeśli host ma uprawnienia Superhost"""
    event_id = session['host_event_id']
    event = db.session.get(Event, event_id)
    
    if not event or not event.is_superhost:
        return jsonify({'error': 'Brak uprawnień Superhost'}), 403
    
    qrcodes = QRCode.query.filter_by(event_id=event_id).all()
    return jsonify([{
        'id': qr.id,
        'code_identifier': qr.code_identifier,
        'color': qr.color,
        'claimed_by_player_id': qr.claimed_by_player_id
    } for qr in qrcodes])

# --- API: HOST ---
@app.route('/api/host/state', methods=['GET'])
@host_required
def get_host_game_state(): 
    return jsonify(get_full_game_state(session['host_event_id']))

@app.route('/api/host/start_game', methods=['POST'])
@host_required
def start_game():
    event_id = session['host_event_id']
    print(f"=== START GAME DEBUG ===")
    print(f"Event ID: {event_id}")
    
    try:
        # ✅ KROK 1: Najpierw resetujemy kody QR (usuwamy referencje do graczy)
        qr_codes_to_reset = QRCode.query.filter(
            QRCode.event_id == event_id, 
            QRCode.claimed_by_player_id.isnot(None)
        ).all()
        for qr in qr_codes_to_reset:
            qr.claimed_by_player_id = None
        
        # Commit żeby zapisać zmiany w kodach QR przed usunięciem graczy
        db.session.commit()
        
        # ✅ KROK 2: Teraz możemy bezpiecznie usunąć graczy i powiązane dane
        Player.query.filter_by(event_id=event_id).delete()
        PlayerScan.query.filter_by(event_id=event_id).delete()
        PlayerAnswer.query.filter_by(event_id=event_id).delete()
        FunnyPhoto.query.filter_by(event_id=event_id).delete()
        PhotoVote.query.filter_by(event_id=event_id).delete()
        
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
        
        print(f"Game state set: active=True, timer_running=True, duration={minutes}min")
        
        db.session.commit()
        
        # ✅ POPRAWKA: Pobierz świeży stan i emituj SYNCHRONICZNIE
        room = f'event_{event_id}'
        print(f"Emitting to room: {room}")
        
        # Pobierz aktualny stan po zapisie do bazy
        fresh_state = get_full_game_state(event_id)
        print(f"Fresh state to emit: time_left={fresh_state.get('time_left')}, game_active={fresh_state.get('game_active')}")
        
        # Wyemituj aktualizację stanu
        socketio.emit('game_state_update', fresh_state, room=room)
        socketio.emit('leaderboard_update', [], room=room)
        socketio.emit('password_update', fresh_state['password'], room=room)
        socketio.emit('photos_update', [], room=room)  # Resetuj galerię
        
        print(f"✅ Game started successfully! Updates emitted.")
        
        return jsonify({'message': f'Gra rozpoczęta na {minutes} minut.'})
    except Exception as e:
        print(f"❌ ERROR in start_game: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

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
    is_active = get_game_state(event_id, 'game_active', 'False') == 'True'

    if control == 'pause':
        if is_running:
            # ✅ PAUZOWANIE - zapisz dokładnie tyle czasu ile pokazuje zegar
            set_game_state(event_id, 'is_timer_running', 'False')
            set_game_state(event_id, 'pause_start_time', datetime.utcnow().isoformat())
            end_time_str = get_game_state(event_id, 'game_end_time')
            if end_time_str:
                # Zapisz dokładnie ile sekund pozostało do końca
                time_left = (datetime.fromisoformat(end_time_str) - datetime.utcnow()).total_seconds()
                set_game_state(event_id, 'time_left_on_pause', time_left)
                print(f"⏸️  Paused at: {time_left:.1f}s")
        else:
            # ✅ WZNOWIENIE - wznów dokładnie z tego samego momentu
            pause_start_str = get_game_state(event_id, 'pause_start_time')
            if pause_start_str:
                paused_duration = (datetime.utcnow() - datetime.fromisoformat(pause_start_str)).total_seconds()
                total_paused = float(get_game_state(event_id, 'total_paused_duration', 0))
                set_game_state(event_id, 'total_paused_duration', total_paused + paused_duration)
            
            # Pobierz dokładnie tyle czasu ile było podczas pauzy
            time_left = float(get_game_state(event_id, 'time_left_on_pause', 0))
            
            # ✅ Wznów z dokładnie tego samego miejsca (bez przeliczania!)
            # update_timers() zastosuje aktualną prędkość automatycznie
            new_end_time = datetime.utcnow() + timedelta(seconds=time_left)
            set_game_state(event_id, 'game_end_time', new_end_time.isoformat())
            set_game_state(event_id, 'is_timer_running', 'True')

            current_speed = float(get_game_state(event_id, 'time_speed', 1))
            print(f"▶️  Resumed at: {time_left:.1f}s (speed x{current_speed})")
    
    elif control == 'speed':
        current_speed = float(get_game_state(event_id, 'time_speed', 1))
        new_speed = float(value) if str(current_speed) != str(value) else 1
        
        print(f"⚡ Speed change: {current_speed}x → {new_speed}x")
        
        # ✅ TYLKO zmień prędkość
        # NIE modyfikuj time_left_on_pause - to zatrzymany czas!
        set_game_state(event_id, 'time_speed', new_speed)
        
        if is_active and is_running:
            print(f"   Running - update_timers() will apply x{new_speed}")
        elif is_active and not is_running:
            print(f"   Paused - x{new_speed} will be used after resume")        
    elif control == 'language_player':
        set_game_state(event_id, 'language_player', value)

    elif control == 'language_host':
        set_game_state(event_id, 'language_host', value)
    
    emit_full_state_update(f'event_{event_id}')
    return jsonify(get_full_game_state(event_id))

# ✅ NOWY ENDPOINT: Zmiana czasu gry podczas aktywnej rozgrywki
@app.route('/api/host/adjust_time', methods=['POST'])
@host_required
def adjust_time():
    """Zmienia całkowity czas gry podczas aktywnej rozgrywki"""
    event_id = session['host_event_id']
    data = request.json
    new_minutes = data.get('new_minutes')
    password = data.get('password')
    
    # Walidacja
    event = db.session.get(Event, event_id)
    if not event or not password:
        return jsonify({'error': 'Brak danych uwierzytelniających'}), 400
        
    if not event.check_password(password):
        return jsonify({'error': 'Nieprawidłowe hasło!'}), 401
    
    if not new_minutes or new_minutes < 1:
        return jsonify({'error': 'Nieprawidłowy czas (minimum 1 minuta)'}), 400
    
    # Sprawdź czy gra jest aktywna
    is_active = get_game_state(event_id, 'game_active', 'False') == 'True'
    if not is_active:
        return jsonify({'error': 'Gra nie jest aktywna'}), 403
    
    is_running = get_game_state(event_id, 'is_timer_running', 'False') == 'True'
    
    try:
        # Oblicz nowy end_time
        new_duration_seconds = int(new_minutes) * 60
        
        if is_running:
            # ✅ Jeśli gra jest uruchomiona, ustaw nowy end_time od teraz
            new_end_time = datetime.utcnow() + timedelta(seconds=new_duration_seconds)
            set_game_state(event_id, 'game_end_time', new_end_time.isoformat())
            print(f"⏰ Adjusted time while running: {new_minutes} min (new end: {new_end_time})")
        else:
            # ✅ Jeśli gra jest zapauzowana, ustaw time_left_on_pause
            set_game_state(event_id, 'time_left_on_pause', new_duration_seconds)
            # Ustaw również game_end_time na przyszłość (będzie zaktualizowany przy wznowieniu)
            new_end_time = datetime.utcnow() + timedelta(seconds=new_duration_seconds)
            set_game_state(event_id, 'game_end_time', new_end_time.isoformat())
            print(f"⏸️  Adjusted time while paused: {new_minutes} min (time_left_on_pause: {new_duration_seconds}s)")
        
        # Aktualizuj initial_game_duration (dla statystyk)
        set_game_state(event_id, 'initial_game_duration', new_duration_seconds)
        
        # Wyemituj aktualizację stanu
        emit_full_state_update(f'event_{event_id}')
        
        return jsonify({'message': f'Czas gry został zmieniony na {new_minutes} minut.'})
    except Exception as e:
        print(f"❌ ERROR in adjust_time: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ✅ NOWY ENDPOINT: Wysyłanie komunikatów na ekran gry
@app.route('/api/host/send_message', methods=['POST'])
@host_required
def send_message():
    """Wysyła komunikat na ekran gry (display)"""
    event_id = session['host_event_id']
    data = request.json
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'error': 'Wiadomość nie może być pusta'}), 400

    if len(message) > 500:
        return jsonify({'error': 'Wiadomość może mieć maksymalnie 500 znaków'}), 400

    # Zapisz komunikat w GameState dla dashboard'u graczy
    set_game_state(event_id, 'host_message', message)

    # Wyślij komunikat przez Socket.IO do ekranu gry
    room = f'event_{event_id}'
    socketio.emit('host_message', {'message': message}, room=room)

    return jsonify({'message': 'Komunikat wysłany na ekran gry'})

@app.route('/fix-db-columns-v2')
def fix_db_columns_v2():
    try:
        # Najpierw sprawdź, które kolumny już istnieją
        result = db.session.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'question'
        """)
        existing_columns = [row[0] for row in result]
        
        added = []
        
        # Dodaj brakujące kolumny
        if 'category' not in existing_columns:
            db.session.execute("ALTER TABLE question ADD COLUMN category VARCHAR(50) DEFAULT 'company'")
            added.append('category')
            
        if 'difficulty' not in existing_columns:
            db.session.execute("ALTER TABLE question ADD COLUMN difficulty VARCHAR(20) DEFAULT 'easy'")
            added.append('difficulty')
            
        if 'times_shown' not in existing_columns:
            db.session.execute("ALTER TABLE question ADD COLUMN times_shown INTEGER DEFAULT 0")
            added.append('times_shown')
            
        if 'times_correct' not in existing_columns:
            db.session.execute("ALTER TABLE question ADD COLUMN times_correct INTEGER DEFAULT 0")
            added.append('times_correct')

        if 'round' not in existing_columns:
            db.session.execute("ALTER TABLE question ADD COLUMN round INTEGER DEFAULT 1")
            added.append('round')

        db.session.commit()
        
        if added:
            return f"Dodano kolumny: {', '.join(added)}<br><br>Możesz teraz dodawać pytania!"
        else:
            return "Wszystkie kolumny już istnieją. Możesz dodawać pytania!"
            
    except Exception as e:
        db.session.rollback()
        return f"Błąd: {str(e)}"

# --- API: HOST Players & Questions ---
def calculate_max_possible_points(event_id):
    """Oblicza maksymalną możliwą liczbę punktów z aktywnych zakładek"""
    # Sprawdź czy gra jest aktywna
    game_active = get_game_state(event_id, 'game_active', 'False') == 'True'
    if not game_active:
        return 0

    total_max_points = 0
    bonus_multiplier = int(get_game_state(event_id, 'bonus_multiplier', '1'))

    # 1. Pytania (Questions) - jeśli aktywne
    questions_enabled = get_game_state(event_id, 'questions_enabled', 'True') == 'True'
    if questions_enabled:
        # Policz pytania według trudności
        easy_questions = Question.query.filter_by(event_id=event_id, difficulty='easy').count()
        medium_questions = Question.query.filter_by(event_id=event_id, difficulty='medium').count()
        hard_questions = Question.query.filter_by(event_id=event_id, difficulty='hard').count()

        # Punkty za pytania
        easy_points = int(get_game_state(event_id, 'questions_easy_points', '5'))
        medium_points = int(get_game_state(event_id, 'questions_medium_points', '10'))
        hard_points = int(get_game_state(event_id, 'questions_hard_points', '15'))

        total_max_points += (easy_questions * easy_points * bonus_multiplier)
        total_max_points += (medium_questions * medium_points * bonus_multiplier)
        total_max_points += (hard_questions * hard_points * bonus_multiplier)

    # 2. AI - jeśli aktywne
    ai_enabled = get_game_state(event_id, 'ai_enabled', 'True') == 'True'
    if ai_enabled:
        # Policz pytania AI według trudności
        easy_ai = AIQuestion.query.filter_by(event_id=event_id, difficulty='easy').count()
        medium_ai = AIQuestion.query.filter_by(event_id=event_id, difficulty='medium').count()
        hard_ai = AIQuestion.query.filter_by(event_id=event_id, difficulty='hard').count()

        # Punkty za AI
        ai_easy_points = int(get_game_state(event_id, 'ai_easy_points', '5'))
        ai_medium_points = int(get_game_state(event_id, 'ai_medium_points', '10'))
        ai_hard_points = int(get_game_state(event_id, 'ai_hard_points', '15'))

        total_max_points += (easy_ai * ai_easy_points)
        total_max_points += (medium_ai * ai_medium_points)
        total_max_points += (hard_ai * ai_hard_points)

    # 3. Wróżka AI (Fortune) - jeśli aktywne
    fortune_enabled = get_game_state(event_id, 'fortune_enabled', 'False') == 'True'
    if fortune_enabled:
        fortune_points = int(get_game_state(event_id, 'fortune_points', '5'))
        # Zakładam że każdy gracz może użyć wróżki tylko raz
        # Więc maksymalne punkty to fortune_points na gracza
        # Ale nie wiemy ile graczy jest, więc liczymy dla jednego gracza
        total_max_points += fortune_points

    # 4. Minigry - jeśli aktywne
    minigames_enabled = get_game_state(event_id, 'minigames_enabled', 'True') == 'True'
    if minigames_enabled:
        completion_points = int(get_game_state(event_id, 'minigame_completion_points', '10'))

        # Policz aktywne minigry
        active_minigames = 0
        if get_game_state(event_id, 'minigame_tetris_disabled', 'False') == 'False':
            active_minigames += 1
        if get_game_state(event_id, 'minigame_arkanoid_disabled', 'False') == 'False':
            active_minigames += 1
        if get_game_state(event_id, 'minigame_snake_disabled', 'False') == 'False':
            active_minigames += 1
        if get_game_state(event_id, 'minigame_trex_disabled', 'False') == 'False':
            active_minigames += 1

        total_max_points += (active_minigames * completion_points * bonus_multiplier)

    # 5. Foto - jeśli aktywne (nie uwzględniamy polubień)
    photo_enabled = get_game_state(event_id, 'photo_enabled', 'True') != 'False'
    if photo_enabled:
        selfie_points = int(get_game_state(event_id, 'photo_selfie_points', '10'))
        # Zakładamy że gracz może zrobić jedno zdjęcie
        total_max_points += selfie_points

    return total_max_points

@app.route('/api/host/players', methods=['GET'])
@host_required
def get_players():
    event_id = session['host_event_id']
    players = Player.query.filter_by(event_id=event_id).order_by(Player.score.desc()).all()

    # Oblicz maksymalne możliwe punkty
    max_points = calculate_max_possible_points(event_id)

    # Dodaj % ukończenia dla każdego gracza
    players_data = []
    for p in players:
        completion_percentage = None
        if max_points > 0:
            completion_percentage = round((p.score / max_points) * 100, 1)

        players_data.append({
            'id': p.id,
            'name': p.name,
            'score': p.score,
            'warnings': p.warnings,
            'completion_percentage': completion_percentage
        })

    return jsonify(players_data)

@app.route('/api/host/player/<int:player_id>/warn', methods=['POST'])
@host_required
def warn_player(player_id):
    player = db.session.get(Player, player_id)
    if player and player.event_id == session['host_event_id']:
        player.warnings += 1
        db.session.commit()
        return jsonify({'warnings': player.warnings})
    return jsonify({'error': 'Nie znaleziono gracza'}), 404

@app.route('/api/host/player/<int:player_id>', methods=['DELETE', 'PUT'])
@host_required
def manage_player(player_id):
    player = db.session.get(Player, player_id)

    if not player or player.event_id != session['host_event_id']:
        return jsonify({'error': 'Nie znaleziono gracza'}), 404

    if request.method == 'DELETE':
        db.session.delete(player)
        db.session.commit()
        emit_leaderboard_update(f'event_{session["host_event_id"]}')
        return jsonify({'message': 'Gracz usunięty'})

    elif request.method == 'PUT':
        data = request.json
        new_name = data.get('name', '').strip()
        new_score = data.get('score')

        if not new_name:
            return jsonify({'error': 'Nazwa gracza nie może być pusta'}), 400

        if new_score is None or not isinstance(new_score, int) or new_score < 0:
            return jsonify({'error': 'Nieprawidłowa liczba punktów'}), 400

        # Aktualizuj dane gracza
        player.name = new_name
        player.score = new_score
        db.session.commit()

        # Wyślij aktualizację rankingu
        emit_leaderboard_update(f'event_{session["host_event_id"]}')

        return jsonify({
            'message': 'Gracz zaktualizowany',
            'player': {
                'id': player.id,
                'name': player.name,
                'score': player.score
            }
        })

# --- API: HOST Minigames ---
@app.route('/api/host/minigames/status', methods=['GET'])
@host_required
def get_minigames_status():
    event_id = session['host_event_id']
    tetris_disabled = get_game_state(event_id, 'minigame_tetris_disabled', 'False') == 'True'
    arkanoid_disabled = get_game_state(event_id, 'minigame_arkanoid_disabled', 'False') == 'True'
    snake_disabled = get_game_state(event_id, 'minigame_snake_disabled', 'False') == 'True'
    trex_disabled = get_game_state(event_id, 'minigame_trex_disabled', 'False') == 'True'
    return jsonify({
        'tetris_enabled': not tetris_disabled,
        'arkanoid_enabled': not arkanoid_disabled,
        'snake_enabled': not snake_disabled,
        'trex_enabled': not trex_disabled
    })

@app.route('/api/host/minigames/toggle', methods=['POST'])
@host_required
def toggle_minigame():
    event_id = session['host_event_id']
    data = request.json
    game_type = data.get('game_type')
    enabled = data.get('enabled', False)
    
    if game_type == 'tetris':
        # Zapisujemy czy gra jest WYŁĄCZONA (odwrotna logika - domyślnie włączona)
        set_game_state(event_id, 'minigame_tetris_disabled', 'False' if enabled else 'True')
        return jsonify({
            'message': f'Tetris {"aktywowany" if enabled else "deaktywowany"}',
            'tetris_enabled': enabled
        })
    elif game_type == 'arkanoid':
        # Zapisujemy czy gra jest WYŁĄCZONA (odwrotna logika - domyślnie włączona)
        set_game_state(event_id, 'minigame_arkanoid_disabled', 'False' if enabled else 'True')
        return jsonify({
            'message': f'Arkanoid {"aktywowany" if enabled else "deaktywowany"}',
            'arkanoid_enabled': enabled
        })
    elif game_type == 'snake':
        # Zapisujemy czy gra jest WYŁĄCZONA (odwrotna logika - domyślnie włączona)
        set_game_state(event_id, 'minigame_snake_disabled', 'False' if enabled else 'True')
        return jsonify({
            'message': f'Snake {"aktywowany" if enabled else "deaktywowany"}',
            'snake_enabled': enabled
        })
    elif game_type == 'trex':
        # Zapisujemy czy gra jest WYŁĄCZONA (odwrotna logika - domyślnie włączona)
        set_game_state(event_id, 'minigame_trex_disabled', 'False' if enabled else 'True')
        return jsonify({
            'message': f'T-Rex {"aktywowany" if enabled else "deaktywowany"}',
            'trex_enabled': enabled
        })

    return jsonify({'error': 'Nieznany typ minigry'}), 400

@app.route('/api/host/minigames/settings', methods=['GET', 'POST'])
@host_required
def minigames_settings():
    event_id = session['host_event_id']

    if request.method == 'GET':
        # Pobieranie ustawień
        completion_points = int(get_game_state(event_id, 'minigame_completion_points', '10'))
        target_points = int(get_game_state(event_id, 'minigame_target_points', '20'))
        player_choice = get_game_state(event_id, 'minigame_player_choice', 'False') == 'True'

        return jsonify({
            'completion_points': completion_points,
            'target_points': target_points,
            'player_choice': player_choice
        })

    elif request.method == 'POST':
        # Zapisywanie ustawień
        data = request.json
        setting_type = data.get('setting_type')
        value = data.get('value')

        if setting_type == 'completion_points':
            set_game_state(event_id, 'minigame_completion_points', str(value))
            return jsonify({
                'message': f'Liczba punktów za przejście gry ustawiona na {value}',
                'completion_points': value
            })

        elif setting_type == 'target_points':
            set_game_state(event_id, 'minigame_target_points', str(value))
            return jsonify({
                'message': f'Liczba punktów do zdobycia w grze ustawiona na {value}',
                'target_points': value
            })

        elif setting_type == 'player_choice':
            set_game_state(event_id, 'minigame_player_choice', 'True' if value else 'False')
            return jsonify({
                'message': f'Wybór gry {"włączony" if value else "wyłączony"}',
                'player_choice': value
            })

        return jsonify({'error': 'Nieznany typ ustawienia'}), 400

@app.route('/api/player/minigames/available', methods=['GET'])
def get_available_minigames():
    """Endpoint dla gracza do pobrania dostępnych minigrów"""
    event_id = request.args.get('event_id', type=int)
    if not event_id:
        return jsonify({'error': 'Brak event_id'}), 400

    # Pobierz ustawienia
    player_choice = get_game_state(event_id, 'minigame_player_choice', 'False') == 'True'
    target_points = int(get_game_state(event_id, 'minigame_target_points', '20'))
    completion_points = int(get_game_state(event_id, 'minigame_completion_points', '10'))

    # Sprawdź które gry są aktywne
    available_games = []

    if get_game_state(event_id, 'minigame_tetris_disabled', 'False') == 'False':
        available_games.append({'id': 'tetris', 'name': '🎮 Tetris', 'description': 'Ułóż linie'})

    if get_game_state(event_id, 'minigame_arkanoid_disabled', 'False') == 'False':
        available_games.append({'id': 'arkanoid', 'name': '🏓 Arkanoid', 'description': 'Zbij cegły'})

    if get_game_state(event_id, 'minigame_snake_disabled', 'False') == 'False':
        available_games.append({'id': 'snake', 'name': '🐍 Snake', 'description': 'Zbieraj jedzenie'})

    if get_game_state(event_id, 'minigame_trex_disabled', 'False') == 'False':
        available_games.append({'id': 'trex', 'name': '🦖 T-Rex', 'description': 'Unikaj przeszkód'})

    return jsonify({
        'player_choice': player_choice,
        'target_points': target_points,
        'completion_points': completion_points,
        'available_games': available_games
    })

@app.route('/api/host/questions', methods=['GET', 'POST'])
@host_required
def host_questions():
    event_id = session['host_event_id']
    if request.method == 'POST':
        data = request.json
        round_num = data.get('round', 1)
        new_q = Question(
            text=data['text'],
            option_a=data['answers'][0],
            option_b=data['answers'][1],
            option_c=data['answers'][2],
            correct_answer=data['correctAnswer'],
            letter_to_reveal=data.get('letterToReveal', 'X').upper(),
            category=data.get('category', 'company'),
            difficulty=data.get('difficulty', 'easy'),
            round=round_num,
            event_id=event_id
        )
        db.session.add(new_q)
        db.session.commit()
        return jsonify({'id': new_q.id})

    # GET: filter by round if provided
    round_num = request.args.get('round', type=int)
    if round_num:
        questions = Question.query.filter_by(event_id=event_id, round=round_num).all()
    else:
        questions = Question.query.filter_by(event_id=event_id, round=1).all()

    return jsonify([{
        'id': q.id,
        'text': q.text,
        'answers': [q.option_a, q.option_b, q.option_c],
        'correctAnswer': q.correct_answer,
        'letterToReveal': q.letter_to_reveal,
        'category': q.category,
        'difficulty': q.difficulty,
        'times_shown': q.times_shown,
        'times_correct': q.times_correct
    } for q in questions])

@app.route('/api/host/question/<int:question_id>', methods=['PUT', 'DELETE'])
@host_required
def manage_question(question_id):
    q = db.session.get(Question, question_id)
    if not q or q.event_id != session['host_event_id']:
        return jsonify({'error': 'Nie znaleziono pytania'}), 404
    
    if request.method == 'PUT':
        data = request.json
        q.text = data.get('text', q.text)
        q.option_a = data['answers'][0]
        q.option_b = data['answers'][1]
        q.option_c = data['answers'][2]
        q.correct_answer = data.get('correctAnswer', q.correct_answer)
        q.letter_to_reveal = data.get('letterToReveal', q.letter_to_reveal).upper()
        q.category = data.get('category', q.category)
        q.difficulty = data.get('difficulty', q.difficulty)
        q.round = data.get('round', q.round)
        db.session.commit()
        return jsonify({'message': 'Pytanie zaktualizowane'})
    
    if request.method == 'DELETE':
        db.session.delete(q)
        db.session.commit()
        return jsonify({'message': 'Pytanie usunięte'})

@app.route('/api/host/qrcodes/counts', methods=['GET'])
@host_required
def get_host_qr_counts():
    event_id = session['host_event_id']
    event = db.session.get(Event, event_id)
    
    if not event or not event.is_superhost:
        return jsonify({'error': 'Brak uprawnień Superhost'}), 403
    
    counts = {
        'red': QRCode.query.filter_by(event_id=event_id, color='red').count(),
        'white_trap': QRCode.query.filter_by(event_id=event_id, color='white_trap').count(),
        'green': QRCode.query.filter_by(event_id=event_id, color='green').count(),
        'pink': QRCode.query.filter_by(event_id=event_id, color='pink').count()
    }
    return jsonify(counts)

# --- API: HOST AI Categories ---
@app.route('/api/host/ai/categories', methods=['GET', 'POST'])
@host_required
def manage_ai_categories():
    event_id = session['host_event_id']

    if request.method == 'GET':
        categories = AICategory.query.filter_by(event_id=event_id).all()
        return jsonify([{
            'id': c.id,
            'name': c.name,
            'is_enabled': c.is_enabled,
            'is_custom': c.is_custom,
            'difficulty_level': c.difficulty_level
        } for c in categories])

    if request.method == 'POST':
        data = request.json
        name = data.get('name', '').strip()
        difficulty = data.get('difficulty_level', 'easy')

        if not name:
            return jsonify({'error': 'Nazwa kategorii nie może być pusta'}), 400

        # Sprawdź czy kategoria już istnieje
        existing = AICategory.query.filter_by(event_id=event_id, name=name).first()
        if existing:
            return jsonify({'error': 'Kategoria o tej nazwie już istnieje'}), 409

        new_category = AICategory(
            event_id=event_id,
            name=name,
            is_enabled=True,
            is_custom=True,
            difficulty_level=difficulty
        )
        db.session.add(new_category)
        db.session.commit()

        return jsonify({
            'id': new_category.id,
            'name': new_category.name,
            'is_enabled': new_category.is_enabled,
            'is_custom': new_category.is_custom,
            'difficulty_level': new_category.difficulty_level
        })

@app.route('/api/host/ai/category/<int:category_id>', methods=['PUT', 'DELETE'])
@host_required
def update_or_delete_ai_category(category_id):
    event_id = session['host_event_id']
    category = AICategory.query.filter_by(id=category_id, event_id=event_id).first()

    if not category:
        return jsonify({'error': 'Nie znaleziono kategorii'}), 404

    if request.method == 'PUT':
        data = request.json
        category.is_enabled = data.get('is_enabled', category.is_enabled)
        category.difficulty_level = data.get('difficulty_level', category.difficulty_level)
        db.session.commit()

        return jsonify({
            'id': category.id,
            'name': category.name,
            'is_enabled': category.is_enabled,
            'is_custom': category.is_custom,
            'difficulty_level': category.difficulty_level
        })

    if request.method == 'DELETE':
        if not category.is_custom:
            return jsonify({'error': 'Nie można usunąć predefiniowanej kategorii'}), 403

        AIQuestion.query.filter_by(category_id=category_id).delete()
        db.session.delete(category)
        db.session.commit()

        return jsonify({'message': 'Kategoria została usunięta'})

@app.route('/api/host/ai/generate_questions/<int:category_id>', methods=['POST'])
@host_required
def generate_questions_for_category(category_id):
    """Generuje pytania AI dla custom kategorii używając Claude API"""
    event_id = session['host_event_id']
    category = AICategory.query.filter_by(id=category_id, event_id=event_id).first()

    if not category:
        return jsonify({'error': 'Nie znaleziono kategorii'}), 404

    if not category.is_custom:
        return jsonify({'error': 'Generowanie pytań dostępne tylko dla custom kategorii'}), 403

    data = request.json
    count = data.get('count', 10)

    # Generuj pytania używając Claude API
    result = generate_ai_questions_with_claude(
        category.name,
        category.difficulty_level,
        count
    )

    if 'error' in result:
        return jsonify(result), 500

    # Zapisz wygenerowane pytania do bazy
    generated_count = 0
    for q_data in result['questions']:
        new_question = AIQuestion(
            event_id=event_id,
            category_id=category_id,
            text=q_data['text'],
            option_a=q_data['option_a'],
            option_b=q_data['option_b'],
            option_c=q_data['option_c'],
            correct_answer=q_data['correct_answer'].upper(),
            source='generated'
        )
        db.session.add(new_question)
        generated_count += 1

    db.session.commit()

    return jsonify({
        'message': f'Wygenerowano {generated_count} pytań dla kategorii {category.name}',
        'count': generated_count
    })

@app.route('/api/host/ai/questions/<int:category_id>', methods=['GET'])
@host_required
def get_host_ai_questions(category_id):
    """Pobierz wszystkie pytania AI dla kategorii (Host)"""
    event_id = session['host_event_id']
    category = AICategory.query.filter_by(id=category_id, event_id=event_id).first()

    if not category:
        return jsonify({'error': 'Nie znaleziono kategorii'}), 404

    questions = AIQuestion.query.filter_by(category_id=category_id, event_id=event_id).all()
    return jsonify([{
        'id': q.id,
        'text': q.text,
        'option_a': q.option_a,
        'option_b': q.option_b,
        'option_c': q.option_c,
        'correct_answer': q.correct_answer,
        'source': q.source,
        'times_shown': q.times_shown,
        'times_correct': q.times_correct
    } for q in questions])

@app.route('/api/host/ai/question/<int:question_id>', methods=['PUT', 'DELETE'])
@host_required
def update_or_delete_host_ai_question(question_id):
    """Edytuj lub usuń pytanie AI (Host)"""
    event_id = session['host_event_id']
    question = AIQuestion.query.filter_by(id=question_id, event_id=event_id).first()

    if not question:
        return jsonify({'error': 'Nie znaleziono pytania'}), 404

    if request.method == 'PUT':
        data = request.json
        question.text = data.get('text', question.text)
        question.option_a = data.get('option_a', question.option_a)
        question.option_b = data.get('option_b', question.option_b)
        question.option_c = data.get('option_c', question.option_c)
        question.correct_answer = data.get('correct_answer', question.correct_answer)
        question.source = 'edited'
        db.session.commit()

        return jsonify({'message': 'Pytanie zaktualizowane'})

    if request.method == 'DELETE':
        db.session.delete(question)
        db.session.commit()
        return jsonify({'message': 'Pytanie usunięte'})

@app.route('/api/host/qrcodes/generate', methods=['POST'])
@host_required
def host_generate_qr_codes():
    event_id = session['host_event_id']
    event = db.session.get(Event, event_id)
    
    if not event or not event.is_superhost:
        return jsonify({'error': 'Brak uprawnień Superhost'}), 403
    
    if get_game_state(event_id, 'game_active', 'False') == 'True':
        return jsonify({'message': 'Nie można zmieniać kodów podczas aktywnej gry.'}), 403
    
    data = request.json
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

# --- API: PLAYER ---
@app.route('/api/player/register', methods=['POST'])
def register_player():
    data = request.json
    name, event_id = data.get('name'), data.get('event_id')
    if Player.query.filter_by(name=name, event_id=event_id).first():
        return jsonify({'error': 'Ta nazwa jest już zajęta.'}), 409
    new_player = Player(name=name, event_id=event_id)
    db.session.add(new_player)
    db.session.commit()
    emit_leaderboard_update(f'event_{event_id}')
    return jsonify({'id': new_player.id, 'name': new_player.name, 'score': 0})

@app.route('/api/player/upload_photo', methods=['POST'])
def upload_photo():
    """Upload selfie photo from player"""
    print("=" * 60)
    print("📸 PHOTO UPLOAD REQUEST RECEIVED")
    print("=" * 60)
    try:
        # Get form data
        player_id = request.form.get('player_id')
        event_id = request.form.get('event_id')
        photo_file = request.files.get('photo')

        print(f"📋 Form data: player_id={player_id}, event_id={event_id}")
        print(f"📁 Photo file: {photo_file}")
        print(f"📁 Photo filename: {photo_file.filename if photo_file else 'None'}")

        if not player_id or not event_id or not photo_file:
            print("❌ Missing required data")
            return jsonify({'error': 'Brak wymaganych danych'}), 400

        player_id = int(player_id)
        event_id = int(event_id)
        print(f"✅ Parsed IDs: player_id={player_id}, event_id={event_id}")

        # Verify player exists
        player = db.session.get(Player, player_id)
        if not player or player.event_id != event_id:
            print(f"❌ Player not found or event mismatch")
            return jsonify({'error': 'Nieprawidłowy gracz'}), 404

        print(f"✅ Player verified: {player.name}")

        # Generate unique filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{event_id}_{player_id}_{timestamp}.jpg"
        filepath = os.path.join('static', 'photos', filename)

        print(f"📝 Filename: {filename}")
        print(f"📂 Filepath: {filepath}")

        # Save file
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        photo_file.save(filepath)

        print(f"💾 File saved to disk")

        # Create database record
        image_url = f"/static/photos/{filename}"
        new_photo = FunnyPhoto(
            player_id=player_id,
            player_name=player.name,
            image_url=image_url,
            event_id=event_id
        )
        db.session.add(new_photo)

        print(f"📊 Database record created")

        # Award points
        bonus_multiplier = int(get_game_state(event_id, 'bonus_multiplier', '1'))
        selfie_points = int(get_game_state(event_id, 'photo_selfie_points', '10'))
        points_awarded = selfie_points * bonus_multiplier

        print(f"🎯 Points calculation: {selfie_points} × {bonus_multiplier} = {points_awarded}")

        player.score += points_awarded
        db.session.commit()

        print(f"✅ Database committed, player score updated")

        # Emit updates
        emit_leaderboard_update(f'event_{event_id}')

        print(f"📡 Leaderboard update emitted")

        # Notify via SocketIO about new photo
        socketio.emit('new_photo', {
            'photo': {
                'id': new_photo.id,
                'player_name': player.name,
                'image_url': image_url,
                'votes': 0,
                'timestamp': new_photo.timestamp.isoformat()
            }
        }, room=f'event_{event_id}')

        print(f"📡 New photo notification emitted")
        print(f"🎉 Upload successful!")
        print("=" * 60)

        return jsonify({
            'success': True,
            'points': points_awarded,
            'photo_id': new_photo.id,
            'message': f'Zdjęcie zapisane! Otrzymujesz {points_awarded} punktów!'
        })

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error uploading photo: {e}")
        print(f"❌ Error type: {type(e)}")
        import traceback
        print(f"❌ Traceback:")
        traceback.print_exc()
        print("=" * 60)
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/scan_qr', methods=['POST'])
def scan_qr():
    data = request.json
    player_id, qr_id, event_id = data.get('player_id'), data.get('qr_code'), data.get('event_id')
    
    # DEBUG LOGGING
    print(f"=== SCAN QR DEBUG ===")
    print(f"Received data: {data}")
    print(f"Player ID: {player_id}, QR Code: {qr_id}, Event ID: {event_id}")
    
    # ✅ WALIDACJA: Sprawdź czy gracz istnieje
    player = db.session.get(Player, player_id) if player_id else None
    
    print(f"Player found: {player is not None}")
    if player:
        print(f"Player name: {player.name}, Event ID: {player.event_id}")
    
    # ✅ Jeśli gracz nie istnieje, zwróć błąd z flagą czyszczenia
    if not player:
        print(f"ERROR: Player ID {player_id} not found in database!")
        return jsonify({
            'status': 'error',
            'message': 'Twoje dane wygasły po resecie gry. Odśwież stronę (F5) i zarejestruj się ponownie.',
            'clear_storage': True
        }), 404
    
    # ✅ Sprawdź czy event_id gracza zgadza się z event_id w żądaniu
    if player.event_id != event_id:
        print(f"ERROR: Player event mismatch. Player event: {player.event_id}, Request event: {event_id}")
        return jsonify({
            'status': 'error',
            'message': 'Nieprawidłowy event. Odśwież stronę.',
            'clear_storage': True
        }), 400
    
    # Znajdź kod QR
    qr_code = QRCode.query.filter_by(code_identifier=qr_id, event_id=event_id).first()
    
    print(f"QR Code found: {qr_code is not None}")
    if qr_code:
        print(f"QR Code color: {qr_code.color}")
    
    if not qr_code:
        print(f"ERROR: QR code not found!")
        return jsonify({'message': 'Nieprawidłowy kod QR.'}), 404
    
    # Sprawdź czy gra jest aktywna
    game_active = get_game_state(event_id, 'game_active', 'False')
    print(f"Game active: {game_active}")
    
    if game_active != 'True':
        print(f"ERROR: Game not active!")
        return jsonify({'message': 'Gra nie jest aktywna.'}), 403

    print(f"QR Code color check: {qr_code.color}")

    # BIAŁE I ŻÓŁTE KODY (wielorazowe - quizy)
    if qr_code.color in ['white', 'yellow']:
        last_scan = PlayerScan.query.filter_by(
            player_id=player_id,
            color_category=qr_code.color
        ).order_by(PlayerScan.scan_time.desc()).first()

        if last_scan and datetime.utcnow() < last_scan.scan_time + timedelta(minutes=5):
            wait_time = (last_scan.scan_time + timedelta(minutes=5) - datetime.utcnow()).seconds
            return jsonify({
                'status': 'wait',
                'message': f'Odczekaj jeszcze {wait_time // 60}m {wait_time % 60}s.'
            }), 429

        db.session.add(PlayerScan(
            player_id=player_id,
            qrcode_id=qr_code.id,
            event_id=event_id,
            color_category=qr_code.color
        ))
        db.session.commit()

        # BIAŁY KOD - wybór między pytaniami ręcznymi i AI
        if qr_code.color == 'white':
            # Sprawdź czy są dostępne pytania AI
            # Sprawdź czy w sesji jest zapisany poziom trudności dla AI (z kodów QR hosta)
            ai_difficulty_filter = session.get('ai_difficulty', None)

            # Filtruj kategorie AI według poziomu trudności jeśli jest zapisany
            query = AICategory.query.filter_by(event_id=event_id, is_enabled=True)

            if ai_difficulty_filter and ai_difficulty_filter in ['easy', 'medium', 'hard']:
                # Mapowanie poziomów trudności (hard -> advanced dla AI)
                difficulty_map = {'easy': 'easy', 'medium': 'medium', 'hard': 'advanced'}
                mapped_difficulty = difficulty_map[ai_difficulty_filter]
                query = query.filter_by(difficulty_level=mapped_difficulty)

            active_ai_categories = query.all()

            # Jeśli są aktywne kategorie AI, pokaż wybór kategorii
            if active_ai_categories:
                return jsonify({
                    'status': 'ai_categories',
                    'categories': [{
                        'id': cat.id,
                        'name': cat.name,
                        'difficulty_level': cat.difficulty_level
                    } for cat in active_ai_categories]
                })
            # Jeśli nie ma kategorii AI, pokaż pytania ręczne
            quiz_category = 'company'
        else:
            # ŻÓŁTY KOD - pytania world
            quiz_category = 'world'

        # Pokaż pytania ręczne (dla żółtego lub białego bez kategorii AI)
        answered_ids = [ans.question_id for ans in PlayerAnswer.query.filter_by(player_id=player_id).all()]

        # Sprawdź czy w sesji jest zapisany poziom trudności (z kodów QR hosta)
        difficulty_filter = session.get('questions_difficulty', None)

        # Filtruj pytania według poziomu trudności jeśli jest zapisany
        query = Question.query.filter(
            Question.id.notin_(answered_ids),
            Question.event_id == event_id,
            Question.category == quiz_category
        )

        if difficulty_filter and difficulty_filter in ['easy', 'medium', 'hard']:
            query = query.filter(Question.difficulty == difficulty_filter)

        question = query.order_by(db.func.random()).first()

        if not question:
            return jsonify({
                'status': 'info',
                'message': 'Odpowiedziałeś na wszystkie pytania z tej kategorii!'
            })

        return jsonify({
            'status': 'question',
            'question': {
                'id': question.id,
                'text': question.text,
                'option_a': question.option_a,
                'option_b': question.option_b,
                'option_c': question.option_c
            }
        })
    
    # 🎮 ZIELONY KOD - MINIGRY (Tetris lub Arkanoid)
    elif qr_code.color == 'green':
        print(f"=== GREEN CODE - MINIGAME MODE ===")
        
        # Sprawdź czy minigry są aktywne
        tetris_disabled = get_game_state(event_id, 'minigame_tetris_disabled', 'False')
        arkanoid_disabled = get_game_state(event_id, 'minigame_arkanoid_disabled', 'False')
        snake_disabled = get_game_state(event_id, 'minigame_snake_disabled', 'False')
        trex_disabled = get_game_state(event_id, 'minigame_trex_disabled', 'False')

        print(f"Tetris disabled: {tetris_disabled}, Arkanoid disabled: {arkanoid_disabled}, Snake disabled: {snake_disabled}, T-Rex disabled: {trex_disabled}")

        # Jeśli wszystkie minigry są wyłączone
        if tetris_disabled == 'True' and arkanoid_disabled == 'True' and snake_disabled == 'True' and trex_disabled == 'True':
            message = 'Wszystkie minigry zostały wyłączone przez organizatora.'
            print(f"All minigames DISABLED - returning error")
            return jsonify({'status': 'info', 'message': message})

        # Sprawdź postęp gracza we wszystkich grach
        tetris_score_key = f'minigame_tetris_score_{player_id}'
        arkanoid_score_key = f'minigame_arkanoid_score_{player_id}'
        snake_score_key = f'minigame_snake_score_{player_id}'
        trex_score_key = f'minigame_trex_score_{player_id}'

        current_tetris_score = int(get_game_state(event_id, tetris_score_key, '0'))
        current_arkanoid_score = int(get_game_state(event_id, arkanoid_score_key, '0'))
        current_snake_score = int(get_game_state(event_id, snake_score_key, '0'))
        current_trex_score = int(get_game_state(event_id, trex_score_key, '0'))

        print(f"Player {player_id} - Tetris: {current_tetris_score}/20, Arkanoid: {current_arkanoid_score}/20, Snake: {current_snake_score}/20, T-Rex: {current_trex_score}/20")

        # Sprawdź czy gracz ukończył wszystkie gry
        tetris_completed = current_tetris_score >= 20
        arkanoid_completed = current_arkanoid_score >= 20
        snake_completed = current_snake_score >= 20
        trex_completed = current_trex_score >= 20

        # Jeśli ukończył wszystkie, nie może grać więcej
        if tetris_completed and arkanoid_completed and snake_completed and trex_completed:
            message = 'Ukończyłeś już wszystkie minigry! Świetna robota!'
            return jsonify({'status': 'info', 'message': message})

        # Wybierz dostępną minigrę
        available_games = []

        if tetris_disabled != 'True' and not tetris_completed:
            available_games.append('tetris')

        if arkanoid_disabled != 'True' and not arkanoid_completed:
            available_games.append('arkanoid')

        if snake_disabled != 'True' and not snake_completed:
            available_games.append('snake')

        if trex_disabled != 'True' and not trex_completed:
            available_games.append('trex')
        
        # Jeśli nie ma dostępnych gier
        if not available_games:
            message = 'Brak dostępnych minigier do ukończenia.'
            return jsonify({'status': 'info', 'message': message})
        
        # Wybierz grę (losowo jeśli są dostępne, lub tę jedną dostępną)
        selected_game = random.choice(available_games)

        if selected_game == 'tetris':
            print(f"🎮 Starting Tetris for player {player_id}")
            return jsonify({
                'status': 'minigame',
                'game': 'tetris',
                'current_score': current_tetris_score,
                'message': f'🎮 Minigra Tetris! Twój postęp: {current_tetris_score}/20 pkt'
            })
        elif selected_game == 'arkanoid':
            print(f"🏓 Starting Arkanoid for player {player_id}")
            return jsonify({
                'status': 'minigame',
                'game': 'arkanoid',
                'current_score': current_arkanoid_score,
                'message': f'🏓 Minigra Arkanoid! Twój postęp: {current_arkanoid_score}/20 pkt'
            })
        elif selected_game == 'snake':
            print(f"🐍 Starting Snake for player {player_id}")
            return jsonify({
                'status': 'minigame',
                'game': 'snake',
                'current_score': current_snake_score,
                'message': f'🐍 Minigra Snake! Twój postęp: {current_snake_score}/20 pkt'
            })
        else:  # trex
            print(f"🦖 Starting T-Rex for player {player_id}")
            return jsonify({
                'status': 'minigame',
                'game': 'trex',
                'current_score': current_trex_score,
                'message': f'🦖 Minigra T-Rex! Twój postęp: {current_trex_score}/20 pkt'
            })
    
    # JEDNORAZOWE KODY (czerwone, pułapki, różowe)
    else:
        if qr_code.claimed_by_player_id:
            return jsonify({
                'status': 'error', 
                'message': 'Ten kod został już wykorzystany.'
            }), 403
        
        qr_code.claimed_by_player_id = player_id
        
        # CZERWONY KOD
        if qr_code.color == 'red':
            player.score += 50
            message = 'Kod specjalny! Zdobywasz 50 punktów!'
        
        # PUŁAPKA
        elif qr_code.color == 'white_trap':
            player.score = max(0, player.score - 25)
            message = 'Pułapka! Tracisz 25 punktów.'
        
        # RÓŻOWY KOD - FOTO
        elif qr_code.color == 'pink':
            db.session.commit()
            return jsonify({'status': 'photo_challenge'})
        
        # NIEZNANY KOD
        else:
            message = "Niezidentyfikowany kod."
        
        db.session.commit()
        emit_leaderboard_update(f'event_{event_id}')
        return jsonify({'status': 'info', 'message': message, 'score': player.score})

# --- API: PLAYER AI Questions ---
@app.route('/api/player/ai/categories/<int:event_id>', methods=['GET'])
def get_ai_categories_for_player(event_id):
    """Pobierz aktywne kategorie AI dla gracza"""
    categories = AICategory.query.filter_by(event_id=event_id, is_enabled=True).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'difficulty_level': c.difficulty_level
    } for c in categories])

@app.route('/api/player/ai/get_question', methods=['POST'])
def get_ai_question():
    """Pobierz losowe pytanie AI z wybranej kategorii"""
    data = request.json
    player_id = data.get('player_id')
    category_id = data.get('category_id')
    event_id = data.get('event_id')

    player = db.session.get(Player, player_id)
    category = db.session.get(AICategory, category_id)

    if not player or not category:
        return jsonify({'error': 'Nieprawidłowe dane'}), 404

    # Znajdź pytania na które gracz jeszcze nie odpowiedział
    answered_ids = [ans.question_id for ans in AIPlayerAnswer.query.filter_by(player_id=player_id).all()]

    question = AIQuestion.query.filter(
        AIQuestion.category_id == category_id,
        AIQuestion.event_id == event_id,
        AIQuestion.id.notin_(answered_ids) if answered_ids else True
    ).order_by(db.func.random()).first()

    if not question:
        return jsonify({
            'status': 'info',
            'message': f'Odpowiedziałeś na wszystkie pytania z kategorii {category.name}!'
        })

    # Zwiększ licznik wyświetleń
    question.times_shown += 1
    db.session.commit()

    return jsonify({
        'status': 'question',
        'question': {
            'id': question.id,
            'text': question.text,
            'option_a': question.option_a,
            'option_b': question.option_b,
            'option_c': question.option_c,
            'category_name': category.name
        }
    })

@app.route('/api/player/ai/answer', methods=['POST'])
def process_ai_answer():
    """Przetwarza odpowiedź na pytanie AI"""
    data = request.json
    player_id = data.get('player_id')
    question_id = data.get('question_id')
    answer = data.get('answer')

    player = db.session.get(Player, player_id)
    question = db.session.get(AIQuestion, question_id)

    if not player or not question:
        return jsonify({'error': 'Nieprawidłowe dane'}), 404

    # Zapisz odpowiedź gracza
    db.session.add(AIPlayerAnswer(
        player_id=player_id,
        question_id=question_id,
        event_id=player.event_id
    ))

    if answer == question.correct_answer:
        # Zwiększ licznik poprawnych odpowiedzi
        question.times_correct += 1

        # Pobierz kategorię pytania i jej poziom trudności
        category = db.session.get(AICategory, question.category_id)
        if category:
            difficulty = category.difficulty_level
            # Pobierz punkty w zależności od poziomu trudności
            if difficulty == 'easy':
                points = int(get_game_state(player.event_id, 'ai_easy_points', '5'))
            elif difficulty == 'medium':
                points = int(get_game_state(player.event_id, 'ai_medium_points', '10'))
            elif difficulty == 'advanced':
                points = int(get_game_state(player.event_id, 'ai_hard_points', '15'))
            else:
                points = 5  # Domyślna wartość dla nieznanych poziomów trudności
        else:
            points = 5  # Domyślna wartość jeśli kategoria nie istnieje

        player.score += points

        # ✅ LOGIKA ODKRYWANIA HASŁA: Sprawdź tryb odkrywania hasła
        password_mode = get_game_state(player.event_id, 'password_reveal_mode', 'auto')

        if password_mode == 'auto':
            # Oblicz maksymalną liczbę punktów możliwych do zdobycia
            total_questions = Question.query.filter_by(event_id=player.event_id).count()
            total_ai_questions = AIQuestion.query.filter_by(event_id=player.event_id).count()
            bonus_multiplier = int(get_game_state(player.event_id, 'bonus_multiplier', '1'))

            max_possible_points = (total_questions * 10 * bonus_multiplier) + (total_ai_questions * 5)

            # Pobierz procent odkrywania
            reveal_percentage = int(get_game_state(player.event_id, 'password_reveal_percentage', '50'))

            # Oblicz próg punktów na jedną literę
            if max_possible_points > 0 and reveal_percentage > 0:
                points_per_letter = (max_possible_points * reveal_percentage) / 100

                # Oblicz ile liter gracz powinien mieć odkrytych
                letters_to_reveal = int(player.score / points_per_letter) if points_per_letter > 0 else 0

                # Pobierz aktualny stan hasła
                password_value = get_game_state(player.event_id, 'game_password', 'SAPEREVENT')
                revealed_indices_str = get_game_state(player.event_id, 'revealed_password_indices', '')

                # Parsuj odkryte indeksy
                revealed_indices = set()
                if revealed_indices_str:
                    revealed_indices = set(map(int, revealed_indices_str.split(',')))

                # Znajdź wszystkie indeksy liter (pomijając spacje)
                all_letter_indices = [i for i in range(len(password_value)) if password_value[i] != ' ']

                # Oblicz ile liter trzeba odkryć
                current_revealed_count = len([i for i in revealed_indices if i < len(password_value) and password_value[i] != ' '])
                letters_to_add = min(letters_to_reveal - current_revealed_count, len(all_letter_indices) - current_revealed_count)

                # Odkryj brakujące litery
                if letters_to_add > 0:
                    import random
                    available_indices = [i for i in all_letter_indices if i not in revealed_indices]

                    for _ in range(letters_to_add):
                        if available_indices:
                            revealed_index = random.choice(available_indices)
                            revealed_indices.add(revealed_index)
                            available_indices.remove(revealed_index)

                    # Zapisz zaktualizowane indeksy
                    revealed_indices_str = ','.join(map(str, sorted(revealed_indices)))
                    set_game_state(player.event_id, 'revealed_password_indices', revealed_indices_str)

                    emit_password_update(f'event_{player.event_id}')

        db.session.commit()
        emit_leaderboard_update(f'event_{player.event_id}')

        return jsonify({
            'correct': True,
            'score': player.score,
            'message': 'Poprawna odpowiedź! +5 punktów'
        })
    else:
        # Brak odjęcia punktów za błędną odpowiedź w pytaniach AI
        db.session.commit()

        return jsonify({
            'correct': False,
            'score': player.score,
            'message': 'Niepoprawna odpowiedź'
        })

@app.route('/api/player/answer', methods=['POST'])
def process_answer():
    data = request.json
    player_id, question_id, answer = data.get('player_id'), data.get('question_id'), data.get('answer')
    player, question = db.session.get(Player, player_id), db.session.get(Question, question_id)
    if not player or not question: return jsonify({'error': 'Invalid data'}), 404
    
    db.session.add(PlayerAnswer(player_id=player_id, question_id=question_id, event_id=player.event_id))
    bonus = int(get_game_state(player.event_id, 'bonus_multiplier', 1))
    
    # Zwiększ licznik wyświetleń
    question.times_shown += 1
    
    if answer == question.correct_answer:
        # Zwiększ licznik poprawnych odpowiedzi
        question.times_correct += 1

        # Pobierz punkty w zależności od poziomu trudności pytania
        if question.difficulty == 'easy':
            base_points = int(get_game_state(player.event_id, 'questions_easy_points', '5'))
        elif question.difficulty == 'medium':
            base_points = int(get_game_state(player.event_id, 'questions_medium_points', '10'))
        elif question.difficulty == 'hard':
            base_points = int(get_game_state(player.event_id, 'questions_hard_points', '15'))
        else:
            base_points = 10  # Domyślna wartość dla nieznanych poziomów trudności

        points = base_points * bonus
        player.score += points
        
        # ✅ ZMODYFIKOWANA LOGIKA: Sprawdź tryb odkrywania hasła
        password_mode = get_game_state(player.event_id, 'password_reveal_mode', 'auto')

        if password_mode == 'auto':
            # Oblicz maksymalną liczbę punktów możliwych do zdobycia
            total_questions = Question.query.filter_by(event_id=player.event_id).count()
            total_ai_questions = AIQuestion.query.filter_by(event_id=player.event_id).count()
            bonus_multiplier = int(get_game_state(player.event_id, 'bonus_multiplier', '1'))

            max_possible_points = (total_questions * 10 * bonus_multiplier) + (total_ai_questions * 5)

            # Pobierz procent odkrywania
            reveal_percentage = int(get_game_state(player.event_id, 'password_reveal_percentage', '50'))

            # Oblicz próg punktów na jedną literę
            if max_possible_points > 0 and reveal_percentage > 0:
                points_per_letter = (max_possible_points * reveal_percentage) / 100

                # Oblicz ile liter gracz powinien mieć odkrytych
                letters_to_reveal = int(player.score / points_per_letter) if points_per_letter > 0 else 0

                # Pobierz aktualny stan hasła
                password_value = get_game_state(player.event_id, 'game_password', 'SAPEREVENT')
                revealed_indices_str = get_game_state(player.event_id, 'revealed_password_indices', '')

                # Parsuj odkryte indeksy
                revealed_indices = set()
                if revealed_indices_str:
                    revealed_indices = set(map(int, revealed_indices_str.split(',')))

                # Znajdź wszystkie indeksy liter (pomijając spacje)
                all_letter_indices = [i for i in range(len(password_value)) if password_value[i] != ' ']

                # Oblicz ile liter trzeba odkryć
                current_revealed_count = len([i for i in revealed_indices if i < len(password_value) and password_value[i] != ' '])
                letters_to_add = min(letters_to_reveal - current_revealed_count, len(all_letter_indices) - current_revealed_count)

                # Odkryj brakujące litery
                if letters_to_add > 0:
                    import random
                    available_indices = [i for i in all_letter_indices if i not in revealed_indices]

                    for _ in range(letters_to_add):
                        if available_indices:
                            revealed_index = random.choice(available_indices)
                            revealed_indices.add(revealed_index)
                            available_indices.remove(revealed_index)

                    # Zapisz zaktualizowane indeksy
                    revealed_indices_str = ','.join(map(str, sorted(revealed_indices)))
                    set_game_state(player.event_id, 'revealed_password_indices', revealed_indices_str)

                    emit_password_update(f'event_{player.event_id}')
        
        db.session.commit()
        emit_leaderboard_update(f'event_{player.event_id}')
        return jsonify({'correct': True, 'letter': question.letter_to_reveal, 'score': player.score})
    else:
        player.score = max(0, player.score - 5)
        db.session.commit()
        emit_leaderboard_update(f'event_{player.event_id}')
        return jsonify({'correct': False, 'score': player.score})

# 🎉 ENDPOINTY DLA GŁOSOWANIA NA ZDJĘCIA

@app.route('/api/photos/<int:event_id>', methods=['GET'])
def get_photos(event_id):
    """Pobierz wszystkie zdjęcia dla danego eventu z liczbą głosów"""
    photos = FunnyPhoto.query.filter_by(event_id=event_id).order_by(FunnyPhoto.votes.desc(), FunnyPhoto.timestamp.desc()).all()
    return jsonify([{
        'id': p.id,
        'player_name': p.player_name,
        'image_url': p.image_url,
        'votes': p.votes,
        'timestamp': p.timestamp.isoformat()
    } for p in photos])

@app.route('/api/host/photo/settings/<int:event_id>', methods=['GET'])
def get_photo_settings(event_id):
    """Pobierz ustawienia foto dla danego eventu"""
    try:
        settings = {
            'selfie_points': int(get_game_state(event_id, 'photo_selfie_points', '30')),
            'like_given_points': int(get_game_state(event_id, 'photo_like_given_points', '2')),
            'like_received_points': int(get_game_state(event_id, 'photo_like_received_points', '5')),
            'max_likes': int(get_game_state(event_id, 'photo_max_likes', '10'))
        }
        return jsonify(settings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/<int:player_id>/votes', methods=['GET'])
def get_player_votes(player_id):
    """Pobierz listę ID zdjęć, które gracz polubił"""
    try:
        votes = PhotoVote.query.filter_by(player_id=player_id).all()
        photo_ids = [vote.photo_id for vote in votes]
        return jsonify(photo_ids)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/photo/<int:photo_id>/vote', methods=['POST'])
def vote_photo(photo_id):
    """Zagłosuj na zdjęcie (lub cofnij głos)"""
    data = request.json
    player_id = data.get('player_id')

    if not player_id:
        return jsonify({'error': 'Brak ID gracza'}), 400

    player = db.session.get(Player, player_id)
    photo = db.session.get(FunnyPhoto, photo_id)
    
    if not player or not photo:
        return jsonify({'error': 'Nie znaleziono gracza lub zdjęcia'}), 404
    
    # Sprawdź czy gracz już głosował na to zdjęcie
    existing_vote = PhotoVote.query.filter_by(photo_id=photo_id, player_id=player_id).first()
    
    if existing_vote:
        # Cofnij głos
        db.session.delete(existing_vote)
        photo.votes = max(0, photo.votes - 1)
        action = 'removed'
    else:
        # Dodaj głos
        new_vote = PhotoVote(photo_id=photo_id, player_id=player_id, event_id=photo.event_id)
        db.session.add(new_vote)
        photo.votes += 1
        action = 'added'
    
    db.session.commit()
    
    # Wyemituj aktualizację do wszystkich
    room = f'event_{photo.event_id}'
    socketio.emit('photo_vote_update', {
        'photo_id': photo_id, 
        'votes': photo.votes
    }, room=room)
    
    return jsonify({
        'action': action,
        'votes': photo.votes,
        'message': 'Głos oddany!' if action == 'added' else 'Głos cofnięty'
    })

@app.route('/api/photo/<int:photo_id>/check_vote/<int:player_id>', methods=['GET'])
def check_vote(photo_id, player_id):
    """Sprawdź czy gracz zagłosował na dane zdjęcie"""
    vote = PhotoVote.query.filter_by(photo_id=photo_id, player_id=player_id).first()
    return jsonify({'voted': vote is not None})

@app.route('/api/player_dashboard/state', methods=['GET'])
def get_player_dashboard_state():
    """Zwraca pełny stan gry dla panelu gracza"""
    event_id = request.args.get('event_id', type=int)
    player_id = request.args.get('player_id', type=int)

    if not event_id or not player_id:
        return jsonify({'error': 'Brak event_id lub player_id'}), 400

    player = db.session.get(Player, player_id)
    event = db.session.get(Event, event_id)

    if not player or player.event_id != event_id:
        return jsonify({'error': 'Nie znaleziono gracza'}), 404

    if not event:
        return jsonify({'error': 'Nie znaleziono eventu'}), 404

    # Pobierz stan gry
    game_state = get_full_game_state(event_id)

    # Policz aktywnych graczy
    active_players = Player.query.filter_by(event_id=event_id).count()

    # Policz dostępne punkty (pytania + AI questions)
    total_questions = Question.query.filter_by(event_id=event_id).count()
    total_ai_questions = AIQuestion.query.filter_by(event_id=event_id).count()

    # Policz ile pytań gracz już odpowiedział
    answered_questions = PlayerAnswer.query.filter_by(player_id=player_id, event_id=event_id).count()
    answered_ai_questions = AIPlayerAnswer.query.filter_by(player_id=player_id, event_id=event_id).count()

    # Oblicz możliwe punkty do zdobycia
    bonus_multiplier = int(game_state.get('bonus_multiplier', 1))
    remaining_regular_questions = max(0, total_questions - answered_questions)
    remaining_ai_questions = max(0, total_ai_questions - answered_ai_questions)

    # Regularne pytania: 10 punktów * bonus, AI pytania: 5 punktów
    points_available = (remaining_regular_questions * 10 * bonus_multiplier) + (remaining_ai_questions * 5)

    # Oblicz łączne zdobyte punkty (teoretycznie powinny być równe player.score)
    total_earned = player.score

    # Hasło
    password_value = game_state.get('game_password', 'SAPEREVENT')
    revealed_indices_str = game_state.get('revealed_password_indices', '')
    revealed_indices = set()
    if revealed_indices_str:
        revealed_indices = set(map(int, revealed_indices_str.split(',')))

    displayed_password = ""
    for i, char in enumerate(password_value):
        if char == ' ':
            displayed_password += '  '
        elif i in revealed_indices:
            displayed_password += char
        else:
            displayed_password += '_'

    # Czas pozostały
    time_remaining = 0
    if game_state.get('game_active') == 'True' and game_state.get('is_timer_running') == 'True':
        end_time_str = game_state.get('game_end_time')
        if end_time_str:
            try:
                end_time = datetime.fromisoformat(end_time_str)
                now = datetime.utcnow()
                time_remaining = max(0, int((end_time - now).total_seconds()))
            except:
                time_remaining = 0

    # Komunikat hosta (ostatni wysłany)
    host_message = game_state.get('host_message', '')

    return jsonify({
        'game_name': event.name,
        'player_name': player.name,
        'player_score': player.score,
        'active_players': active_players,
        'total_points_earned': total_earned,
        'points_available': points_available,
        'time_speed': int(game_state.get('time_speed', 1)),
        'point_bonus': int(game_state.get('bonus_multiplier', 1)),
        'time_remaining': time_remaining,
        'password_display': displayed_password,
        'host_message': host_message,
        'game_active': game_state.get('game_active') == 'True'
    })

@app.route('/api/player/selfies', methods=['GET'])
def get_player_selfies():
    """Zwraca listę selfie dla galerii gracza"""
    event_id = request.args.get('event_id', type=int)

    if not event_id:
        return jsonify({'error': 'Brak event_id'}), 400

    photos = FunnyPhoto.query.filter_by(event_id=event_id).order_by(
        FunnyPhoto.votes.desc(), FunnyPhoto.timestamp.desc()
    ).all()

    return jsonify({
        'selfies': [{
            'id': p.id,
            'player_name': p.player_name,
            'image_url': p.image_url,
            'votes': p.votes,
            'timestamp': p.timestamp.isoformat()
        } for p in photos]
    })

@app.route('/api/player/selfie/vote', methods=['POST'])
def vote_player_selfie():
    """Głosowanie na selfie z panelu gracza"""
    data = request.json
    photo_id = data.get('photo_id')
    player_id = data.get('player_id')
    event_id = data.get('event_id')

    if not photo_id or not player_id or not event_id:
        return jsonify({'error': 'Brak wymaganych danych'}), 400

    player = db.session.get(Player, player_id)
    photo = db.session.get(FunnyPhoto, photo_id)

    if not player or not photo:
        return jsonify({'error': 'Nie znaleziono gracza lub zdjęcia'}), 404

    if player.event_id != event_id or photo.event_id != event_id:
        return jsonify({'error': 'Nieprawidłowy event'}), 400

    # Sprawdź czy gracz już głosował
    existing_vote = PhotoVote.query.filter_by(photo_id=photo_id, player_id=player_id).first()

    if existing_vote:
        return jsonify({'success': False, 'message': 'Już zagłosowałeś na to zdjęcie'}), 400

    # Sprawdź maksymalną liczbę polubień
    max_likes = int(get_game_state(event_id, 'photo_max_likes', '10'))
    player_votes_count = PhotoVote.query.filter_by(player_id=player_id, event_id=event_id).count()

    if player_votes_count >= max_likes:
        return jsonify({'success': False, 'message': f'Możesz polubić maksymalnie {max_likes} zdjęć'}), 400

    # Dodaj głos
    new_vote = PhotoVote(photo_id=photo_id, player_id=player_id, event_id=event_id)
    db.session.add(new_vote)
    photo.votes += 1

    # Przyznaj punkty graczowi który polubił
    like_given_points = int(get_game_state(event_id, 'photo_like_given_points', '2'))
    player.score += like_given_points

    # Przyznaj punkty właścicielowi zdjęcia
    photo_owner = db.session.get(Player, photo.player_id)
    if photo_owner:
        like_received_points = int(get_game_state(event_id, 'photo_like_received_points', '5'))
        photo_owner.score += like_received_points

    db.session.commit()

    # Wyemituj aktualizację
    room = f'event_{event_id}'
    socketio.emit('photo_vote_update', {
        'photo_id': photo_id,
        'votes': photo.votes
    }, room=room)

    return jsonify({
        'success': True,
        'votes': photo.votes,
        'message': 'Głos oddany!'
    })

@app.route('/api/player/minigame/complete', methods=['POST'])
def complete_minigame():
    data = request.json
    player_id = data.get('player_id')
    game_type = data.get('game_type')
    score = data.get('score', 0)
    
    player = db.session.get(Player, player_id)
    if not player:
        return jsonify({'error': 'Nie znaleziono gracza'}), 404
    
    # Sprawdź czy minigra jest aktywna
    if game_type == 'tetris':
        tetris_disabled = get_game_state(player.event_id, 'minigame_tetris_disabled', 'False')
        if tetris_disabled == 'True':
            return jsonify({'error': 'Ta minigra została wyłączona'}), 403
        score_key = f'minigame_tetris_score_{player_id}'
    elif game_type == 'arkanoid':
        arkanoid_disabled = get_game_state(player.event_id, 'minigame_arkanoid_disabled', 'False')
        if arkanoid_disabled == 'True':
            return jsonify({'error': 'Ta minigra została wyłączona'}), 403
        score_key = f'minigame_arkanoid_score_{player_id}'
    elif game_type == 'snake':
        snake_disabled = get_game_state(player.event_id, 'minigame_snake_disabled', 'False')
        if snake_disabled == 'True':
            return jsonify({'error': 'Ta minigra została wyłączona'}), 403
        score_key = f'minigame_snake_score_{player_id}'
    elif game_type == 'trex':
        trex_disabled = get_game_state(player.event_id, 'minigame_trex_disabled', 'False')
        if trex_disabled == 'True':
            return jsonify({'error': 'Ta minigra została wyłączona'}), 403
        score_key = f'minigame_trex_score_{player_id}'
    else:
        return jsonify({'error': 'Nieznany typ minigry'}), 400

    # Pobierz aktualny wynik gracza w tej minigrze
    current_score = int(get_game_state(player.event_id, score_key, '0'))

    # Dodaj zdobyte punkty do sumy
    new_score = current_score + score
    set_game_state(player.event_id, score_key, str(new_score))

    game_name_map = {'tetris': 'Tetris', 'arkanoid': 'Arkanoid', 'snake': 'Snake', 'trex': 'T-Rex'}
    game_name = game_name_map.get(game_type, 'Unknown')

    # Pobierz ustawienia punktów z konfiguracji
    target_points = int(get_game_state(player.event_id, 'minigame_target_points', '20'))
    completion_points = int(get_game_state(player.event_id, 'minigame_completion_points', '10'))

    # Sprawdź czy gracz osiągnął wymaganą liczbę punktów
    if new_score >= target_points:
        # Gracz ukończył wyzwanie - przyznaj nagrody
        bonus = int(get_game_state(player.event_id, 'bonus_multiplier', 1))
        points = completion_points * bonus
        player.score += points

        # ✅ LOGIKA ODKRYWANIA HASŁA: Sprawdź tryb odkrywania hasła
        password_mode = get_game_state(player.event_id, 'password_reveal_mode', 'auto')

        if password_mode == 'auto':
            # Oblicz maksymalną liczbę punktów możliwych do zdobycia
            total_questions = Question.query.filter_by(event_id=player.event_id).count()
            total_ai_questions = AIQuestion.query.filter_by(event_id=player.event_id).count()
            bonus_multiplier = int(get_game_state(player.event_id, 'bonus_multiplier', '1'))

            max_possible_points = (total_questions * 10 * bonus_multiplier) + (total_ai_questions * 5)

            # Pobierz procent odkrywania
            reveal_percentage = int(get_game_state(player.event_id, 'password_reveal_percentage', '50'))

            # Oblicz próg punktów na jedną literę
            if max_possible_points > 0 and reveal_percentage > 0:
                points_per_letter = (max_possible_points * reveal_percentage) / 100

                # Oblicz ile liter gracz powinien mieć odkrytych
                letters_to_reveal = int(player.score / points_per_letter) if points_per_letter > 0 else 0

                # Pobierz aktualny stan hasła
                password_value = get_game_state(player.event_id, 'game_password', 'SAPEREVENT')
                revealed_indices_str = get_game_state(player.event_id, 'revealed_password_indices', '')

                # Parsuj odkryte indeksy
                revealed_indices = set()
                if revealed_indices_str:
                    revealed_indices = set(map(int, revealed_indices_str.split(',')))

                # Znajdź wszystkie indeksy liter (pomijając spacje)
                all_letter_indices = [i for i in range(len(password_value)) if password_value[i] != ' ']

                # Oblicz ile liter trzeba odkryć
                current_revealed_count = len([i for i in revealed_indices if i < len(password_value) and password_value[i] != ' '])
                letters_to_add = min(letters_to_reveal - current_revealed_count, len(all_letter_indices) - current_revealed_count)

                # Odkryj brakujące litery
                if letters_to_add > 0:
                    import random
                    available_indices = [i for i in all_letter_indices if i not in revealed_indices]

                    for _ in range(letters_to_add):
                        if available_indices:
                            revealed_index = random.choice(available_indices)
                            revealed_indices.add(revealed_index)
                            available_indices.remove(revealed_index)

                    # Zapisz zaktualizowane indeksy
                    revealed_indices_str = ','.join(map(str, sorted(revealed_indices)))
                    set_game_state(player.event_id, 'revealed_password_indices', revealed_indices_str)

        db.session.commit()
        emit_password_update(f'event_{player.event_id}')
        emit_leaderboard_update(f'event_{player.event_id}')
        
        return jsonify({
            'success': True,
            'completed': True,
            'points_earned': points,
            'total_score': player.score,
            f'{game_type}_score': new_score,
            'letter_revealed': revealed_letter,
            'message': f'WYZWANIE {game_name.upper()} UKOŃCZONE! Zdobyłeś {new_score} pkt i otrzymujesz {points} punktów!' + (f' Odsłonięta litera: {revealed_letter}' if revealed_letter else '')
        })
    else:
        # Gracz jeszcze nie osiągnął 20 punktów - może kontynuować
        db.session.commit()
        return jsonify({
            'success': True,
            'completed': False,
            'points_earned': 0,
            'total_score': player.score,
            f'{game_type}_score': new_score,
            'message': f'Postęp w {game_name}: {new_score}/20 pkt. Zeskanuj kod ponownie, aby kontynuować!'
        })

# --- API: PASSWORD MANAGEMENT ---
@app.route('/api/host/password/set', methods=['POST'])
@host_required
def set_password():
    """Ustaw nowe hasło (tylko przed startem gry)"""
    event_id = session['host_event_id']
    is_active = get_game_state(event_id, 'game_active', 'False') == 'True'
    
    if is_active:
        return jsonify({'error': 'Nie można zmieniać hasła podczas aktywnej gry'}), 403
    
    data = request.json
    new_password = data.get('password', '').upper().strip()
    
    if not new_password:
        return jsonify({'error': 'Hasło nie może być puste'}), 400
    
    if len(new_password) > 50:
        return jsonify({'error': 'Hasło może mieć maksymalnie 50 znaków'}), 400
    
    set_game_state(event_id, 'game_password', new_password)
    set_game_state(event_id, 'revealed_password_indices', '')
    
    emit_password_update(f'event_{event_id}')
    
    return jsonify({
        'message': 'Hasło zostało zaktualizowane',
        'password': new_password
    })

@app.route('/api/host/password/mode', methods=['POST'])
@host_required
def set_password_mode():
    """Ustaw tryb odkrywania hasła (auto/manual)"""
    event_id = session['host_event_id']
    data = request.json
    mode = data.get('mode', 'auto')

    if mode not in ['auto', 'manual']:
        return jsonify({'error': 'Nieprawidłowy tryb'}), 400

    set_game_state(event_id, 'password_reveal_mode', mode)

    return jsonify({
        'message': f'Tryb odkrywania ustawiony na: {mode}',
        'mode': mode
    })

@app.route('/api/host/password/reveal_percentage', methods=['POST'])
@host_required
def set_password_reveal_percentage():
    """Ustaw procent punktów wymagany do odkrycia litery"""
    event_id = session['host_event_id']
    data = request.json
    percentage = data.get('percentage', 50)

    try:
        percentage = int(percentage)
        if percentage < 1 or percentage > 100:
            return jsonify({'error': 'Procent musi być w zakresie 1-100'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Nieprawidłowa wartość procentu'}), 400

    set_game_state(event_id, 'password_reveal_percentage', str(percentage))

    return jsonify({
        'message': f'Procent odkrywania ustawiony na: {percentage}%',
        'percentage': percentage
    })

@app.route('/api/host/password/reveal_manual', methods=['POST'])
@host_required
def reveal_password_letters_manual():
    """Ręczne odkrycie wybranych liter hasła (po indeksach)"""
    event_id = session['host_event_id']
    data = request.json
    indices_to_reveal = data.get('indices', [])
    
    if not indices_to_reveal:
        return jsonify({'error': 'Nie wybrano żadnych liter'}), 400
    
    current_revealed = get_game_state(event_id, 'revealed_password_indices', '')
    
    revealed_set = set()
    if current_revealed:
        try:
            revealed_set = set(map(int, current_revealed.split(',')))
        except (ValueError, AttributeError):
            revealed_set = set()
    
    for idx in indices_to_reveal:
        revealed_set.add(int(idx))
    
    revealed_indices_str = ','.join(map(str, sorted(revealed_set)))
    set_game_state(event_id, 'revealed_password_indices', revealed_indices_str)
    
    emit_password_update(f'event_{event_id}')
    
    password = get_game_state(event_id, 'game_password', 'SAPEREVENT')
    revealed_chars = [password[i] for i in indices_to_reveal if i < len(password)]
    
    return jsonify({
        'message': f'Odsłonięto litery: {", ".join(revealed_chars)}',
        'revealed_indices': revealed_indices_str
    })

@app.route('/api/host/password/state', methods=['GET'])
@host_required
def get_password_state():
    """Pobierz aktualny stan hasła"""
    event_id = session['host_event_id']
    
    password = get_game_state(event_id, 'game_password', 'SAPEREVENT')
    revealed_indices_str = get_game_state(event_id, 'revealed_password_indices', '')
    mode = get_game_state(event_id, 'password_reveal_mode', 'auto')
    percentage = int(get_game_state(event_id, 'password_reveal_percentage', '50'))

    revealed_indices = []
    if revealed_indices_str:
        try:
            revealed_indices = list(map(int, revealed_indices_str.split(',')))
        except (ValueError, AttributeError):
            revealed_indices = []

    displayed_password = ""
    for i, char in enumerate(password):
        if char == ' ':
            displayed_password += '  '
        elif i in revealed_indices:
            displayed_password += char
        else:
            displayed_password += '_'

    return jsonify({
        'password': password,
        'revealed_letters': revealed_indices_str,
        'displayed_password': displayed_password,
        'mode': mode,
        'reveal_percentage': percentage
    })


# ===================================================================
# --- Gniazda (SocketIO) ---
# ===================================================================
def emit_full_state_update(room):
    """Emit full game state to all clients in the room"""
    event_id = int(room.split('_')[1])
    state = get_full_game_state(event_id)
    
    print(f"📤 Emitting full state to {room}:")
    print(f"   - game_active: {state['game_active']}")
    print(f"   - is_timer_running: {state['is_timer_running']}")
    print(f"   - time_left: {state['time_left']}")
    
    socketio.emit('game_state_update', state, room=room)

def emit_leaderboard_update(room):
    event_id = int(room.split('_')[1])
    with app.app_context():
        players = Player.query.filter_by(event_id=event_id).order_by(Player.score.desc()).all()
        socketio.emit('leaderboard_update', [{'name': p.name, 'score': p.score} for p in players], room=room)

def emit_password_update(room):
     event_id = int(room.split('_')[1])
     with app.app_context():
        socketio.emit('password_update', get_full_game_state(event_id)['password'], room=room)

_background_task_started = False
_background_task_lock = False

def update_timers():
    """Background task that sends timer updates every second"""
    print("🚀 Timer background task started")
    
    last_tick_times = {}  # Śledzi ostatni czas tick'a dla każdego eventu
    
    while True:
        try:
            with app.app_context():
                # Znajdź wszystkie aktywne eventy
                active_events = db.session.query(GameState.event_id).filter_by(
                    key='game_active', 
                    value='True'
                ).distinct().all()
                event_ids = [e[0] for e in active_events]
                
                current_time = datetime.utcnow()
                
                for event_id in event_ids:
                    is_running = get_game_state(event_id, 'is_timer_running', 'False')
                    
                    if is_running == 'True':
                        # Pobierz time_speed dla tego eventu
                        time_speed = float(get_game_state(event_id, 'time_speed', 1))
                        
                        # Oblicz ile czasu upłynęło od ostatniego tick'a
                        if event_id in last_tick_times:
                            elapsed_real_time = (current_time - last_tick_times[event_id]).total_seconds()
                        else:
                            elapsed_real_time = 1.0  # Pierwszy tick
                        
                        last_tick_times[event_id] = current_time
                        
                        # Oblicz ile czasu "game time" upłynęło (uwzględniając prędkość)
                        elapsed_game_time = elapsed_real_time * time_speed
                        
                        # Pobierz aktualny game_end_time
                        end_time_str = get_game_state(event_id, 'game_end_time')
                        if end_time_str:
                            end_time = datetime.fromisoformat(end_time_str)
                            
                            # Nowy end_time = stary end_time - (elapsed_game_time - elapsed_real_time)
                            # To powoduje, że czas "przyspiesza"
                            time_adjustment = elapsed_game_time - elapsed_real_time
                            new_end_time = end_time - timedelta(seconds=time_adjustment)
                            
                            # Zapisz nowy end_time
                            set_game_state(event_id, 'game_end_time', new_end_time.isoformat())
                            
                            # Oblicz pozostały czas
                            time_left = max(0, (new_end_time - current_time).total_seconds())
                        else:
                            time_left = 0
                        
                        state = get_full_game_state(event_id)
                        room_name = f'event_{event_id}'
                        
                        # Emit timer tick
                        socketio.emit('timer_tick', {
                            'time_left': time_left,
                            'time_elapsed': state['time_elapsed'],
                            'time_elapsed_with_pauses': state['time_elapsed_with_pauses']
                        }, room=room_name)
                        
                        if event_ids:  # Log tylko jeśli są aktywne eventy
                            print(f"⏱️  Tick -> {room_name}: {time_left:.1f}s left (speed: x{time_speed})")
                        
                        # Sprawdź czy czas minął
                        if time_left <= 0:
                            print(f"⏰ TIME'S UP for event {event_id}!")
                            set_game_state(event_id, 'game_active', 'False')
                            set_game_state(event_id, 'is_timer_running', 'False')
                            emit_full_state_update(room_name)
                            socketio.emit('game_over', {}, room=room_name)
                            # Usuń z last_tick_times
                            if event_id in last_tick_times:
                                del last_tick_times[event_id]
                    else:
                        # Jeśli timer nie jest uruchomiony, usuń z last_tick_times
                        if event_id in last_tick_times:
                            del last_tick_times[event_id]
                            
        except Exception as e:
            print(f"❌ Błąd w update_timers: {e}")
            import traceback
            traceback.print_exc()
        
        # Sleep 1 second between updates
        socketio.sleep(1)

def init_background_tasks():
    """Initialize background tasks - called once per worker"""
    global _background_task_started, _background_task_lock
    
    if _background_task_started or _background_task_lock:
        return
    
    _background_task_lock = True
    print("=" * 60)
    print("🚀 INITIALIZING BACKGROUND TASKS")
    print("=" * 60)
    
    try:
        print("📡 Starting timer background task...")
        socketio.start_background_task(target=update_timers)
        _background_task_started = True
        print("✅ Background task started successfully")
    except Exception as e:
        print(f"❌ Error starting background task: {e}")
        import traceback
        traceback.print_exc()
    finally:
        _background_task_lock = False


# Initialize background tasks when worker starts (for gunicorn/production)
@socketio.on('connect')
def handle_connect():
    """Called on first connection - ensures background task is running"""
    init_background_tasks()

@socketio.on('join')
def on_join(data):
    event_id = data.get('event_id')
    if event_id:
        room = f'event_{event_id}'
        join_room(room)
        emit('game_state_update', get_full_game_state(event_id), room=request.sid)
        emit_leaderboard_update(room)

@socketio.on('host_message_to_player')
def handle_host_message_to_player(data):
    """Host wysyła wiadomość do konkretnego gracza"""
    player_id = data.get('player_id')
    message = data.get('message')
    event_id = data.get('event_id')

    if not player_id or not message or not event_id:
        return

    # Walidacja długości wiadomości
    if len(message) > 120:
        return

    # Wyślij wiadomość do konkretnego gracza przez Socket.IO
    # Używamy room dla eventu i emitujemy do wszystkich w roomie
    # Po stronie klienta (player.html) musi sprawdzić czy wiadomość jest dla niego
    room = f'event_{event_id}'
    socketio.emit('host_message', {
        'player_id': player_id,
        'message': message
    }, room=room)

    print(f"Host wysłał wiadomość do gracza {player_id}: {message}")

# ===================================================================
# --- AR (Augmented Reality) Endpoints ---
# ===================================================================

@app.route('/api/host/ar/objects', methods=['GET'])
@host_required
def get_ar_objects():
    """Pobierz listę obiektów AR dla eventu"""
    event_id = session['host_event_id']
    objects = ARObject.query.filter_by(event_id=event_id, is_active=True).all()

    result = []
    for obj in objects:
        result.append({
            'id': obj.id,
            'object_name': obj.object_name,
            'image_data': obj.image_data,
            'game_type': obj.game_type,
            'sensitivity': obj.sensitivity if obj.sensitivity is not None else 50,
            'scan_interval': obj.scan_interval if obj.scan_interval is not None else 2,
            'created_at': obj.created_at.isoformat()
        })

    return jsonify({'objects': result})

@app.route('/api/host/ar/setup-object', methods=['POST'])
@host_required
def setup_ar_object():
    """Zapisz nowy obiekt AR z obrazem"""
    if not CV2_AVAILABLE:
        return jsonify({'error': 'OpenCV nie jest zainstalowany. AR nie jest dostępne.'}), 500

    data = request.json
    event_id = session['host_event_id']

    object_name = data.get('object_name')
    image_data = data.get('image_data')
    game_type = data.get('game_type')

    if not all([object_name, image_data, game_type]):
        return jsonify({'error': 'Brakuje wymaganych danych'}), 400

    try:
        # Dekoduj obraz z base64
        image_bytes = base64.b64decode(image_data.split(',')[1])
        image = Image.open(io.BytesIO(image_bytes))

        # Konwertuj na OpenCV format
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Wyciągnij cechy obrazu (ORB - szybkie i dobre do obiektów)
        orb = cv2.ORB_create(nfeatures=500)
        keypoints, descriptors = orb.detectAndCompute(cv_image, None)

        # Zapisz cechy jako JSON
        features = {
            'descriptors': descriptors.tolist() if descriptors is not None else [],
            'shape': cv_image.shape
        }

        # Zapisz do bazy
        ar_object = ARObject(
            event_id=event_id,
            object_name=object_name,
            image_data=image_data,
            image_features=json.dumps(features),
            game_type=game_type
        )
        db.session.add(ar_object)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Obiekt AR zapisany',
            'object_id': ar_object.id
        })

    except Exception as e:
        db.session.rollback()
        print(f"Błąd zapisu obiektu AR: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/host/ar/object/<int:object_id>', methods=['DELETE'])
@host_required
def delete_ar_object(object_id):
    """Usuń obiekt AR"""
    event_id = session['host_event_id']
    ar_object = ARObject.query.filter_by(id=object_id, event_id=event_id).first()

    if not ar_object:
        return jsonify({'error': 'Obiekt nie znaleziony'}), 404

    db.session.delete(ar_object)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Obiekt usunięty'})

@app.route('/api/host/ar/object/<int:object_id>/sensitivity', methods=['PUT'])
@host_required
def update_ar_sensitivity(object_id):
    """Zaktualizuj czułość wykrywania obiektu AR"""
    event_id = session['host_event_id']
    ar_object = ARObject.query.filter_by(id=object_id, event_id=event_id).first()

    if not ar_object:
        return jsonify({'error': 'Obiekt nie znaleziony'}), 404

    data = request.json
    sensitivity = data.get('sensitivity')

    if sensitivity is None:
        return jsonify({'error': 'Brak wartości czułości'}), 400

    # Walidacja zakresu
    try:
        sensitivity = int(sensitivity)
        if sensitivity < 5 or sensitivity > 500:
            return jsonify({'error': 'Czułość musi być w zakresie 5-500'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Nieprawidłowa wartość czułości'}), 400

    ar_object.sensitivity = sensitivity
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Czułość zaktualizowana do {sensitivity}',
        'sensitivity': sensitivity
    })

@app.route('/api/host/ar/object/<int:object_id>/interval', methods=['PUT'])
@host_required
def update_ar_interval(object_id):
    """Zaktualizuj interwał skanowania obiektu AR"""
    event_id = session['host_event_id']
    ar_object = ARObject.query.filter_by(id=object_id, event_id=event_id).first()

    if not ar_object:
        return jsonify({'error': 'Obiekt nie znaleziony'}), 404

    data = request.json
    scan_interval = data.get('scan_interval')

    if scan_interval is None:
        return jsonify({'error': 'Brak wartości interwału'}), 400

    # Walidacja zakresu
    try:
        scan_interval = int(scan_interval)
        if scan_interval < 1 or scan_interval > 10:
            return jsonify({'error': 'Interwał musi być w zakresie 1-10 sekund'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Nieprawidłowa wartość interwału'}), 400

    ar_object.scan_interval = scan_interval
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Interwał skanowania zaktualizowany do {scan_interval}s',
        'scan_interval': scan_interval
    })

@app.route('/api/player/ar/recognize', methods=['POST'])
def recognize_ar_object():
    """Rozpoznaj obiekt AR z obrazu przesłanego przez gracza"""
    if not CV2_AVAILABLE:
        return jsonify({'recognized': False, 'error': 'OpenCV nie jest zainstalowany'}), 500

    data = request.json
    image_data = data.get('image_data')
    event_id = data.get('event_id')

    if not all([image_data, event_id]):
        return jsonify({'recognized': False, 'error': 'Brakuje danych'}), 400

    try:
        # Dekoduj obraz
        image_bytes = base64.b64decode(image_data.split(',')[1])
        image = Image.open(io.BytesIO(image_bytes))
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Wyciągnij cechy
        orb = cv2.ORB_create(nfeatures=500)
        kp_test, des_test = orb.detectAndCompute(cv_image, None)

        if des_test is None:
            return jsonify({'recognized': False})

        # Pobierz obiekty AR dla eventu
        ar_objects = ARObject.query.filter_by(event_id=event_id, is_active=True).all()

        if not ar_objects:
            return jsonify({'recognized': False, 'error': 'Brak obiektów AR dla tego eventu'})

        # Porównaj z zapisanymi obiektami
        best_match = None
        best_score = 0

        for ar_obj in ar_objects:
            if not ar_obj.image_features:
                continue

            features = json.loads(ar_obj.image_features)
            descriptors_list = features.get('descriptors', [])

            if not descriptors_list:
                continue

            des_ref = np.array(descriptors_list, dtype=np.uint8)

            if len(des_ref) > 0:
                # Użyj BFMatcher do porównania
                bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                matches = bf.match(des_ref, des_test)

                # Oblicz score (więcej dopasowań = lepszy wynik)
                score = len(matches)

                if score > best_score and score > 15:  # Próg minimum 15 dopasowań
                    best_score = score
                    best_match = ar_obj

        if best_match:
            # Obiekt rozpoznany!
            response_data = {
                'recognized': True,
                'game_type': best_match.game_type,
                'object_name': best_match.object_name,
                'confidence': best_score
            }

            # Jeśli to quiz, pobierz losowe pytanie
            if best_match.game_type == 'quiz':
                # Pobierz pytanie, które gracz jeszcze nie widział
                player_id = data.get('player_id')
                if player_id:
                    # Sprawdź, które pytania gracz już widział
                    answered_ids = [ans.question_id for ans in
                                  PlayerAnswer.query.filter_by(player_id=player_id, event_id=event_id).all()]

                    # Pobierz pytanie, którego gracz jeszcze nie widział
                    question = Question.query.filter(
                        Question.event_id == event_id,
                        ~Question.id.in_(answered_ids)
                    ).order_by(db.func.random()).first()

                    if question:
                        response_data['question'] = {
                            'id': question.id,
                            'text': question.text,
                            'option_a': question.option_a,
                            'option_b': question.option_b,
                            'option_c': question.option_c
                        }

            return jsonify(response_data)

        return jsonify({'recognized': False})

    except Exception as e:
        print(f"Błąd rozpoznawania AR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'recognized': False, 'error': str(e)}), 500

# ===================================================================
# --- Questions QR Code Endpoints ---
# ===================================================================

@app.route('/questions_qr/<int:event_id>')
@host_required
def questions_qr_preview(event_id):
    """Podgląd i druk kodu QR dla Pytań"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Event nie znaleziony", 404

    # Sprawdź czy to zapasowy kod QR
    is_backup = request.args.get('backup', 'false').lower() == 'true'

    # Pobierz poziom trudności
    difficulty = request.args.get('difficulty', 'easy')
    if difficulty not in ['easy', 'medium', 'hard', 'mixed']:
        difficulty = 'easy'

    difficulty_labels = {
        'easy': 'Łatwe',
        'medium': 'Średnie',
        'hard': 'Trudne',
        'mixed': 'Mieszane'
    }

    # Generuj kod QR dla pytań
    if is_backup:
        backup_uuid = get_game_state(event_id, f'questions_backup_qr_{difficulty}_uuid', None)
        if not backup_uuid:
            return f"Zapasowy kod QR dla {difficulty_labels[difficulty].lower()} pytań nie został jeszcze wygenerowany", 404
        questions_url = url_for('questions_player_backup', event_id=event_id, backup_uuid=backup_uuid, _external=True)
        title = f"❓ Pytania - {difficulty_labels[difficulty]} - Zapasowy Kod"
    else:
        questions_url = url_for('questions_player', event_id=event_id, difficulty=difficulty, _external=True)
        title = f"❓ Pytania - {difficulty_labels[difficulty]}"

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pytania - Kod QR</title>
        <meta charset="UTF-8">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 600px;
                margin: 0 auto;
            }}
            h1 {{
                color: #0d6efd;
                margin-bottom: 10px;
            }}
            #qrcode {{
                margin: 30px auto;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .info {{
                margin: 20px;
                font-size: 18px;
                color: #333;
            }}
            button {{
                background: #0d6efd;
                color: white;
                border: none;
                padding: 12px 30px;
                font-size: 16px;
                border-radius: 5px;
                cursor: pointer;
                margin-top: 20px;
            }}
            button:hover {{
                background: #0a58ca;
            }}
            @media print {{
                body {{ background: white; }}
                button {{ display: none; }}
                .container {{ box-shadow: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{title}</h1>
            <div class="info">Zeskanuj kod QR aby uzyskać dostęp do pytań!</div>
            <div id="qrcode"></div>
            <div class="info"><strong>Event:</strong> {event.name}</div>
            <button onclick="window.print()">🖨️ Drukuj</button>
        </div>
        <script>
            // Generuj kod QR
            var qrcode = new QRCode(document.getElementById("qrcode"), {{
                text: "{questions_url}",
                width: 300,
                height: 300,
                colorDark: "#000000",
                colorLight: "#ffffff",
                correctLevel: QRCode.CorrectLevel.H
            }});
        </script>
    </body>
    </html>
    '''

@app.route('/api/host/questions/generate_backup_qr/<int:event_id>', methods=['POST'])
@host_required
def generate_questions_backup_qr(event_id):
    """Generuj zapasowy kod QR dla Pytań"""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'error': 'Event nie znaleziony'}), 404

    # Pobierz poziom trudności
    difficulty = request.args.get('difficulty', 'easy')
    if difficulty not in ['easy', 'medium', 'hard', 'mixed']:
        difficulty = 'easy'

    # Generuj nowy UUID dla zapasowego kodu QR
    backup_uuid = str(uuid.uuid4())
    set_game_state(event_id, f'questions_backup_qr_{difficulty}_uuid', backup_uuid)

    difficulty_labels = {
        'easy': 'łatwych pytań',
        'medium': 'średnich pytań',
        'hard': 'trudnych pytań',
        'mixed': 'mieszanych pytań'
    }

    return jsonify({
        'message': f'Zapasowy kod QR dla {difficulty_labels[difficulty]} został wygenerowany',
        'backup_uuid': backup_uuid
    })

@app.route('/questions_backup/<int:event_id>/<backup_uuid>')
def questions_player_backup(event_id, backup_uuid):
    """Widok Pytań dla gracza - zapasowy kod QR"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Event nie znaleziony", 404

    # Sprawdź który poziom trudności ma ten UUID
    difficulty = None
    for diff in ['easy', 'medium', 'hard', 'mixed']:
        stored_uuid = get_game_state(event_id, f'questions_backup_qr_{diff}_uuid', None)
        if stored_uuid and stored_uuid == backup_uuid:
            difficulty = diff
            break

    if not difficulty:
        return "Nieprawidłowy kod QR", 403

    # Sprawdź czy włączona
    enabled = get_game_state(event_id, 'questions_enabled', 'True') == 'True'
    if not enabled:
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Pytania</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                .message {
                    background: rgba(255,255,255,0.1);
                    padding: 30px;
                    border-radius: 15px;
                    margin: 20px auto;
                    max-width: 400px;
                }
            </style>
        </head>
        <body>
            <h1>❓ Pytania</h1>
            <div class="message">
                <h2>⏸️ Chwilowo niedostępne</h2>
                <p>Pytania są obecnie wyłączone przez organizatora.</p>
            </div>
        </body>
        </html>
        ''')

    # Przekieruj do widoku pytań z odpowiednim poziomem trudności
    return redirect(url_for('questions_player', event_id=event_id, difficulty=difficulty))

@app.route('/questions/<int:event_id>')
def questions_player(event_id):
    """Widok Pytań dla gracza z filtrowaniem po poziomie trudności"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Event nie znaleziony", 404

    # Pobierz poziom trudności
    difficulty = request.args.get('difficulty', 'easy')
    if difficulty not in ['easy', 'medium', 'hard', 'mixed']:
        difficulty = 'easy'

    # Zapisz difficulty w sesji
    session['questions_difficulty'] = difficulty

    # Sprawdź czy pytania są włączone
    enabled = get_game_state(event_id, 'questions_enabled', 'True') == 'True'
    if not enabled:
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Pytania</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                .message {
                    background: rgba(255,255,255,0.1);
                    padding: 30px;
                    border-radius: 15px;
                    margin: 20px auto;
                    max-width: 400px;
                }
            </style>
        </head>
        <body>
            <h1>❓ Pytania</h1>
            <div class="message">
                <h2>⏸️ Chwilowo niedostępne</h2>
                <p>Pytania są obecnie wyłączone przez organizatora.</p>
            </div>
        </body>
        </html>
        ''')

    # Przekieruj do rejestracji gracza z zapisanym difficulty w sesji
    return redirect(url_for('player_register', event_id=event_id))

# ===================================================================
# --- Fortune Teller AI Endpoints ---
# ===================================================================

@app.route('/fortune_qr/<int:event_id>')
@host_required
def fortune_qr_preview(event_id):
    """Podgląd i druk kodu QR dla Wróżki AI"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Event nie znaleziony", 404

    # Sprawdź czy to zapasowy kod QR
    is_backup = request.args.get('backup', 'false').lower() == 'true'

    # Generuj kod QR dla fortune
    if is_backup:
        backup_uuid = get_game_state(event_id, 'fortune_backup_qr_uuid', None)
        if not backup_uuid:
            return "Zapasowy kod QR nie został jeszcze wygenerowany", 404
        fortune_url = url_for('fortune_player_backup', event_id=event_id, backup_uuid=backup_uuid, _external=True)
        title = "🔮 Wróżka AI - Zapasowy Kod"
    else:
        fortune_url = url_for('fortune_player', event_id=event_id, _external=True)
        title = "🔮 Wróżka AI"

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Wróżka AI - Kod QR</title>
        <meta charset="UTF-8">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 600px;
                margin: 0 auto;
            }}
            h1 {{
                color: #7b2cbf;
                margin-bottom: 10px;
            }}
            #qrcode {{
                margin: 30px auto;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .info {{
                margin: 20px;
                font-size: 18px;
                color: #333;
            }}
            button {{
                background: #7b2cbf;
                color: white;
                border: none;
                padding: 12px 30px;
                font-size: 16px;
                border-radius: 5px;
                cursor: pointer;
                margin-top: 20px;
            }}
            button:hover {{
                background: #5a1f8f;
            }}
            @media print {{
                body {{ background: white; }}
                button {{ display: none; }}
                .container {{ box-shadow: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{title}</h1>
            <div class="info">Zeskanuj kod QR aby poznać swoją przyszłość!</div>
            <div id="qrcode"></div>
            <div class="info"><strong>Event:</strong> {event.name}</div>
            <button onclick="window.print()">🖨️ Drukuj</button>
        </div>
        <script>
            // Generuj kod QR
            var qrcode = new QRCode(document.getElementById("qrcode"), {{
                text: "{fortune_url}",
                width: 300,
                height: 300,
                colorDark: "#000000",
                colorLight: "#ffffff",
                correctLevel: QRCode.CorrectLevel.H
            }});
        </script>
    </body>
    </html>
    '''

@app.route('/fortune/<int:event_id>')
def fortune_player(event_id):
    """Widok Wróżki AI dla gracza"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Event nie znaleziony", 404

    # Sprawdź czy włączona
    enabled = get_game_state(event_id, 'fortune_enabled', 'False') == 'True'
    if not enabled:
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <title>Wróżka AI</title>
        </head>
        <body>
            <div class="container mt-5 text-center">
                <h2>🔮 Wróżka AI</h2>
                <div class="alert alert-warning mt-4">
                    Wróżka AI jest obecnie nieaktywna.
                </div>
            </div>
        </body>
        </html>
        ''')

    # Pobierz ustawienia
    player_words = int(get_game_state(event_id, 'fortune_player_words', '2'))

    # Pobierz playerId z localStorage lub pokaż formularz rejestracji
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <title>Wróżka AI</title>
        <style>
            body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
            .fortune-box { background: white; border-radius: 15px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); margin-top: 50px; }
            .word-input { margin-bottom: 15px; }
            .prediction { background: #f8f9fa; padding: 20px; border-radius: 10px; margin-top: 20px; white-space: pre-wrap; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="fortune-box">
                <h2 class="text-center mb-4">🔮 Wróżka AI</h2>

                <!-- Formularz rejestracji/logowania -->
                <div id="login-section" style="display: none;">
                    <p class="text-center text-muted mb-3">Witaj! Najpierw podaj swoje imię, aby móc korzystać z Wróżki AI</p>
                    <div class="mb-3">
                        <label class="form-label">Twoje imię lub nazwa drużyny:</label>
                        <input type="text" class="form-control" id="player-name-input" placeholder="Wpisz swoje imię..." maxlength="50">
                    </div>
                    <button class="btn btn-primary w-100" onclick="registerPlayer()">Dalej</button>
                </div>

                <!-- Formularz Wróżki -->
                <div id="fortune-form" style="display: none;">
                    <p class="text-center text-muted mb-3">Witaj <strong id="player-name-display"></strong>! Wpisz {{ player_words }} słów opisujących Twoje ostatnie sny</p>

                    {% for i in range(player_words) %}
                    <div class="word-input">
                        <label class="form-label">Słowo {{ i + 1 }}:</label>
                        <input type="text" class="form-control" id="word{{ i }}" placeholder="np. rower, góry, ocean..." maxlength="50">
                    </div>
                    {% endfor %}

                    <button class="btn btn-success w-100 mt-3" id="predict-btn" onclick="predictFuture()">
                        ✨ Przepowiadaj przyszłość
                    </button>

                    <div id="loading" style="display: none; text-align: center; margin-top: 20px;">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Ładowanie...</span>
                        </div>
                        <p class="mt-2">Wróżka wpatruje się w kryształową kulę...</p>
                    </div>

                    <div id="prediction" class="prediction" style="display: none;"></div>
                </div>
            </div>
        </div>

        <script>
            const eventId = {{ event_id }};
            const playerWords = {{ player_words }};
            let playerId = null;
            let playerName = '';

            // Funkcja do weryfikacji czy gracz nadal istnieje w bazie
            async function verifyPlayer() {
                try {
                    // Sprawdź czy gracz nadal istnieje przez próbę pobrania danych
                    const response = await fetch('/api/event/' + eventId + '/players');
                    const data = await response.json();

                    // Sprawdź czy nasz gracz jest na liście
                    const playerExists = data.players.some(p => p.id == playerId);

                    if (!playerExists) {
                        console.log('Player no longer exists in database - clearing localStorage');
                        // Gracz został usunięty (np. po resecie gry)
                        localStorage.removeItem(`saperPlayerId_${eventId}`);
                        localStorage.removeItem(`saperPlayerName_${eventId}`);
                        playerId = null;
                        playerName = '';

                        alert('Twoje dane wygasły po resecie gry. Zaloguj się ponownie.');
                        document.getElementById('fortune-form').style.display = 'none';
                        document.getElementById('login-section').style.display = 'block';
                        return false;
                    }

                    return true;
                } catch (error) {
                    console.error('Error verifying player:', error);
                    return true; // W razie błędu pozwól kontynuować
                }
            }

            // Sprawdź localStorage przy załadowaniu strony
            document.addEventListener('DOMContentLoaded', async () => {
                playerId = localStorage.getItem(`saperPlayerId_${eventId}`);
                playerName = localStorage.getItem(`saperPlayerName_${eventId}`);

                if (playerId && playerName) {
                    // Gracz w localStorage - sprawdź czy nadal istnieje w bazie
                    console.log('Player found in localStorage:', playerName, playerId);
                    const isValid = await verifyPlayer();

                    if (isValid) {
                        // Gracz istnieje - pokaż formularz Wróżki
                        console.log('Player verified successfully');
                        document.getElementById('player-name-display').textContent = playerName;
                        document.getElementById('fortune-form').style.display = 'block';
                    }
                    // Jeśli nie istnieje, verifyPlayer() już pokazał formularz logowania
                } else {
                    // Nowy gracz - pokaż formularz logowania
                    console.log('New player - showing login form');
                    document.getElementById('login-section').style.display = 'block';
                }
            });

            // Rejestracja gracza
            async function registerPlayer() {
                const nameInput = document.getElementById('player-name-input');
                const name = nameInput.value.trim();

                if (!name) {
                    alert('Proszę podać imię lub nazwę drużyny.');
                    return;
                }

                try {
                    const response = await fetch('/api/player/register', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name, event_id: eventId })
                    });

                    if (!response.ok) {
                        const data = await response.json();
                        alert(data.error || 'Błąd rejestracji');
                        return;
                    }

                    const data = await response.json();
                    playerId = data.id;
                    playerName = data.name;

                    // Zapisz w localStorage
                    localStorage.setItem(`saperPlayerId_${eventId}`, playerId);
                    localStorage.setItem(`saperPlayerName_${eventId}`, playerName);

                    console.log('Player registered successfully:', playerName, playerId);

                    // Ukryj formularz logowania, pokaż formularz Wróżki
                    document.getElementById('login-section').style.display = 'none';
                    document.getElementById('player-name-display').textContent = playerName;
                    document.getElementById('fortune-form').style.display = 'block';

                } catch (error) {
                    console.error('Registration error:', error);
                    alert('Błąd połączenia z serwerem: ' + error.message);
                }
            }

            async function predictFuture() {
                // Zbierz słowa
                const words = [];
                for (let i = 0; i < playerWords; i++) {
                    const word = document.getElementById(`word${i}`).value.trim();
                    if (!word) {
                        alert(`Proszę wpisać słowo ${i + 1}`);
                        return;
                    }
                    words.push(word);
                }

                // Wyślij do API
                document.getElementById('predict-btn').disabled = true;
                document.getElementById('loading').style.display = 'block';
                document.getElementById('prediction').style.display = 'none';

                try {
                    const response = await fetch('/api/fortune/predict', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            event_id: eventId,
                            player_id: playerId,
                            words: words
                        })
                    });

                    const data = await response.json();

                    if (response.ok) {
                        document.getElementById('prediction').innerHTML = `
                            <h4>✨ Twoja Przepowiednia</h4>
                            <p>${data.prediction}</p>
                            <div class="alert alert-success mt-3">
                                🎉 Otrzymałeś ${data.points} punktów!
                            </div>
                        `;
                        document.getElementById('prediction').style.display = 'block';
                    } else {
                        alert('Błąd: ' + data.error);
                    }
                } catch (error) {
                    alert('Błąd: ' + error.message);
                } finally {
                    document.getElementById('predict-btn').disabled = false;
                    document.getElementById('loading').style.display = 'none';
                }
            }
        </script>
    </body>
    </html>
    ''', player_words=player_words, event_id=event_id)

@app.route('/api/host/fortune/toggle', methods=['POST'])
@host_required
def toggle_fortune():
    """Przełącz aktywność Wróżki AI"""
    event_id = session['host_event_id']
    data = request.json
    enabled = data.get('enabled', False)

    set_game_state(event_id, 'fortune_enabled', 'True' if enabled else 'False')

    return jsonify({
        'message': f'Wróżka AI {"aktywowana" if enabled else "deaktywowana"}',
        'enabled': enabled
    })

@app.route('/api/host/questions/toggle', methods=['POST'])
@host_required
def toggle_questions():
    """Przełącz aktywność pytań"""
    event_id = session['host_event_id']
    data = request.json
    enabled = data.get('enabled', False)

    set_game_state(event_id, 'questions_enabled', 'True' if enabled else 'False')

    return jsonify({
        'message': f'Pytania {"aktywowane" if enabled else "deaktywowane"}',
        'enabled': enabled
    })

@app.route('/api/host/ai/toggle', methods=['POST'])
@host_required
def toggle_ai():
    """Przełącz aktywność pytań AI"""
    event_id = session['host_event_id']
    data = request.json
    enabled = data.get('enabled', False)

    set_game_state(event_id, 'ai_enabled', 'True' if enabled else 'False')

    return jsonify({
        'message': f'Pytania AI {"aktywowane" if enabled else "deaktywowane"}',
        'enabled': enabled
    })

@app.route('/api/host/minigames/toggle', methods=['POST'])
@host_required
def toggle_minigames():
    """Przełącz aktywność wszystkich minigier"""
    event_id = session['host_event_id']
    data = request.json
    enabled = data.get('enabled', False)

    set_game_state(event_id, 'minigames_enabled', 'True' if enabled else 'False')

    return jsonify({
        'message': f'Minigry {"aktywowane" if enabled else "deaktywowane"}',
        'enabled': enabled
    })

@app.route('/api/host/photo/toggle', methods=['POST'])
@host_required
def toggle_photo():
    """Przełącz aktywność galerii zdjęć"""
    event_id = session['host_event_id']
    data = request.json
    enabled = data.get('enabled', False)

    set_game_state(event_id, 'photo_enabled', 'True' if enabled else 'False')

    return jsonify({
        'message': f'Galeria zdjęć {"aktywowana" if enabled else "deaktywowana"}',
        'enabled': enabled
    })

@app.route('/api/host/fortune/word-count', methods=['PUT'])
@host_required
def update_fortune_word_count():
    """Aktualizuj liczbę słów AI"""
    event_id = session['host_event_id']
    data = request.json
    value = data.get('value')

    if not value or value < 10 or value > 500:
        return jsonify({'error': 'Wartość musi być w zakresie 10-500'}), 400

    set_game_state(event_id, 'fortune_word_count', str(value))
    return jsonify({'message': f'Liczba słów AI zaktualizowana do {value}'})

@app.route('/api/host/fortune/points', methods=['PUT'])
@host_required
def update_fortune_points():
    """Aktualizuj punkty za udział"""
    event_id = session['host_event_id']
    data = request.json
    value = data.get('value')

    if not value or value < 1 or value > 100:
        return jsonify({'error': 'Wartość musi być w zakresie 1-100'}), 400

    set_game_state(event_id, 'fortune_points', str(value))
    return jsonify({'message': f'Punkty za udział zaktualizowane do {value}'})

@app.route('/api/host/fortune/player-words', methods=['PUT'])
@host_required
def update_fortune_player_words():
    """Aktualizuj liczbę słów gracza"""
    event_id = session['host_event_id']
    data = request.json
    value = data.get('value')

    if not value or value < 1 or value > 10:
        return jsonify({'error': 'Wartość musi być w zakresie 1-10'}), 400

    set_game_state(event_id, 'fortune_player_words', str(value))
    return jsonify({'message': f'Liczba słów gracza zaktualizowana do {value}'})

# ===================================================================
# --- Questions Points Settings Endpoints ---
# ===================================================================

@app.route('/api/host/questions/easy-points/<int:event_id>', methods=['PUT'])
@host_required
def update_questions_easy_points(event_id):
    """Aktualizuj punkty za łatwe pytanie"""
    data = request.json
    value = data.get('value')

    if not value or value < 1 or value > 100:
        return jsonify({'error': 'Wartość musi być w zakresie 1-100'}), 400

    set_game_state(event_id, 'questions_easy_points', str(value))
    return jsonify({'message': f'Punkty za łatwe pytanie zaktualizowane do {value}'})

@app.route('/api/host/questions/medium-points/<int:event_id>', methods=['PUT'])
@host_required
def update_questions_medium_points(event_id):
    """Aktualizuj punkty za średnie pytanie"""
    data = request.json
    value = data.get('value')

    if not value or value < 1 or value > 100:
        return jsonify({'error': 'Wartość musi być w zakresie 1-100'}), 400

    set_game_state(event_id, 'questions_medium_points', str(value))
    return jsonify({'message': f'Punkty za średnie pytanie zaktualizowane do {value}'})

@app.route('/api/host/questions/hard-points/<int:event_id>', methods=['PUT'])
@host_required
def update_questions_hard_points(event_id):
    """Aktualizuj punkty za trudne pytanie"""
    data = request.json
    value = data.get('value')

    if not value or value < 1 or value > 100:
        return jsonify({'error': 'Wartość musi być w zakresie 1-100'}), 400

    set_game_state(event_id, 'questions_hard_points', str(value))
    return jsonify({'message': f'Punkty za trudne pytanie zaktualizowane do {value}'})

# ===================================================================
# --- AI Points Settings Endpoints ---
# ===================================================================

@app.route('/api/host/ai/easy-points/<int:event_id>', methods=['PUT'])
@host_required
def update_ai_easy_points(event_id):
    """Aktualizuj punkty za łatwe pytanie AI"""
    data = request.json
    value = data.get('value')

    if not value or value < 1 or value > 100:
        return jsonify({'error': 'Wartość musi być w zakresie 1-100'}), 400

    set_game_state(event_id, 'ai_easy_points', str(value))
    return jsonify({'message': f'Punkty za łatwe pytanie AI zaktualizowane do {value}'})

@app.route('/api/host/ai/medium-points/<int:event_id>', methods=['PUT'])
@host_required
def update_ai_medium_points(event_id):
    """Aktualizuj punkty za średnie pytanie AI"""
    data = request.json
    value = data.get('value')

    if not value or value < 1 or value > 100:
        return jsonify({'error': 'Wartość musi być w zakresie 1-100'}), 400

    set_game_state(event_id, 'ai_medium_points', str(value))
    return jsonify({'message': f'Punkty za średnie pytanie AI zaktualizowane do {value}'})

@app.route('/api/host/ai/hard-points/<int:event_id>', methods=['PUT'])
@host_required
def update_ai_hard_points(event_id):
    """Aktualizuj punkty za trudne pytanie AI"""
    data = request.json
    value = data.get('value')

    if not value or value < 1 or value > 100:
        return jsonify({'error': 'Wartość musi być w zakresie 1-100'}), 400

    set_game_state(event_id, 'ai_hard_points', str(value))
    return jsonify({'message': f'Punkty za trudne pytanie AI zaktualizowane do {value}'})

# ===================================================================
# --- Photo Points Settings Endpoints ---
# ===================================================================

@app.route('/api/host/photo/selfie-points/<int:event_id>', methods=['PUT'])
@host_required
def update_photo_selfie_points(event_id):
    """Aktualizuj punkty za wykonane zdjęcie selfie"""
    data = request.json
    value = data.get('value')

    if not value or value < 1 or value > 1000:
        return jsonify({'error': 'Wartość musi być w zakresie 1-1000'}), 400

    set_game_state(event_id, 'photo_selfie_points', str(value))
    return jsonify({'message': f'Punkty za zdjęcie selfie zaktualizowane do {value}'})

@app.route('/api/host/photo/like-given-points/<int:event_id>', methods=['PUT'])
@host_required
def update_photo_like_given_points(event_id):
    """Aktualizuj punkty za polubienie czyjegoś zdjęcia"""
    data = request.json
    value = data.get('value')

    if value is None or value < 0 or value > 100:
        return jsonify({'error': 'Wartość musi być w zakresie 0-100'}), 400

    set_game_state(event_id, 'photo_like_given_points', str(value))
    return jsonify({'message': f'Punkty za polubienie zdjęcia zaktualizowane do {value}'})

@app.route('/api/host/photo/like-received-points/<int:event_id>', methods=['PUT'])
@host_required
def update_photo_like_received_points(event_id):
    """Aktualizuj punkty za uzyskanie polubienia"""
    data = request.json
    value = data.get('value')

    if value is None or value < 0 or value > 100:
        return jsonify({'error': 'Wartość musi być w zakresie 0-100'}), 400

    set_game_state(event_id, 'photo_like_received_points', str(value))
    return jsonify({'message': f'Punkty za uzyskanie polubienia zaktualizowane do {value}'})

@app.route('/api/host/photo/max-likes/<int:event_id>', methods=['PUT'])
@host_required
def update_photo_max_likes(event_id):
    """Aktualizuj maksymalną liczbę zdjęć do polubienia"""
    data = request.json
    value = data.get('value')

    if not value or value < 1 or value > 1000:
        return jsonify({'error': 'Wartość musi być w zakresie 1-1000'}), 400

    set_game_state(event_id, 'photo_max_likes', str(value))
    return jsonify({'message': f'Maksymalna liczba polubionych zdjęć zaktualizowana do {value}'})

@app.route('/api/host/fortune/generate_backup_qr/<int:event_id>', methods=['POST'])
@host_required
def generate_fortune_backup_qr(event_id):
    """Generuj zapasowy kod QR dla Wróżki AI"""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'error': 'Event nie znaleziony'}), 404

    # Generuj nowy UUID dla zapasowego kodu QR
    backup_uuid = str(uuid.uuid4())
    set_game_state(event_id, 'fortune_backup_qr_uuid', backup_uuid)

    return jsonify({
        'message': 'Zapasowy kod QR został wygenerowany',
        'backup_uuid': backup_uuid
    })

@app.route('/fortune_backup/<int:event_id>/<backup_uuid>')
def fortune_player_backup(event_id, backup_uuid):
    """Widok Wróżki AI dla gracza - zapasowy kod QR"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Event nie znaleziony", 404

    # Sprawdź czy UUID się zgadza
    stored_uuid = get_game_state(event_id, 'fortune_backup_qr_uuid', None)
    if not stored_uuid or stored_uuid != backup_uuid:
        return "Nieprawidłowy kod QR", 403

    # Sprawdź czy włączona
    enabled = get_game_state(event_id, 'fortune_enabled', 'False') == 'True'
    if not enabled:
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Wróżka AI</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                .message {
                    background: rgba(255,255,255,0.1);
                    padding: 30px;
                    border-radius: 15px;
                    margin: 20px auto;
                    max-width: 400px;
                }
            </style>
        </head>
        <body>
            <h1>🔮 Wróżka AI</h1>
            <div class="message">
                <h2>⏸️ Chwilowo niedostępna</h2>
                <p>Wróżka AI jest obecnie wyłączona przez organizatora.</p>
            </div>
        </body>
        </html>
        ''')

    # Przekieruj do tego samego widoku co fortune_player
    return redirect(url_for('fortune_player', event_id=event_id))

# ===================================================================
# --- Photo QR Code Endpoints ---
# ===================================================================

@app.route('/photo_qr/<int:event_id>')
@host_required
def photo_qr_preview(event_id):
    """Podgląd i druk kodu QR dla Foto"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Event nie znaleziony", 404

    # Sprawdź czy to zapasowy kod QR
    is_backup = request.args.get('backup', 'false').lower() == 'true'

    # Generuj kod QR dla photo
    if is_backup:
        backup_uuid = get_game_state(event_id, 'photo_backup_qr_uuid', None)
        if not backup_uuid:
            return "Zapasowy kod QR nie został jeszcze wygenerowany", 404
        photo_url = url_for('photo_player_backup', event_id=event_id, backup_uuid=backup_uuid, _external=True)
        title = "📸 Foto - Zapasowy Kod"
    else:
        photo_url = url_for('photo_player', event_id=event_id, _external=True)
        title = "📸 Foto"

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Foto - Kod QR</title>
        <meta charset="UTF-8">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 600px;
                margin: 0 auto;
            }}
            h1 {{
                color: #e91e63;
                margin-bottom: 10px;
            }}
            #qrcode {{
                margin: 30px auto;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .info {{
                margin: 20px;
                font-size: 18px;
                color: #333;
            }}
            button {{
                background: #e91e63;
                color: white;
                border: none;
                padding: 12px 30px;
                font-size: 16px;
                border-radius: 5px;
                cursor: pointer;
                margin-top: 20px;
            }}
            button:hover {{
                background: #c2185b;
            }}
            @media print {{
                body {{ background: white; }}
                button {{ display: none; }}
                .container {{ box-shadow: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{title}</h1>
            <p class="info">📸 Wyzwanie Fotograficzne</p>
            <div id="qrcode"></div>
            <p style="color: #666; font-size: 14px; margin-top: 20px;">
                Zeskanuj kod QR, aby zrobić śmieszne selfie<br>
                i zdobyć 15 punktów!
            </p>
            <button onclick="window.print()">🖨️ Drukuj kod QR</button>
        </div>
        <script>
            new QRCode(document.getElementById("qrcode"), {{
                text: "{photo_url}",
                width: 300,
                height: 300
            }});
        </script>
    </body>
    </html>
    '''

@app.route('/api/host/photo/generate_backup_qr/<int:event_id>', methods=['POST'])
@host_required
def generate_photo_backup_qr(event_id):
    """Generuj zapasowy kod QR dla Foto"""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'error': 'Event nie znaleziony'}), 404

    # Generuj nowy UUID dla zapasowego kodu QR
    backup_uuid = str(uuid.uuid4())
    set_game_state(event_id, 'photo_backup_qr_uuid', backup_uuid)

    return jsonify({
        'message': 'Zapasowy kod QR został wygenerowany',
        'backup_uuid': backup_uuid
    })

@app.route('/photo_backup/<int:event_id>/<backup_uuid>')
def photo_player_backup(event_id, backup_uuid):
    """Widok Foto dla gracza - zapasowy kod QR"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Event nie znaleziony", 404

    # Sprawdź czy UUID się zgadza
    stored_uuid = get_game_state(event_id, 'photo_backup_qr_uuid', None)
    if not stored_uuid or stored_uuid != backup_uuid:
        return "Nieprawidłowy kod QR", 403

    # Sprawdź czy włączona (domyślnie True)
    enabled = get_game_state(event_id, 'photo_enabled', 'True') != 'False'
    if not enabled:
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Foto</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #e91e63, #f06292);
                    color: white;
                }
                .container {
                    text-align: center;
                    padding: 40px;
                }
                h1 { font-size: 3rem; margin-bottom: 20px; }
                p { font-size: 1.2rem; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📸 Foto</h1>
                <p>Wyzwanie fotograficzne jest obecnie wyłączone przez organizatora.</p>
            </div>
        </body>
        </html>
        ''')

    # Przekieruj do tego samego widoku co photo_player
    return redirect(url_for('photo_player', event_id=event_id))

@app.route('/photo/<int:event_id>')
def photo_player(event_id):
    """Widok Foto dla gracza - główny kod QR"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Event nie znaleziony", 404

    # Sprawdź czy włączona (domyślnie True)
    enabled = get_game_state(event_id, 'photo_enabled', 'True') != 'False'
    if not enabled:
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Foto</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #e91e63, #f06292);
                    color: white;
                }
                .container {
                    text-align: center;
                    padding: 40px;
                }
                h1 { font-size: 3rem; margin-bottom: 20px; }
                p { font-size: 1.2rem; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📸 Foto</h1>
                <p>Wyzwanie fotograficzne jest obecnie wyłączone przez organizatora.</p>
            </div>
        </body>
        </html>
        ''')

    # Renderuj dedykowany template do selfie
    return render_template('photo_selfie.html',
                         event_id=event_id,
                         event_name=event.name)

# ===================================================================
# --- Minigames QR Code Endpoints ---
# ===================================================================

@app.route('/minigames_qr/<int:event_id>')
@host_required
def minigames_qr_preview(event_id):
    """Podgląd i druk kodu QR dla Minigry"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Event nie znaleziony", 404

    # Sprawdź czy to zapasowy kod QR
    is_backup = request.args.get('backup', 'false').lower() == 'true'

    # Generuj kod QR dla minigames
    if is_backup:
        backup_uuid = get_game_state(event_id, 'minigames_backup_qr_uuid', None)
        if not backup_uuid:
            return "Zapasowy kod QR nie został jeszcze wygenerowany", 404
        minigames_url = url_for('minigames_player_backup', event_id=event_id, backup_uuid=backup_uuid, _external=True)
        title = "🎮 Minigry - Zapasowy Kod"
    else:
        minigames_url = url_for('minigames_player', event_id=event_id, _external=True)
        title = "🎮 Minigry"

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Minigry - Kod QR</title>
        <meta charset="UTF-8">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 600px;
                margin: 0 auto;
            }}
            h1 {{
                color: #28a745;
                margin-bottom: 10px;
            }}
            #qrcode {{
                margin: 30px auto;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .info {{
                margin: 20px;
                font-size: 18px;
                color: #333;
            }}
            button {{
                background: #28a745;
                color: white;
                border: none;
                padding: 12px 30px;
                font-size: 16px;
                border-radius: 5px;
                cursor: pointer;
                margin-top: 20px;
            }}
            button:hover {{
                background: #218838;
            }}
            @media print {{
                body {{ background: white; }}
                button {{ display: none; }}
                .container {{ box-shadow: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{title}</h1>
            <p class="info">🎮 Zagraj w minigrę!</p>
            <div id="qrcode"></div>
            <p style="color: #666; font-size: 14px; margin-top: 20px;">
                Zeskanuj kod QR, aby zagrać w losową minigrę<br>
                i zdobyć 20 punktów!
            </p>
            <button onclick="window.print()">🖨️ Drukuj kod QR</button>
        </div>
        <script>
            new QRCode(document.getElementById("qrcode"), {{
                text: "{minigames_url}",
                width: 300,
                height: 300
            }});
        </script>
    </body>
    </html>
    '''

@app.route('/api/host/minigames/generate_backup_qr/<int:event_id>', methods=['POST'])
@host_required
def generate_minigames_backup_qr(event_id):
    """Generuj zapasowy kod QR dla Minigry"""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'error': 'Event nie znaleziony'}), 404

    # Generuj nowy UUID dla zapasowego kodu QR
    backup_uuid = str(uuid.uuid4())
    set_game_state(event_id, 'minigames_backup_qr_uuid', backup_uuid)

    return jsonify({
        'message': 'Zapasowy kod QR został wygenerowany',
        'backup_uuid': backup_uuid
    })

@app.route('/minigames_backup/<int:event_id>/<backup_uuid>')
def minigames_player_backup(event_id, backup_uuid):
    """Widok Minigry dla gracza - zapasowy kod QR"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Event nie znaleziony", 404

    # Sprawdź czy UUID się zgadza
    stored_uuid = get_game_state(event_id, 'minigames_backup_qr_uuid', None)
    if not stored_uuid or stored_uuid != backup_uuid:
        return "Nieprawidłowy kod QR", 403

    # Sprawdź czy włączona
    enabled = get_game_state(event_id, 'minigames_enabled', 'True') == 'True'
    if not enabled:
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Minigry</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #28a745, #5cb85c);
                    color: white;
                }
                .container {
                    text-align: center;
                    padding: 40px;
                }
                h1 { font-size: 3rem; margin-bottom: 20px; }
                p { font-size: 1.2rem; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎮 Minigry</h1>
                <p>Minigry są obecnie wyłączone przez organizatora.</p>
            </div>
        </body>
        </html>
        ''')

    # Przekieruj do tego samego widoku co minigames_player
    return redirect(url_for('minigames_player', event_id=event_id))

@app.route('/minigames/<int:event_id>')
def minigames_player(event_id):
    """Widok Minigry dla gracza - główny kod QR"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Event nie znaleziony", 404

    # Sprawdź czy włączona
    enabled = get_game_state(event_id, 'minigames_enabled', 'True') == 'True'
    if not enabled:
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Minigry</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #28a745, #5cb85c);
                    color: white;
                }
                .container {
                    text-align: center;
                    padding: 40px;
                }
                h1 { font-size: 3rem; margin-bottom: 20px; }
                p { font-size: 1.2rem; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎮 Minigry</h1>
                <p>Minigry są obecnie wyłączone przez organizatora.</p>
            </div>
        </body>
        </html>
        ''')

    # Pobierz ustawienia punktów
    target_points = int(get_game_state(event_id, 'minigame_target_points', '20'))
    completion_points = int(get_game_state(event_id, 'minigame_completion_points', '10'))
    player_choice = get_game_state(event_id, 'minigame_player_choice', 'False') == 'True'

    # Przekieruj do widoku player - gracz musi być zalogowany
    game_mode_text = "wybierz grę" if player_choice else "zagraj w losową minigrę"

    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Minigry - Wyzwanie!</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #28a745, #5cb85c);
                color: white;
            }
            .container {
                text-align: center;
                padding: 40px;
                max-width: 500px;
            }
            h1 { font-size: 3rem; margin-bottom: 20px; }
            p { font-size: 1.2rem; margin-bottom: 30px; }
            .btn {
                display: inline-block;
                padding: 15px 40px;
                font-size: 1.2rem;
                font-weight: bold;
                color: #28a745;
                background: white;
                border: none;
                border-radius: 30px;
                text-decoration: none;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0,0,0,0.2);
                transition: transform 0.2s;
            }
            .btn:hover {
                transform: scale(1.05);
            }
            .info-box {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎮 Minigry!</h1>
            <div class="info-box">
                <p style="margin: 0;">{{ game_mode_text|title }} i zdobądź {{ target_points }} punktów!</p>
                <p style="margin: 10px 0 0 0; font-size: 1rem;">Nagroda: {{ completion_points }} punktów</p>
            </div>
            <p style="font-size: 1rem;">
                Aby zagrać, musisz być zarejestrowany w grze.
            </p>
            <a href="{{ url_for('player_register', event_id=event_id, qr_code='minigames_' + event_id|string) }}" class="btn">
                🎮 Rozpocznij Grę
            </a>
        </div>
    </body>
    </html>
    ''', event_id=event_id, target_points=target_points, completion_points=completion_points, game_mode_text=game_mode_text)

# ===================================================================
# --- AI QR Code Endpoints ---
# ===================================================================

@app.route('/ai_qr/<int:event_id>')
@host_required
def ai_qr_preview(event_id):
    """Podgląd i druk kodu QR dla AI"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Event nie znaleziony", 404

    # Sprawdź czy to zapasowy kod QR
    is_backup = request.args.get('backup', 'false').lower() == 'true'

    # Pobierz poziom trudności
    difficulty = request.args.get('difficulty', 'easy')
    if difficulty not in ['easy', 'medium', 'hard', 'mixed']:
        difficulty = 'easy'

    difficulty_labels = {
        'easy': 'Łatwe',
        'medium': 'Średnie',
        'hard': 'Trudne',
        'mixed': 'Mieszane'
    }

    # Generuj kod QR dla AI
    if is_backup:
        backup_uuid = get_game_state(event_id, f'ai_backup_qr_{difficulty}_uuid', None)
        if not backup_uuid:
            return f"Zapasowy kod QR dla {difficulty_labels[difficulty].lower()} pytań AI nie został jeszcze wygenerowany", 404
        ai_url = url_for('ai_player_backup', event_id=event_id, backup_uuid=backup_uuid, _external=True)
        title = f"🤖 AI - {difficulty_labels[difficulty]} - Zapasowy Kod"
    else:
        ai_url = url_for('ai_player', event_id=event_id, difficulty=difficulty, _external=True)
        title = f"🤖 AI - {difficulty_labels[difficulty]}"

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI - Kod QR</title>
        <meta charset="UTF-8">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 600px;
                margin: 0 auto;
            }}
            h1 {{
                color: #6c757d;
                margin-bottom: 10px;
            }}
            #qrcode {{
                margin: 30px auto;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .info {{
                margin: 20px;
                font-size: 18px;
                color: #333;
            }}
            button {{
                background: #6c757d;
                color: white;
                border: none;
                padding: 12px 30px;
                font-size: 16px;
                border-radius: 5px;
                cursor: pointer;
                margin-top: 20px;
            }}
            button:hover {{
                background: #5a6268;
            }}
            @media print {{
                body {{ background: white; }}
                button {{ display: none; }}
                .container {{ box-shadow: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{title}</h1>
            <p class="info">🤖 Pytania AI</p>
            <div id="qrcode"></div>
            <p style="color: #666; font-size: 14px; margin-top: 20px;">
                Zeskanuj kod QR, aby odpowiedzieć na pytania AI<br>
                i zdobyć 5 punktów za poprawną odpowiedź!
            </p>
            <button onclick="window.print()">🖨️ Drukuj kod QR</button>
        </div>
        <script>
            new QRCode(document.getElementById("qrcode"), {{
                text: "{ai_url}",
                width: 300,
                height: 300
            }});
        </script>
    </body>
    </html>
    '''

@app.route('/api/host/ai/generate_backup_qr/<int:event_id>', methods=['POST'])
@host_required
def generate_ai_backup_qr(event_id):
    """Generuj zapasowy kod QR dla AI"""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'error': 'Event nie znaleziony'}), 404

    # Pobierz poziom trudności
    difficulty = request.args.get('difficulty', 'easy')
    if difficulty not in ['easy', 'medium', 'hard', 'mixed']:
        difficulty = 'easy'

    # Generuj nowy UUID dla zapasowego kodu QR
    backup_uuid = str(uuid.uuid4())
    set_game_state(event_id, f'ai_backup_qr_{difficulty}_uuid', backup_uuid)

    difficulty_labels = {
        'easy': 'łatwych pytań AI',
        'medium': 'średnich pytań AI',
        'hard': 'trudnych pytań AI',
        'mixed': 'mieszanych pytań AI'
    }

    return jsonify({
        'message': f'Zapasowy kod QR dla {difficulty_labels[difficulty]} został wygenerowany',
        'backup_uuid': backup_uuid
    })

@app.route('/ai_backup/<int:event_id>/<backup_uuid>')
def ai_player_backup(event_id, backup_uuid):
    """Widok AI dla gracza - zapasowy kod QR"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Event nie znaleziony", 404

    # Sprawdź który poziom trudności ma ten UUID
    difficulty = None
    for diff in ['easy', 'medium', 'hard', 'mixed']:
        stored_uuid = get_game_state(event_id, f'ai_backup_qr_{diff}_uuid', None)
        if stored_uuid and stored_uuid == backup_uuid:
            difficulty = diff
            break

    if not difficulty:
        return "Nieprawidłowy kod QR", 403

    # Sprawdź czy włączona
    enabled = get_game_state(event_id, 'ai_enabled', 'True') == 'True'
    if not enabled:
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #6c757d, #adb5bd);
                    color: white;
                }
                .container {
                    text-align: center;
                    padding: 40px;
                }
                h1 { font-size: 3rem; margin-bottom: 20px; }
                p { font-size: 1.2rem; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 AI</h1>
                <p>Pytania AI są obecnie wyłączone przez organizatora.</p>
            </div>
        </body>
        </html>
        ''')

    # Przekieruj do widoku AI z odpowiednim poziomem trudności
    return redirect(url_for('ai_player', event_id=event_id, difficulty=difficulty))

@app.route('/ai/<int:event_id>')
def ai_player(event_id):
    """Widok AI dla gracza - główny kod QR"""
    event = db.session.get(Event, event_id)
    if not event:
        return "Event nie znaleziony", 404

    # Pobierz poziom trudności
    difficulty = request.args.get('difficulty', 'easy')
    if difficulty not in ['easy', 'medium', 'hard', 'mixed']:
        difficulty = 'easy'

    # Zapisz difficulty w sesji
    session['ai_difficulty'] = difficulty

    # Sprawdź czy włączona
    enabled = get_game_state(event_id, 'ai_enabled', 'True') == 'True'
    if not enabled:
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #6c757d, #adb5bd);
                    color: white;
                }
                .container {
                    text-align: center;
                    padding: 40px;
                }
                h1 { font-size: 3rem; margin-bottom: 20px; }
                p { font-size: 1.2rem; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 AI</h1>
                <p>Pytania AI są obecnie wyłączone przez organizatora.</p>
            </div>
        </body>
        </html>
        ''')

    # Przekieruj do widoku player - gracz musi być zalogowany
    # Kod QR dla AI uruchomi quiz z pytaniami z kategorii AI
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI - Quiz!</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #6c757d, #adb5bd);
                color: white;
            }
            .container {
                text-align: center;
                padding: 40px;
                max-width: 500px;
            }
            h1 { font-size: 3rem; margin-bottom: 20px; }
            p { font-size: 1.2rem; margin-bottom: 30px; }
            .btn {
                display: inline-block;
                padding: 15px 40px;
                font-size: 1.2rem;
                font-weight: bold;
                color: #6c757d;
                background: white;
                border: none;
                border-radius: 30px;
                text-decoration: none;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0,0,0,0.2);
                transition: transform 0.2s;
            }
            .btn:hover {
                transform: scale(1.05);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Quiz AI!</h1>
            <p>Odpowiedz na pytania z wybranej kategorii i zdobądź 5 punktów!</p>
            <p style="font-size: 1rem;">
                Aby zagrać, musisz być zarejestrowany w grze.
            </p>
            <a href="{{ url_for('player_register', event_id=event_id, qr_code='ai_' + event_id|string) }}" class="btn">
                🤖 Rozpocznij Quiz
            </a>
        </div>
    </body>
    </html>
    ''', event_id=event_id)

@app.route('/api/fortune/predict', methods=['POST'])
def fortune_predict():
    """Generuj przepowiednię AI"""
    data = request.json
    event_id = data.get('event_id')
    player_id = data.get('player_id')
    words = data.get('words', [])

    if not event_id or not player_id or not words:
        return jsonify({'error': 'Brak wymaganych danych'}), 400

    player = db.session.get(Player, player_id)
    if not player or player.event_id != event_id:
        return jsonify({'error': 'Gracz nie znaleziony'}), 404

    # Pobierz ustawienia
    word_count = int(get_game_state(event_id, 'fortune_word_count', '300'))
    points = int(get_game_state(event_id, 'fortune_points', '5'))

    # Sprawdź czy gracz już użył Wróżki
    already_used_key = f'fortune_used_{player_id}'
    if get_game_state(event_id, already_used_key, 'False') == 'True':
        return jsonify({'error': 'Już skorzystałeś z Wróżki AI'}), 403

    # Użyj Claude API (tak samo jak w generowaniu pytań)
    if not ANTHROPIC_AVAILABLE:
        return jsonify({'error': 'AI nie jest dostępne. Skontaktuj się z organizatorem.'}), 500

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return jsonify({'error': 'Brak klucza API. Skontaktuj się z organizatorem.'}), 500

    # Przygotuj prompt
    words_str = ', '.join(words)
    prompt = f'''Jesteś wróżką na imprezie firmowej. Gracz opisał swoje sny używając słów: {words_str}

Napisz zabawną, kreatywną i pozytywną przepowiednię przyszłości dla tego gracza (około {word_count} słów).
Przepowiednia powinna:
- Nawiązywać do podanych słów w ciekawy sposób
- Być zabawna ale nie obraźliwa
- Być pozytywna i motywująca
- Zawierać konkretne "przewidywania"
- Być napisana w stylu wróżki/jasnowidza

Przykład dla słów "rower, góry":
"Piękny Sen! Moim zdaniem wkrótce wejdziesz w sporty ekstremalne i cały świat zobaczy jak zjeżdżasz na rowerze z Rysów i to z wierzchołka po stronie polskiej. Prosto do Czarnego Stawu!"

Napisz TYLKO przepowiednię, bez żadnych dodatkowych komentarzy czy wyjaśnień.'''

    try:
        print(f"🔮 Generating fortune prediction for player {player_id} with words: {words_str}")

        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=word_count * 3,
            temperature=0.9,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        prediction = message.content[0].text.strip()

        print(f"✅ Successfully generated fortune prediction (length: {len(prediction)} chars)")

        # Dodaj punkty
        player.score += points

        # Oznacz że gracz użył Wróżki
        set_game_state(event_id, already_used_key, 'True')

        db.session.commit()

        # Emit leaderboard update
        room = f'event_{event_id}'
        emit_leaderboard_update(room)

        return jsonify({
            'prediction': prediction,
            'points': points
        })

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error generating fortune prediction: {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Błąd generowania przepowiedni. Spróbuj ponownie.'}), 500

@app.route('/api/event/<int:event_id>/players', methods=['GET'])
def get_event_players(event_id):
    """Pobierz listę graczy dla eventu"""
    players = Player.query.filter_by(event_id=event_id).order_by(Player.name).all()
    return jsonify({
        'players': [{'id': p.id, 'name': p.name, 'score': p.score} for p in players]
    })

# ========================================
# LIVE MODE API ENDPOINTS
# ========================================

@app.route('/api/host/live/session', methods=['GET', 'POST'])
@host_required
def live_session():
    """Pobierz lub utwórz sesję Live Mode"""
    event_id = session['host_event_id']

    if request.method == 'GET':
        live_session = LiveSession.query.filter_by(event_id=event_id).first()
        if not live_session:
            # Utwórz domyślną sesję jeśli nie istnieje
            import secrets
            qr_code = secrets.token_urlsafe(16)[:12]
            live_session = LiveSession(
                event_id=event_id,
                is_enabled=True,
                button_count=3,
                qr_code=qr_code
            )
            db.session.add(live_session)
            db.session.commit()

        return jsonify({
            'id': live_session.id,
            'is_enabled': live_session.is_enabled,
            'button_count': live_session.button_count,
            'qr_code': live_session.qr_code
        })

    elif request.method == 'POST':
        data = request.json
        live_session = LiveSession.query.filter_by(event_id=event_id).first()

        if live_session:
            live_session.is_enabled = data.get('is_enabled', live_session.is_enabled)
            live_session.button_count = data.get('button_count', live_session.button_count)
        else:
            import secrets
            qr_code = secrets.token_urlsafe(16)[:12]
            live_session = LiveSession(
                event_id=event_id,
                is_enabled=data.get('is_enabled', True),
                button_count=data.get('button_count', 3),
                qr_code=qr_code
            )
            db.session.add(live_session)

        db.session.commit()
        return jsonify({'message': 'Sesja Live zaktualizowana', 'session_id': live_session.id})

@app.route('/api/host/live/questions', methods=['GET'])
@host_required
def get_live_questions():
    """Pobierz wszystkie pytania Live Mode"""
    event_id = session['host_event_id']
    live_session = LiveSession.query.filter_by(event_id=event_id).first()

    if not live_session:
        return jsonify({'questions': []})

    questions = LiveQuestion.query.filter_by(
        event_id=event_id,
        session_id=live_session.id
    ).order_by(LiveQuestion.created_at.desc()).all()

    result = []
    for q in questions:
        # Policz odpowiedzi
        total_answers = LivePlayerAnswer.query.filter_by(question_id=q.id).count()
        correct_answers = LivePlayerAnswer.query.filter_by(question_id=q.id, is_correct=True).count() if q.is_revealed else 0

        result.append({
            'id': q.id,
            'question_text': q.question_text,
            'option_a': q.option_a,
            'option_b': q.option_b,
            'option_c': q.option_c,
            'option_d': q.option_d,
            'correct_answer': q.correct_answer if q.is_revealed else None,
            'is_active': q.is_active,
            'is_revealed': q.is_revealed,
            'time_limit': q.time_limit,
            'started_at': q.started_at.isoformat() if q.started_at else None,
            'total_answers': total_answers,
            'correct_answers': correct_answers
        })

    return jsonify({'questions': result})

@app.route('/api/host/live/question', methods=['POST'])
@host_required
def create_live_question():
    """Utwórz nowe pytanie Live Mode"""
    event_id = session['host_event_id']
    data = request.json

    live_session = LiveSession.query.filter_by(event_id=event_id).first()
    if not live_session:
        return jsonify({'error': 'Brak aktywnej sesji Live'}), 400

    # Dezaktywuj wszystkie poprzednie pytania
    LiveQuestion.query.filter_by(
        event_id=event_id,
        session_id=live_session.id,
        is_active=True
    ).update({'is_active': False})

    new_question = LiveQuestion(
        event_id=event_id,
        session_id=live_session.id,
        question_text=data.get('question_text', ''),
        option_a=data.get('option_a', ''),
        option_b=data.get('option_b', ''),
        option_c=data.get('option_c', ''),
        option_d=data.get('option_d', ''),
        time_limit=data.get('time_limit', 30),
        is_active=False
    )

    db.session.add(new_question)
    db.session.commit()

    return jsonify({
        'message': 'Pytanie utworzone',
        'question_id': new_question.id
    })

@app.route('/api/host/live/question/<int:question_id>/start', methods=['POST'])
@host_required
def start_live_question(question_id):
    """Uruchom pytanie Live Mode"""
    event_id = session['host_event_id']
    question = LiveQuestion.query.filter_by(id=question_id, event_id=event_id).first()

    if not question:
        return jsonify({'error': 'Nie znaleziono pytania'}), 404

    # Dezaktywuj wszystkie inne pytania
    LiveQuestion.query.filter_by(
        event_id=event_id,
        is_active=True
    ).update({'is_active': False})

    # Aktywuj to pytanie
    question.is_active = True
    question.started_at = datetime.utcnow()
    question.is_revealed = False
    db.session.commit()

    # Wyślij powiadomienie przez WebSocket
    socketio.emit('live_question_started', {
        'question_id': question.id,
        'question_text': question.question_text,
        'option_a': question.option_a,
        'option_b': question.option_b,
        'option_c': question.option_c,
        'option_d': question.option_d,
        'time_limit': question.time_limit
    }, room=f'event_{event_id}')

    return jsonify({'message': 'Pytanie uruchomione'})

@app.route('/api/host/live/question/<int:question_id>/reveal', methods=['POST'])
@host_required
def reveal_live_answer(question_id):
    """Ujawnij poprawną odpowiedź"""
    event_id = session['host_event_id']
    data = request.json
    question = LiveQuestion.query.filter_by(id=question_id, event_id=event_id).first()

    if not question:
        return jsonify({'error': 'Nie znaleziono pytania'}), 404

    correct_answer = data.get('correct_answer', '').upper()
    if correct_answer not in ['A', 'B', 'C', 'D']:
        return jsonify({'error': 'Nieprawidłowa odpowiedź'}), 400

    question.correct_answer = correct_answer
    question.is_revealed = True
    question.revealed_at = datetime.utcnow()
    question.is_active = False

    # Zaktualizuj odpowiedzi graczy i przyznaj punkty
    answers = LivePlayerAnswer.query.filter_by(question_id=question_id).all()
    for answer in answers:
        answer.is_correct = (answer.answer == correct_answer)
        if answer.is_correct:
            answer.points_awarded = 10  # Można to skonfigurować
            # Dodaj punkty do głównego score gracza
            player = Player.query.get(answer.player_id)
            if player:
                player.score += answer.points_awarded

    db.session.commit()

    # Wyślij powiadomienie przez WebSocket
    socketio.emit('live_answer_revealed', {
        'question_id': question.id,
        'correct_answer': correct_answer
    }, room=f'event_{event_id}')

    return jsonify({'message': 'Odpowiedź ujawniona', 'correct_answer': correct_answer})

@app.route('/api/host/live/question/<int:question_id>', methods=['PUT', 'DELETE'])
@host_required
def update_or_delete_live_question(question_id):
    """Edytuj lub usuń pytanie Live Mode"""
    event_id = session['host_event_id']
    question = LiveQuestion.query.filter_by(id=question_id, event_id=event_id).first()

    if not question:
        return jsonify({'error': 'Nie znaleziono pytania'}), 404

    if request.method == 'PUT':
        data = request.json
        question.question_text = data.get('question_text', question.question_text)
        question.option_a = data.get('option_a', question.option_a)
        question.option_b = data.get('option_b', question.option_b)
        question.option_c = data.get('option_c', question.option_c)
        question.option_d = data.get('option_d', question.option_d)
        question.time_limit = data.get('time_limit', question.time_limit)
        db.session.commit()
        return jsonify({'message': 'Pytanie zaktualizowane'})

    elif request.method == 'DELETE':
        db.session.delete(question)
        db.session.commit()
        return jsonify({'message': 'Pytanie usunięte'})

@app.route('/api/host/live/answers/<int:question_id>', methods=['GET'])
@host_required
def get_live_answers(question_id):
    """Pobierz odpowiedzi graczy dla pytania"""
    event_id = session['host_event_id']
    question = LiveQuestion.query.filter_by(id=question_id, event_id=event_id).first()

    if not question:
        return jsonify({'error': 'Nie znaleziono pytania'}), 404

    answers = db.session.query(
        LivePlayerAnswer, Player
    ).join(
        Player, LivePlayerAnswer.player_id == Player.id
    ).filter(
        LivePlayerAnswer.question_id == question_id
    ).all()

    result = []
    for answer, player in answers:
        result.append({
            'player_name': player.name,
            'answer': answer.answer,
            'is_correct': answer.is_correct,
            'points_awarded': answer.points_awarded,
            'answered_at': answer.answered_at.isoformat()
        })

    return jsonify({'answers': result})

@app.route('/live/<int:event_id>/<qr_code>')
def live_player_view(event_id, qr_code):
    """Widok gracza dla Live Mode"""
    # Sprawdź czy sesja live istnieje
    live_session = LiveSession.query.filter_by(event_id=event_id, qr_code=qr_code).first()

    if not live_session or not live_session.is_enabled:
        return "Tryb Live nie jest aktywny", 404

    # Sprawdź czy gracz jest zalogowany
    player_id = session.get('player_id')
    if not player_id:
        # Przekieruj do rejestracji lub zaloguj automatycznie
        return render_template('live_player.html',
                             event_id=event_id,
                             qr_code=qr_code,
                             button_count=live_session.button_count,
                             player_id=None)

    player = Player.query.filter_by(id=player_id, event_id=event_id).first()
    if not player:
        return "Gracz nie znaleziony", 404

    return render_template('live_player.html',
                         event_id=event_id,
                         qr_code=qr_code,
                         button_count=live_session.button_count,
                         player=player)

@app.route('/api/player/live/answer', methods=['POST'])
def submit_live_answer():
    """Gracz wysyła odpowiedź w trybie Live"""
    data = request.json
    player_id = session.get('player_id')

    if not player_id:
        # Spróbuj utworzyć gracza anonimowego
        event_id = data.get('event_id')
        qr_code = data.get('qr_code')

        if not event_id or not qr_code:
            return jsonify({'error': 'Brak danych gracza'}), 400

        # Utwórz gracza tymczasowego
        import secrets
        temp_name = f"Gracz_{secrets.token_hex(4)}"
        player = Player(name=temp_name, event_id=event_id)
        db.session.add(player)
        db.session.commit()
        player_id = player.id
        session['player_id'] = player_id

    question_id = data.get('question_id')
    answer = data.get('answer', '').upper()

    if not question_id or answer not in ['A', 'B', 'C', 'D']:
        return jsonify({'error': 'Nieprawidłowe dane'}), 400

    # Sprawdź czy pytanie jest aktywne
    question = LiveQuestion.query.get(question_id)
    if not question or not question.is_active:
        return jsonify({'error': 'Pytanie nie jest aktywne'}), 400

    # Sprawdź czy gracz już odpowiedział
    existing_answer = LivePlayerAnswer.query.filter_by(
        player_id=player_id,
        question_id=question_id
    ).first()

    if existing_answer:
        return jsonify({'error': 'Już udzielono odpowiedzi'}), 400

    # Zapisz odpowiedź
    player_answer = LivePlayerAnswer(
        player_id=player_id,
        question_id=question_id,
        event_id=question.event_id,
        answer=answer
    )
    db.session.add(player_answer)
    db.session.commit()

    return jsonify({'message': 'Odpowiedź zapisana', 'answer': answer})

@app.route('/api/player/live/status/<int:event_id>/<qr_code>', methods=['GET'])
def get_live_status(event_id, qr_code):
    """Pobierz aktualny status pytania Live dla gracza"""
    live_session = LiveSession.query.filter_by(event_id=event_id, qr_code=qr_code).first()

    if not live_session or not live_session.is_enabled:
        return jsonify({'active': False})

    # Znajdź aktywne pytanie
    active_question = LiveQuestion.query.filter_by(
        event_id=event_id,
        session_id=live_session.id,
        is_active=True
    ).first()

    if not active_question:
        return jsonify({'active': False})

    player_id = session.get('player_id')
    has_answered = False

    if player_id:
        existing_answer = LivePlayerAnswer.query.filter_by(
            player_id=player_id,
            question_id=active_question.id
        ).first()
        has_answered = existing_answer is not None

    # Oblicz pozostały czas
    time_remaining = None
    if active_question.started_at and active_question.time_limit:
        elapsed = (datetime.utcnow() - active_question.started_at).total_seconds()
        time_remaining = max(0, active_question.time_limit - elapsed)

    return jsonify({
        'active': True,
        'question_id': active_question.id,
        'question_text': active_question.question_text,
        'option_a': active_question.option_a,
        'option_b': active_question.option_b,
        'option_c': active_question.option_c,
        'option_d': active_question.option_d,
        'button_count': live_session.button_count,
        'has_answered': has_answered,
        'is_revealed': active_question.is_revealed,
        'correct_answer': active_question.correct_answer if active_question.is_revealed else None,
        'time_remaining': time_remaining
    })

# Uruchomienie Aplikacji
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 SAPER QR APPLICATION STARTING")
    print("=" * 60)
    
    print("📡 Starting timer background task...")
    socketio.start_background_task(target=update_timers)
    
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print(f"🌐 Server configuration:")
    print(f"   - Host: 0.0.0.0")
    print(f"   - Port: {port}")
    print(f"   - Debug: {debug_mode}")
    print("=" * 60)
    
    socketio.run(app, host='0.0.0.0', port=port, debug=debug_mode, allow_unsafe_werkzeug=True)








