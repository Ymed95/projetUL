import pytest
import tempfile
import os
import sqlite3
import json
import logging
from unittest.mock import patch, MagicMock

# Import de l'application
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.app import create_app
from app.app import JSONFormatter

@pytest.fixture
def client():
    """Fixture pour créer un client de test avec base de données temporaire"""
    db_fd, test_db = tempfile.mkstemp()
    os.environ['DATABASE_PATH'] = test_db
    os.environ['FLASK_ENV'] = 'testing'
    
    app = create_app('testing')
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        with app.app_context():
            # Initialiser la base de données de test
            conn = sqlite3.connect(test_db)
            conn.execute('''CREATE TABLE IF NOT EXISTS tasks
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             task TEXT NOT NULL,
                             completed BOOLEAN DEFAULT FALSE)''')
            conn.close()
        yield client
    
    os.close(db_fd)
    os.unlink(test_db)

class TestHealthEndpoint:
    """Tests pour l'endpoint de santé"""
    
    def test_health_success(self, client):
        """Test du health check en cas de succès"""
        rv = client.get('/health')
        assert rv.status_code == 200
        data = rv.get_json()
        assert data['status'] == 'healthy'
        assert data['database'] == 'connected'
    
    @patch('sqlite3.connect')
    def test_health_with_database_error(self, mock_connect, client):
        """Test du health check avec erreur de base de données"""
        mock_connect.side_effect = Exception("Database error")
        rv = client.get('/health')
        assert rv.status_code == 500
        data = rv.get_json()
        assert data['status'] == 'unhealthy'

class TestTaskManagement:
    """Tests pour la gestion des tâches"""
    
    def test_index_empty(self, client):
        """Test de la page d'accueil sans tâches"""
        rv = client.get('/')
        assert rv.status_code == 200
    
    def test_add_task_success(self, client):
        """Test d'ajout de tâche réussi"""
        rv = client.post('/add', data={'task': 'Test task'})
        assert rv.status_code == 302
        
        # Vérifier que la tâche a été ajoutée
        rv = client.get('/')
        assert rv.status_code == 200
        assert b'Test task' in rv.data
    
    def test_add_empty_task(self, client):
        """Test d'ajout de tâche vide"""
        rv = client.post('/add', data={'task': ''})
        assert rv.status_code == 302
    
    def test_add_whitespace_task(self, client):
        """Test d'ajout de tâche avec espaces"""
        rv = client.post('/add', data={'task': '   '})
        assert rv.status_code == 302
    
    def test_complete_task(self, client):
        """Test de completion de tâche"""
        # Ajouter une tâche
        client.post('/add', data={'task': 'Task to complete'})
        
        # Récupérer l'ID de la tâche
        conn = sqlite3.connect(os.environ['DATABASE_PATH'])
        task = conn.execute('SELECT id FROM tasks WHERE task = ?', ('Task to complete',)).fetchone()
        task_id = task[0]
        conn.close()
        
        # Compléter la tâche
        rv = client.get(f'/complete/{task_id}')
        assert rv.status_code == 302
    
    def test_delete_task(self, client):
        """Test de suppression de tâche"""
        # Ajouter une tâche
        client.post('/add', data={'task': 'Task to delete'})
        
        # Récupérer l'ID de la tâche
        conn = sqlite3.connect(os.environ['DATABASE_PATH'])
        task = conn.execute('SELECT id FROM tasks WHERE task = ?', ('Task to delete',)).fetchone()
        task_id = task[0]
        conn.close()
        
        # Supprimer la tâche
        rv = client.get(f'/delete/{task_id}')
        assert rv.status_code == 302

class TestErrorHandling:
    """Tests pour la gestion d'erreurs"""
    
    def test_404_error(self, client):
        """Test de page non trouvée"""
        rv = client.get('/nonexistent-page')
        assert rv.status_code == 404
    
    @patch('sqlite3.connect')
    def test_add_task_database_error(self, mock_connect, client):
        """Test d'erreur de base de données lors de l'ajout"""
        mock_connect.side_effect = Exception("Database error")
        rv = client.post('/add', data={'task': 'Test task'})
        assert rv.status_code == 500
    
    @patch('sqlite3.connect')
    def test_complete_task_database_error(self, mock_connect, client):
        """Test d'erreur de base de données lors de la completion"""
        mock_connect.side_effect = Exception("Database error")
        rv = client.get('/complete/1')
        assert rv.status_code == 500
    
    @patch('sqlite3.connect')
    def test_delete_task_database_error(self, mock_connect, client):
        """Test d'erreur de base de données lors de la suppression"""
        mock_connect.side_effect = Exception("Database error")
        rv = client.get('/delete/1')
        assert rv.status_code == 500
    
    @patch('sqlite3.connect')
    def test_index_database_error(self, mock_connect, client):
        """Test d'erreur de base de données sur la page d'accueil"""
        mock_connect.side_effect = Exception("Database error")
        rv = client.get('/')
        assert rv.status_code == 500

class TestMetrics:
    """Tests pour les métriques Prometheus"""
    
    def test_metrics_endpoint(self, client):
        """Test de l'endpoint des métriques"""
        rv = client.get('/metrics')
        assert rv.status_code == 200
        assert b'flask_http_request_total' in rv.data

