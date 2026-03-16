"""
CodeLearn Platform - App Factory
Flask application factory pattern for modular architecture
"""

from flask import Flask
from flask_pymongo import PyMongo
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize MongoDB (will be configured in create_app)
mongo = PyMongo()

def create_app():
    """
    Application factory pattern
    Creates and configures Flask app with all dependencies
    """
    app = Flask(__name__)
    
    # Configuration
    app.config['MONGO_URI'] = os.getenv('MONGO_URI')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['JSON_SORT_KEYS'] = False
    
    # Initialize MongoDB
    mongo.init_app(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.exercises import exercises_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(exercises_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    
    @app.route('/')
    def index():
        """Temporary route - will be moved to auth blueprint in Week 2"""
        return '''
        <h1>CodeLearn Platform - Under Redesign</h1>
        <p>Modular architecture initialized.</p>
        <p>Check the git repository for progress.</p>
        ''', 200
    
    @app.route('/health')
    def health():
        """Health check endpoint"""
        try:
            # Check MongoDB connection
            mongo.db.command('ping')
            return {'status': 'healthy', 'mongodb': 'connected'}, 200
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}, 500
    
    return app
