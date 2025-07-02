from flask import Flask, render_template, request, redirect, url_for
from prometheus_flask_exporter import PrometheusMetrics
import sqlite3
import os
import logging
import json
from datetime import datetime
from .config import config

# Configuration du logging structuré
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
        
        # Ajouter des informations supplémentaires si disponibles
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

def create_app(config_name=None):
    app = Flask(__name__)
    
    # Configuration
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Configuration du logging structuré
    if not app.debug and config_name != 'testing':
        # Handler pour les logs JSON
        json_handler = logging.StreamHandler()
        json_handler.setFormatter(JSONFormatter())
        json_handler.setLevel(logging.INFO)
        
        # Configurer le logger de l'application
        app.logger.handlers.clear()  # Supprimer les handlers par défaut
        app.logger.addHandler(json_handler)
        app.logger.setLevel(logging.INFO)
        
        # Configurer le logger racine pour capturer tous les logs
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            root_logger.addHandler(json_handler)
            root_logger.setLevel(logging.INFO)
    
    # Métriques Prometheus
    metrics = PrometheusMetrics(app)
    
    def get_db_path():
        return app.config['DATABASE_PATH']
    
    def init_db():
        db_path = get_db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True) if '/' in db_path else None
        
        conn = sqlite3.connect(db_path)
        conn.execute('''CREATE TABLE IF NOT EXISTS tasks
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         task TEXT NOT NULL,
                         completed BOOLEAN DEFAULT FALSE)''')
        conn.close()
        
        app.logger.info('Base de données initialisée', extra={'action': 'db_init'})
    
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
            app.logger.error(f'Erreur lors de la consultation des tâches: {str(e)}', 
                           extra={'action': 'view_tasks_error'})
            return "Erreur lors du chargement des tâches", 500
    
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
            
            app.logger.info(f'Nouvelle tâche ajoutée: {task}', extra={
                'action': 'add_task_success',
                'task_id': task_id,
                'task_content': task,
                'ip_address': request.remote_addr
            })
            
            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(f'Erreur lors de l\'ajout de tâche: {str(e)}', extra={
                'action': 'add_task_error',
                'task_content': task
            })
            return "Erreur lors de l'ajout de la tâche", 500
    
    @app.route('/complete/<int:task_id>')
    def complete_task(task_id):
        try:
            conn = sqlite3.connect(get_db_path())
            conn.execute('UPDATE tasks SET completed = TRUE WHERE id = ?', (task_id,))
            conn.commit()
            conn.close()
            
            app.logger.info(f'Tâche complétée', extra={
                'action': 'complete_task',
                'task_id': task_id,
                'ip_address': request.remote_addr
            })
            
            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(f'Erreur lors de la completion de tâche: {str(e)}', extra={
                'action': 'complete_task_error',
                'task_id': task_id
            })
            return "Erreur lors de la completion de la tâche", 500
    
    @app.route('/delete/<int:task_id>')
    def delete_task(task_id):
        try:
            conn = sqlite3.connect(get_db_path())
            conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            conn.commit()
            conn.close()
            
            app.logger.info(f'Tâche supprimée', extra={
                'action': 'delete_task',
                'task_id': task_id,
                'ip_address': request.remote_addr
            })
            
            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(f'Erreur lors de la suppression de tâche: {str(e)}', extra={
                'action': 'delete_task_error',
                'task_id': task_id
            })
            return "Erreur lors de la suppression de la tâche", 500
    
    @app.route('/health')
    def health():
        try:
            # Test de connexion à la base de données
            conn = sqlite3.connect(get_db_path())
            conn.execute('SELECT 1').fetchone()
            conn.close()
            
            app.logger.info('Health check réussi', extra={
                'action': 'health_check_success',
                'ip_address': request.remote_addr
            })
            
            return {'status': 'healthy', 'database': 'connected'}, 200
        except Exception as e:
            app.logger.error(f'Health check échoué: {str(e)}', extra={
                'action': 'health_check_error'
            })
            return {'status': 'unhealthy', 'error': str(e)}, 500
    
    # Gestionnaire d'erreurs global
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
    
    # Log de démarrage de l'application
    app.logger.info('Application Flask démarrée', extra={
        'action': 'app_startup',
        'config': config_name
    })
    
    return app

# Point d'entrée
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Initialiser la base de données
        def init_db():
            db_path = app.config['DATABASE_PATH']
            os.makedirs(os.path.dirname(db_path), exist_ok=True) if '/' in db_path else None
            
            conn = sqlite3.connect(db_path)
            conn.execute('''CREATE TABLE IF NOT EXISTS tasks
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             task TEXT NOT NULL,
                             completed BOOLEAN DEFAULT FALSE)''')
            conn.close()
        
        init_db()
    
    app.run(host='0.0.0.0', port=5000, debug=False)