from gevent import monkey
monkey.patch_all()

import os
from flask import Flask, render_template, request, jsonify, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'bardzo-tajny-klucz-super-bezpieczny')

# Database Configuration
database_url = os.environ.get('DATABASE_URL')
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace("postgres://", "postgresql://", 1)
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
    
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# SocketIO Configuration
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*", manage_session=True)

# --- Models ---
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    score = db.Column(db.Integer, default=0)
    warnings = db.Column(db.Integer, default=0)
    revealed_letters = db.Column(db.String(100), default='')
    event_id = db.Column(db.Integer, nullable=False, default=0)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)
    option_a = db.Column(db.String(100))
    option_b = db.Column(db.String(100))
    option_c = db.Column(db.String(100))
    correct_answer = db.Column(db.String(1), nullable=False)
    letter_to_reveal = db.Column(db.String(1), nullable=False)
    event_id = db.Column(db.Integer, nullable=False, default=0) # Event specific questions

class QRCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code_identifier = db.Column(db.String(50), nullable=False)
    is_red = db.Column(db.Boolean, default=False)
    claimed_by_player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    event_id = db.Column(db.Integer, nullable=False, default=0)

class PlayerScan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    qrcode_id = db.Column(db.Integer, db.ForeignKey('qr_code.id'), nullable=False)
    scan_time = db.Column(db.DateTime, nullable=False)
    event_id = db.Column(db.Integer, nullable=False, default=0)

class PlayerAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    event_id = db.Column(db.Integer, nullable=False, default=0)

class GameState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, nullable=False, default=0)
    key = db.Column(db.String(50), nullable=False)
    value = db.Column(db.String(100), nullable=False)
    __table_args__ = (db.UniqueConstraint('event_id', 'key', name='_event_key_uc'),)

class Host(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(100), default="Nowy Event")
    login = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