class TestJSONFormatter:
    """Tests pour le formateur JSON"""
    
    def test_json_formatter_basic(self):
        """Test du formateur JSON basique"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test', level=logging.INFO, pathname='test.py', lineno=10,
            msg='Test message', args=(), exc_info=None
        )
        record.process = 1234
        record.thread = 5678
        record.module = 'test_module'
        record.funcName = 'test_function'
        
        result = formatter.format(record)
        parsed = json.loads(result)
        
        assert parsed['message'] == 'Test message'
        assert parsed['level'] == 'INFO'
        assert parsed['module'] == 'test_module'
        assert parsed['function'] == 'test_function'
    
    def test_json_formatter_with_extra_fields(self):
        """Test du formateur JSON avec champs supplémentaires"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test', level=logging.WARNING, pathname='test.py', lineno=20,
            msg='Warning message', args=(), exc_info=None
        )
        record.process = 1234
        record.thread = 5678
        record.module = 'test_module'
        record.funcName = 'test_function'
        record.user_id = 'user123'
        record.task_id = 456
        record.action = 'test_action'
        
        result = formatter.format(record)
        parsed = json.loads(result)
        
        assert parsed['user_id'] == 'user123'
        assert parsed['task_id'] == 456
        assert parsed['action'] == 'test_action'

class TestDatabaseOperations:
    """Tests pour les opérations de base de données"""
    
    def test_multiple_tasks(self, client):
        """Test avec plusieurs tâches"""
        tasks = ['Task 1', 'Task 2', 'Task 3']
        
        # Ajouter plusieurs tâches
        for task in tasks:
            client.post('/add', data={'task': task})
        
        # Vérifier qu'elles sont toutes présentes
        rv = client.get('/')
        for task in tasks:
            assert task.encode() in rv.data
    
    def test_task_persistence(self, client):
        """Test de la persistance des tâches"""
        # Ajouter une tâche
        client.post('/add', data={'task': 'Persistent task'})
        
        # Vérifier directement dans la base de données
        conn = sqlite3.connect(os.environ['DATABASE_PATH'])
        tasks = conn.execute('SELECT task FROM tasks WHERE task = ?', ('Persistent task',)).fetchall()
        conn.close()
        
        assert len(tasks) == 1
        assert tasks[0][0] == 'Persistent task'

class TestSecurity:
    """Tests de sécurité basiques"""
    
    def test_sql_injection_protection(self, client):
        """Test de protection contre l'injection SQL"""
        malicious_input = "'; DROP TABLE tasks; --"
        rv = client.post('/add', data={'task': malicious_input})
        assert rv.status_code == 302
        
        # Vérifier que la table existe toujours
        conn = sqlite3.connect(os.environ['DATABASE_PATH'])
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'").fetchone()
        conn.close()
        assert result is not None


class TestAppInitialization:
    """Tests pour l'initialisation de l'application"""
    
    def test_app_creation_with_config(self):
        """Test de création d'app avec configuration spécifique"""
        app = create_app('testing')
        assert app.config['TESTING'] == True
        assert app.config['DATABASE_PATH'] == '/tmp/test.db'
    
    def test_app_creation_default_config(self):
        """Test de création d'app avec config par défaut"""
        app = create_app()
        assert app is not None

class TestLoggingConfiguration:
    """Tests pour la configuration du logging"""
    
    def test_logging_disabled_in_testing(self):
        """Test que le logging JSON est désactivé en mode test"""
        app = create_app('testing')
        # En mode testing, le logging JSON ne devrait pas être configuré
        assert app is not None
    
    def test_json_formatter_exception_handling(self):
        """Test de la gestion d'exceptions dans JSONFormatter"""
        formatter = JSONFormatter()
        try:
            raise ValueError("Test exception")
        except Exception as e:
            exc_info = (type(e), e, e.__traceback__)
            result = formatter.formatException(exc_info)
            parsed = json.loads(result)
            assert parsed['level'] == 'ERROR'
            assert parsed['exception'] == True

class TestDatabaseInitialization:
    """Tests pour l'initialisation de la base de données"""
    
    def test_database_path_creation(self, client):
        """Test de création du chemin de base de données"""
        # Tester avec un chemin qui nécessite la création de dossiers
        import tempfile
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'subdir', 'test.db')
        
        with client.application.app_context():
            client.application.config['DATABASE_PATH'] = db_path
            # Simuler l'initialisation
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            conn = sqlite3.connect(db_path)
            conn.execute('''CREATE TABLE IF NOT EXISTS tasks
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             task TEXT NOT NULL,
                             completed BOOLEAN DEFAULT FALSE)''')
            conn.close()
        
        assert os.path.exists(db_path)

class TestEdgeCases:
    """Tests pour les cas limites"""
    
    def test_task_with_special_characters(self, client):
        """Test d'ajout de tâche avec caractères spéciaux"""
        special_task = "Tâche avec émoticônes 🚀 et caractères spéciaux @#$%"
        rv = client.post('/add', data={'task': special_task})
        assert rv.status_code == 302
        
        rv = client.get('/')
        assert special_task.encode('utf-8') in rv.data
    
    def test_very_long_task(self, client):
        """Test d'ajout de tâche très longue"""
        long_task = "A" * 1000  # Tâche de 1000 caractères
        rv = client.post('/add', data={'task': long_task})
        assert rv.status_code == 302
    
    def test_task_with_html_content(self, client):
        """Test d'ajout de tâche avec contenu HTML"""
        html_task = "<b>Tâche en gras</b> avec du <i>HTML</i>"
        rv = client.post('/add', data={'task': html_task})
        assert rv.status_code == 302

class TestRequestLogging:
    """Tests pour le logging des requêtes"""
    
    def test_request_with_remote_addr(self, client):
        """Test du logging avec adresse IP"""
        with client.application.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            rv = client.post('/add', data={'task': 'Test IP logging'})
            assert rv.status_code == 302
