from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import secrets
from flask import jsonify


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Gera uma chave aleatória de 32 caracteres

def voltar():
    return render_template("index.html")

def create_table():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT UNIQUE NOT NULL
        )
    ''')
    
    cursor.execute('SELECT * FROM users WHERE username = ?', ('master',))
    master_user = cursor.fetchone()

    if not master_user:
        cursor.execute('INSERT INTO users (username, password, name) VALUES (?, ?, ?)', ('master', '152117', 'Master'))

    conn.commit()
    conn.close()


def create_notes_table():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()


def is_admin(user_id):
    return user_id in (1, 2)


@app.route('/')
def index():
    return render_template('login.html')


@app.route('/home')
def home():
    if 'user_id' not in session:
        flash('Faça o login primeiro', 'error')
        return redirect(url_for('index'))

    user_id = session['user_id']
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM users WHERE id = ?', (user_id,))
    name = cursor.fetchone()[0]
    conn.close()

    return render_template('index.html', name=name)


@app.route('/notes', methods=['GET', 'POST'])
def notes():
    if 'user_id' not in session:
        flash('Faça o login primeiro', 'error')
        return redirect(url_for('index'))

    user_id = session['user_id']
    latest_note_content = ""

    if request.method == 'POST':
        content = request.form['content']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO notes (user_id, content) VALUES (?, ?)', (user_id, content))
        conn.commit()
        conn.close()

        flash('Anotação adicionada com sucesso', 'success')

    # Após salvar a anotação, recupere o conteúdo da última anotação
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT content FROM notes WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id,))
    latest_note = cursor.fetchone()

    if latest_note:
        latest_note_content = latest_note[0]

    conn.close()

    return render_template('notes.html', latest_note_content=latest_note_content)


@app.route('/save_note', methods=['POST'])
def save_note():
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não autenticado'})

    user_id = session['user_id']
    content = request.json.get('content', '')

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO notes (user_id, content) VALUES (?, ?)', (user_id, content))
    conn.commit()
    conn.close()

    return jsonify({'success': True})


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    create_table()
    user_id = session.get('user_id', None)

    if not is_admin(user_id):
        flash('Acesso negado. Apenas administradores podem cadastrar novos usuários.', 'error')
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('Usuário já está em uso', 'error')
        else:
            cursor.execute('INSERT INTO users (username, password, name) VALUES (?, ?, ?)', (username, password, name))
            conn.commit()
            conn.close()

            flash('Cadastrado com sucesso', 'success')

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    create_table()

    user = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

    if user and user[2] == password:
        session['user_id'] = user[0]
        flash('Login feito com sucesso', 'success')
        return redirect(url_for('home'))
    else:
        flash('Usuário ou senha incorreta', 'error')

    return redirect('home')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logout feito com sucesso', 'success')
    return redirect(url_for('index'))


@app.route('/usuarios')
def usuarios():
    if 'user_id' not in session:
        flash('Faça o login primeiro', 'error')
        return redirect(url_for('index'))

    user_id = session['user_id']

    if user_id not in (1, 2):
        flash('Acesso negado. Apenas administradores podem visualizar usuários.', 'error')
        return redirect(url_for('home'))

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, name, password FROM users')
    users = cursor.fetchall()
    conn.close()

    return render_template('usuarios.html', users=users)


@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session:
        flash('Faça o login primeiro', 'error')
        return redirect(url_for('index'))

    current_user_id = session['user_id']

    if current_user_id != 1:
        flash('Acesso negado. Apenas administradores podem excluir usuários.', 'error')
        return redirect(url_for('home'))

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

    flash(f'Usuário ID {user_id} excluído com sucesso.', 'success')
    return redirect(url_for('usuarios'))


if __name__ == '__main__':
    create_table()
    create_notes_table()
    app.run(debug=True)
