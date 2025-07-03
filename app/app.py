from flask import Flask, render_template, request, redirect, url_for
from prometheus_flask_exporter import PrometheusMetrics
import sqlite3
import os
import logging
import json
from datetime import datetime

try:
    from .config import config
except ImportError:
    from config import config

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process': record.process,
            'thread': record.thread
        }

        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'task_id'):
            log_entry['task_id'] = record.task_id
        if hasattr(record, 'action'):
            log_entry['action'] = record.action

        return json.dumps(log_entry)

    def formatException(self, exc_info):
        result = super(JSONFormatter, self).formatException(exc_info)
        json_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "ERROR",
            "module": "app",
            "message": f"{result}",
            "exception": True
        }
        return json.dumps(json_result)


def configure_logging(app, config_name):
    """Configure le logging JSON pour l'application"""
    if not app.debug and config_name != 'testing':
        json_handler = logging.StreamHandler()
        json_handler.setFormatter(JSONFormatter())
        json_handler.setLevel(logging.INFO)

        app.logger.handlers.clear()
        app.logger.addHandler(json_handler)
        app.logger.setLevel(logging.INFO)

        root_logger = logging.getLogger()
        if not root_logger.handlers:
            root_logger.addHandler(json_handler)
            root_logger.setLevel(logging.INFO)


def setup_database(app):
    """Configure les fonctions de base de données"""
    def get_db_path():
        return app.config['DATABASE_PATH']

    def init_db():
        db_path = get_db_path()
        if '/' in db_path:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

        conn = sqlite3.connect(db_path)
        conn.execute('''CREATE TABLE IF NOT EXISTS tasks
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         task TEXT NOT NULL,
                         completed BOOLEAN DEFAULT FALSE)''')
        conn.close()

        app.logger.info('Base de données initialisée',
                        extra={'action': 'db_init'})

    return get_db_path, init_db


def create_index_route(app, get_db_path):
    """Crée la route index"""
    @app.route('/')
    def index():
        try:
            conn = sqlite3.connect(get_db_path())
            tasks = conn.execute('SELECT * FROM tasks').fetchall()
            conn.close()

            app.logger.info('Page d\'accueil consultée', extra={
                'action': 'view_tasks',
                'task_count': len(tasks)
            })

            return render_template('index.html', tasks=tasks)
        except Exception as e:
            app.logger.error(
                'Erreur lors de la consultation des tâches: {}'.format(str(e)),
                extra={'action': 'view_tasks_error'})
            return "Erreur lors du chargement des tâches", 500


def create_add_route(app, get_db_path):
    """Crée la route add"""
    @app.route('/add', methods=['POST'])
    def add_task():
        task = request.form.get('task', '').strip()

        if not task:
            app.logger.warning('Tentative d\'ajout de tâche vide', extra={
                'action': 'add_task_empty',
                'ip_address': request.remote_addr
            })
            return redirect(url_for('index'))

        try:
            conn = sqlite3.connect(get_db_path())
            cursor = conn.execute('INSERT INTO tasks (task) VALUES (?)', (task,))
            task_id = cursor.lastrowid
            conn.commit()
            conn.close()

            app.logger.info('Nouvelle tâche ajoutée: {}'.format(task), extra={
                'action': 'add_task_success',
                'task_id': task_id,
                'task_content': task,
                'ip_address': request.remote_addr
            })

            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(
                'Erreur lors de l\'ajout de tâche: {}'.format(str(e)),
                extra={'action': 'add_task_error', 'task_content': task})
            return "Erreur lors de l'ajout de la tâche", 500


def create_task_routes(app, get_db_path):
    """Crée les routes complete et delete"""
    @app.route('/complete/<int:task_id>')
    def complete_task(task_id):
        try:
            conn = sqlite3.connect(get_db_path())
            conn.execute('UPDATE tasks SET completed = TRUE WHERE id = ?',
                         (task_id,))
            conn.commit()
            conn.close()

            app.logger.info('Tâche complétée', extra={
                'action': 'complete_task',
                'task_id': task_id,
                'ip_address': request.remote_addr
            })

            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(
                'Erreur lors de la completion de tâche: {}'.format(str(e)),
                extra={'action': 'complete_task_error', 'task_id': task_id})
            return "Erreur lors de la completion de la tâche", 500

    @app.route('/delete/<int:task_id>')
    def delete_task(task_id):
        try:
            conn = sqlite3.connect(get_db_path())
            conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            conn.commit()
            conn.close()

            app.logger.info('Tâche supprimée', extra={
                'action': 'delete_task',
                'task_id': task_id,
                'ip_address': request.remote_addr
            })

            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(
                'Erreur lors de la suppression de tâche: {}'.format(str(e)),
                extra={'action': 'delete_task_error', 'task_id': task_id})
            return "Erreur lors de la suppression de la tâche", 500


def create_health_route(app, get_db_path):
    """Crée la route health"""
    @app.route('/health')
    def health():
        try:
            conn = sqlite3.connect(get_db_path())
            conn.execute('SELECT 1').fetchone()
            conn.close()

            app.logger.info('Health check réussi', extra={
                'action': 'health_check_success',
                'ip_address': request.remote_addr
            })

            return {'status': 'healthy', 'database': 'connected'}, 200
        except Exception as e:
            app.logger.error('Health check échoué: {}'.format(str(e)), extra={
                'action': 'health_check_error'
            })
            return {'status': 'unhealthy', 'error': str(e)}, 500


def register_routes(app, get_db_path):
    """Enregistre toutes les routes de l'application"""
    create_index_route(app, get_db_path)
    create_add_route(app, get_db_path)
    create_task_routes(app, get_db_path)
    create_health_route(app, get_db_path)


def register_error_handlers(app):
    """Enregistre les gestionnaires d'erreurs"""
    @app.errorhandler(404)
    def not_found(error):
        app.logger.warning('Page non trouvée', extra={
            'action': 'page_not_found',
            'path': request.path,
            'ip_address': request.remote_addr
        })
        return "Page non trouvée", 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error('Erreur interne du serveur', extra={
            'action': 'internal_server_error',
            'path': request.path,
            'ip_address': request.remote_addr
        })
        return "Erreur interne du serveur", 500


def create_app(config_name=None):
    """Factory pour créer l'application Flask"""
    app = Flask(__name__)

    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])

    configure_logging(app, config_name)
    PrometheusMetrics(app)

    get_db_path, init_db = setup_database(app)
    register_routes(app, get_db_path)
    register_error_handlers(app)

    app.logger.info('Application Flask démarrée', extra={
        'action': 'app_startup',
        'config': config_name
    })

    return app


app = create_app()

if __name__ == '__main__':
    with app.app_context():
        def init_db():
            db_path = app.config['DATABASE_PATH']
            if '/' in db_path:
                os.makedirs(os.path.dirname(db_path), exist_ok=True)

            conn = sqlite3.connect(db_path)
            conn.execute('''CREATE TABLE IF NOT EXISTS tasks
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             task TEXT NOT NULL,
                             completed BOOLEAN DEFAULT FALSE)''')
            conn.close()

        init_db()

    app.run(host='0.0.0.0', port=5000, debug=False)