def host_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'host_id' not in session: return jsonify({'error': 'Unauthorized. Please log in again.'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.cli.command("init-db")
def init_db_command():
    db.create_all()
    for i in range(1, 6): # Increased to 5 events
        if not Host.query.get(i):
            host = Host(id=i, login=f'host{i}', event_name=f'Event #{i}')
            host.set_password(f'password{i}')
            db.session.add(host)
    db.session.commit()
    print("Database initialized for 5 hosts.")

# --- Routes ---
@app.route('/')
def index(): return render_template('host.html')

@app.route('/player/<int:event_id>/<qr_code>')
def player_view(event_id, qr_code): return render_template('player.html', qr_code=qr_code, event_id=event_id)

@app.route('/host')
def host(): return render_template('host.html')

@app.route('/superhost')
def superhost_view(): return render_template('superhost.html')

@app.route('/display/<int:event_id>')
def display(event_id):
    host = db.session.get(Host, event_id)
    event_name = host.event_name if host else f"Event {event_id}"
    return render_template('display.html', event_id=event_id, event_name=event_name)

@app.route('/qrcodes/<int:event_id>')
def list_qrcodes_public(event_id):
    qrcodes = QRCode.query.filter_by(event_id=event_id).all()
    # Zmieniono logikę - nie tworzymy domyślnych kodów. Jeśli ich nie ma, to host musi je wygenerować.
    return render_template('qrcodes.html', qrcodes=qrcodes, event_id=event_id)


# --- API Endpoints for Superhost ---
@app.route('/api/hosts', methods=['GET'])
def get_hosts():
    hosts = Host.query.order_by(Host.id).all()
    return jsonify([{'id': h.id, 'login': h.login, 'event_name': h.event_name} for h in hosts])

@app.route('/api/hosts/update', methods=['POST'])
def update_hosts():
    data = request.get_json()
    for host_data in data:
        host = db.session.get(Host, host_data['id'])
        if not host:
            host = Host(id=host_data['id'])
            db.session.add(host)
        
        host.login = host_data['login']
        host.event_name = host_data['event_name']
        if host_data.get('password'):
            host.set_password(host_data['password'])
    db.session.commit()
    return jsonify({'message': 'Dane hosta zaktualizowane pomyślnie!'})

@app.route('/api/event/<int:event_id>/reset', methods=['POST'])
def reset_event(event_id):
    try:
        Player.query.filter_by(event_id=event_id).delete()
        QRCode.query.filter_by(event_id=event_id).delete()
        PlayerScan.query.filter_by(event_id=event_id).delete()
        PlayerAnswer.query.filter_by(event_id=event_id).delete()
        GameState.query.filter_by(event_id=event_id).delete()
        Question.query.filter_by(event_id=event_id).delete() # Also clear questions for the event
        db.session.commit()
        
        room_name = f'event_{event_id}'
        emit_leaderboard_update(room_name)
        emit_password_update(room_name)
        socketio.emit('game_state_update', get_full_game_state(event_id), room=room_name)
        
        return jsonify({'message': f'Gra dla eventu {event_id} została zresetowana.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Błąd serwera podczas resetowania: {str(e)}'}), 500

# --- API Endpoints ---
@app.route('/api/host/login', methods=['POST'])
def host_login():
    data = request.get_json()
    login, password = data.get('login'), data.get('password')
    host = Host.query.filter_by(login=login).first()
    if host and host.check_password(password):
        session['host_id'] = host.id
        session['event_name'] = host.event_name
        return jsonify({'status': 'success', 'event_id': host.id, 'event_name': host.event_name})
    return jsonify({'status': 'error', 'message': 'Nieprawidłowy login lub hasło'}), 401

# --- Game State Helpers ---
def get_game_state(event_id, key, default=None):
    state = GameState.query.filter_by(event_id=event_id, key=key).first()
    return state.value if state else default

def set_game_state(event_id, key, value):
    state = GameState.query.filter_by(event_id=event_id, key=key).first()
    if state: state.value = str(value)
    else: db.session.add(GameState(event_id=event_id, key=key, value=str(value)))
    db.session.commit()

@app.route('/api/game/state', methods=['GET'])
@host_required
def get_game_state_api():
    event_id = session['host_id']
    return jsonify(get_full_game_state(event_id))

@app.route('/api/generate_qr_codes', methods=['POST'])
@host_required
def generate_qr_codes():
    event_id = session['host_id']
    # Prevent generating codes if the game is active
    if get_game_state(event_id, 'game_active', 'False') == 'True':
        return jsonify({'status': 'error', 'message': 'Nie można generować kodów podczas aktywnej gry.'}), 403

    data = request.json
    white_count = int(data.get('white_codes_count', 5))
    red_count = int(data.get('red_codes_count', 5))
    
    QRCode.query.filter_by(event_id=event_id).delete()
    
    for i in range(1, red_count + 1):
        db.session.add(QRCode(code_identifier=f"czerwony{i}", is_red=True, event_id=event_id))
    for i in range(1, white_count + 1):
        db.session.add(QRCode(code_identifier=f"bialy{i}", is_red=False, event_id=event_id))
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Kody QR zostały wygenerowane.'})

@app.route('/api/start_game', methods=['POST'])
@host_required
def start_game():
    event_id = session['host_id']
    data = request.json
    
    # Reset game progress, but keep QR codes and Questions
    Player.query.filter_by(event_id=event_id).delete()
    PlayerScan.query.filter_by(event_id=event_id).delete()
    PlayerAnswer.query.filter_by(event_id=event_id).delete()
    
    # Unclaim all QR codes for the event, making them reusable
    QRCode.query.filter_by(event_id=event_id).update({QRCode.claimed_by_player_id: None})
    
    set_game_state(event_id, 'game_active', 'True')
    minutes = int(data.get('minutes', 10))
    end_time = datetime.now() + timedelta(minutes=minutes)
    set_game_state(event_id, 'game_end_time', end_time.isoformat())
    set_game_state(event_id, 'is_timer_running', 'True')
    db.session.commit()
    room_name = f'event_{event_id}'
    emit_leaderboard_update(room_name)
    emit_password_update(room_name)
    socketio.emit('game_state_update', get_full_game_state(event_id), room=room_name)
    return jsonify({'status': 'success', 'message': f'Gra rozpoczęta na {minutes} minut.'})


@app.route('/api/stop_game', methods=['POST'])
@host_required
def stop_game():
    event_id = session['host_id']
    set_game_state(event_id, 'game_active', 'False')
    set_game_state(event_id, 'is_timer_running', 'False')
    room_name = f'event_{event_id}'
    socketio.emit('game_state_update', get_full_game_state(event_id), room=room_name)
    return jsonify({'status': 'success', 'message': 'Gra została zakończona.'})

@app.route('/api/game/time/pause', methods=['POST'])
@host_required
def pause_game_time():
    event_id = session['host_id']
    is_running = get_game_state(event_id, 'is_timer_running', 'False') == 'True'
    if is_running:
        end_time_str = get_game_state(event_id, 'game_end_time')
        if end_time_str:
            time_left = (datetime.fromisoformat(end_time_str) - datetime.now()).total_seconds()
            set_game_state(event_id, 'time_left_on_pause', time_left)
        set_game_state(event_id, 'is_timer_running', 'False')
        socketio.emit('timer_paused', room=f'event_{event_id}')
    else:
        time_left = float(get_game_state(event_id, 'time_left_on_pause', 0))
        new_end_time = datetime.now() + timedelta(seconds=time_left)
        set_game_state(event_id, 'game_end_time', new_end_time.isoformat())
        set_game_state(event_id, 'is_timer_running', 'True')
        socketio.emit('timer_started', room=f'event_{event_id}')
    socketio.emit('game_state_update', get_full_game_state(event_id), room=f'event_{event_id}')
    return jsonify({'status': 'success'})

# --- Player-facing API ---
@app.route('/api/register_player', methods=['POST'])
def register_player():
    data = request.get_json()
    name, event_id = data.get('name'), data.get('event_id')
    if not name or not event_id: return jsonify({'error': 'Name and event_id are required'}), 400
    if Player.query.filter_by(name=name, event_id=event_id).first():
        return jsonify({'error': 'Player name already exists for this event'}), 409
    new_player = Player(name=name, score=0, event_id=event_id)
    db.session.add(new_player)
    db.session.commit()
    emit_leaderboard_update(f'event_{event_id}')
    return jsonify({'id': new_player.id, 'name': new_player.name}), 201

@app.route('/api/scan_qr', methods=['POST'])
def scan_qr():
    data = request.get_json()
    player_id, qr_code_identifier, event_id_str = data.get('player_id'), data.get('qr_code'), data.get('event_id')
    event_id = int(event_id_str)
    
    if not all([player_id, qr_code_identifier, event_id]):
        return jsonify({'status': 'error', 'message': 'Brak wszystkich wymaganych danych.'}), 400
    
    player = db.session.get(Player, player_id)
    qr_code = QRCode.query.filter_by(code_identifier=qr_code_identifier, event_id=event_id).first()
    
    if not player or player.event_id != event_id: return jsonify({'status': 'error', 'message': 'ID gracza jest nieprawidłowe dla tego eventu.'}), 401
    if not qr_code: return jsonify({'status': 'error', 'message': 'Ten kod QR jest nieprawidłowy.'}), 404
    if get_game_state(event_id, 'game_active', 'False') != 'True': return jsonify({'status': 'error', 'message': 'Gra nie jest aktywna.'}), 403

    if qr_code.is_red:
        if qr_code.claimed_by_player_id: return jsonify({'status': 'error', 'message': 'Ten kod został już wykorzystany.'}), 403
        qr_code.claimed_by_player_id, player.score = player_id, player.score + 50
        db.session.commit()
        emit_leaderboard_update(f'event_{event_id}')
        return jsonify({'status': 'info', 'message': 'Zdobyłeś 50 punktów za czerwony kod!'})
    else: 
        last_scan = PlayerScan.query.filter_by(player_id=player_id, qrcode_id=qr_code.id).order_by(PlayerScan.scan_time.desc()).first()
        if last_scan and datetime.utcnow() < last_scan.scan_time + timedelta(minutes=5):
            wait_time = (last_scan.scan_time + timedelta(minutes=5) - datetime.utcnow()).seconds
            return jsonify({'status': 'wait', 'message': f'Odczekaj jeszcze {wait_time // 60} min {wait_time % 60} s.'}), 429
        
        db.session.add(PlayerScan(player_id=player_id, qrcode_id=qr_code.id, scan_time=datetime.utcnow(), event_id=event_id))
        db.session.commit()

        is_tetris_active = get_game_state(event_id, 'tetris_active', 'False') == 'True'
        if is_tetris_active and qr_code_identifier in ["bialy1", "bialy2", "bialy3"]:
            return jsonify({'status': 'minigame', 'game': 'tetris'})
        else:
            answered_ids = [ans.question_id for ans in PlayerAnswer.query.filter_by(player_id=player_id, event_id=event_id).all()]
            question = Question.query.filter(Question.id.notin_(answered_ids), Question.event_id==event_id).order_by(db.func.random()).first()
            if not question: return jsonify({'status': 'info', 'message': 'Odpowiedziałeś na wszystkie pytania!'})
            return jsonify({'status': 'question', 'question': {'id': question.id, 'text': question.text, 'option_a': question.option_a, 'option_b': question.option_b, 'option_c': question.option_c}})

@app.route('/api/answer', methods=['POST'])
def process_answer():
    data = request.get_json()
    player_id, question_id, answer, event_id = data.get('player_id'), data.get('question_id'), data.get('answer'), data.get('event_id')
    player, question = db.session.get(Player, player_id), db.session.get(Question, question_id)
    if not player or not question or player.event_id != event_id: return jsonify({'error': 'Invalid data'}), 404
    
    db.session.add(PlayerAnswer(player_id=player_id, question_id=question_id, event_id=event_id))
    room_name = f'event_{event_id}'
    if answer == question.correct_answer:
        player.score, player.revealed_letters = player.score + 10, player.revealed_letters + question.letter_to_reveal
        db.session.commit()
        emit_leaderboard_update(room_name)
        emit_password_update(room_name)
        return jsonify({'correct': True, 'letter': question.letter_to_reveal})
    else:
        player.score = max(0, player.score - 5)
        db.session.commit()
        emit_leaderboard_update(room_name)
        return jsonify({'correct': False})

# --- Host Management API ---
@app.route('/api/players', methods=['GET'])
@host_required
def get_players():
    event_id = session['host_id']
    players = Player.query.filter_by(event_id=event_id).order_by(Player.score.desc()).all()
    return jsonify([{'id': p.id, 'name': p.name, 'score': p.score, 'warnings': p.warnings} for p in players])

@app.route('/api/players/<int:player_id>', methods=['DELETE'])
@host_required
def delete_player(player_id):
    event_id = session['host_id']
    player = db.session.get(Player, player_id)
    if player and player.event_id == event_id:
        db.session.delete(player)
        db.session.commit()
        emit_leaderboard_update(f'event_{event_id}')
        return jsonify({'status': 'success'}), 204
    return jsonify({'status': 'error', 'message': 'Gracz nie znaleziony'}), 404

@app.route('/api/players/<int:player_id>/warn', methods=['POST'])
@host_required
def warn_player(player_id):
    event_id = session['host_id']
    player = db.session.get(Player, player_id)
    if player and player.event_id == event_id:
        player.warnings += 1
        db.session.commit()
        return jsonify({'status': 'success', 'warnings': player.warnings})
    return jsonify({'status': 'error', 'message': 'Gracz nie znaleziony'}), 404

@app.route('/api/questions', methods=['GET', 'POST'])
@host_required
def handle_questions():
    event_id = session['host_id']
    if request.method == 'POST':
        data = request.json
        q = Question(
            text=data['text'], 
            option_a=data['answers'][0], 
            option_b=data['answers'][1], 
            option_c=data['answers'][2], 
            correct_answer=data['correctAnswer'], 
            letter_to_reveal=data.get('letterToReveal', 'X'),
            event_id=event_id
        )
        db.session.add(q)
        db.session.commit()
        return jsonify({'status': 'success', 'id': q.id})
    questions = Question.query.filter_by(event_id=event_id).all()
    return jsonify([{'id': q.id, 'text': q.text, 'answers': [q.option_a, q.option_b, q.option_c], 'correctAnswer': q.correct_answer, 'letterToReveal': q.letter_to_reveal} for q in questions])

@app.route('/api/questions/<int:question_id>', methods=['DELETE'])
@host_required
def delete_question(question_id):
    event_id = session['host_id']
    question = db.session.get(Question, question_id)
    if question and question.event_id == event_id:
        db.session.delete(question)
        db.session.commit()
        return jsonify({'status': 'success'}), 204
    return jsonify({'status': 'error', 'message': 'Question not found or unauthorized'}), 404


@app.route('/api/competition/tetris', methods=['GET', 'POST'])
@host_required
def manage_tetris():
    event_id = session['host_id']
    if request.method == 'POST':
        is_active = request.json.get('active', False)
        set_game_state(event_id, 'tetris_active', is_active)
        socketio.emit('competition_state_update', {'game': 'tetris', 'active': is_active}, room=f'event_{event_id}')
    is_active = get_game_state(event_id, 'tetris_active', 'False') == 'True'
    return jsonify({'tetris_active': is_active})

# --- Helper functions & Timers ---
def get_full_game_state(event_id):
    is_active = get_game_state(event_id, 'game_active', 'False') == 'True'
    is_timer_running = get_game_state(event_id, 'is_timer_running', 'False') == 'True'
    end_time_str = get_game_state(event_id, 'game_end_time')
    time_left = 0
    if is_active and is_timer_running and end_time_str:
        time_left = max(0, (datetime.fromisoformat(end_time_str) - datetime.now()).total_seconds())
    elif is_active and not is_timer_running:
        time_left = float(get_game_state(event_id, 'time_left_on_pause', 0))
    password_value = "SAPEREVENT" 
    revealed_letters = "".join(p.revealed_letters for p in Player.query.filter_by(event_id=event_id).all())
    displayed_password = "".join([char if char in revealed_letters.upper() else "_" for char in password_value.upper()])
    return {'game_active': is_active, 'is_timer_running': is_timer_running, 'time_left': time_left, 'password': displayed_password}

def emit_leaderboard_update(room):
    if not room.startswith('event_'): return
    event_id = int(room.split('_')[1])
    with app.app_context():
        players = Player.query.filter_by(event_id=event_id).order_by(Player.score.desc()).all()
        socketio.emit('leaderboard_update', [{'name': p.name, 'score': p.score} for p in players], room=room)

def emit_password_update(room):
     if not room.startswith('event_'): return
     event_id = int(room.split('_')[1])
     with app.app_context():
        socketio.emit('password_update', get_full_game_state(event_id)['password'], room=room)

def update_timers():
    while True:
        with app.app_context():
             for host in Host.query.all():
                event_id = host.id
                if get_game_state(event_id, 'game_active', 'False') == 'True' and get_game_state(event_id, 'is_timer_running', 'False') == 'True':
                    state = get_full_game_state(event_id)
                    room_name = f'event_{event_id}'
                    socketio.emit('timer_tick', {'time_left': state['time_left']}, room=room_name)
                    if state['time_left'] <= 0:
                        set_game_state(event_id, 'game_active', 'False')
                        set_game_state(event_id, 'is_timer_running', 'False')
                        socketio.emit('game_state_update', get_full_game_state(event_id), room=room_name)
        socketio.sleep(1)

# --- SocketIO events ---
@socketio.on('join')
def on_join(data):
    event_id = data.get('event_id')
    if event_id:
        room = f'event_{event_id}'
        join_room(room)
        emit('game_state_update', get_full_game_state(event_id), room=request.sid)
        emit_leaderboard_update(room)

@socketio.on('connect')
def handle_connect(): print(f"Client connected: {request.sid}")
    
socketio.start_background_task(target=update_timers)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)

