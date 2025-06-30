from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('tasks.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS tasks
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     task TEXT NOT NULL,
                     completed BOOLEAN DEFAULT FALSE)''')
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('tasks.db')
    tasks = conn.execute('SELECT * FROM tasks').fetchall()
    conn.close()
    return render_template('index.html', tasks=tasks)

@app.route('/add', methods=['POST'])
def add_task():
    task = request.form['task']
    conn = sqlite3.connect('tasks.db')
    conn.execute('INSERT INTO tasks (task) VALUES (?)', (task,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/complete/<int:task_id>')
def complete_task(task_id):
    conn = sqlite3.connect('tasks.db')
    conn.execute('UPDATE tasks SET completed = TRUE WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    conn = sqlite3.connect('tasks.db')
    conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)

