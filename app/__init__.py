"""
CodeLearn Platform - App Factory
Flask application factory pattern for modular architecture
"""

from flask import Flask
from flask_pymongo import PyMongo
import os
import secrets
import markdown as md_lib
from dotenv import load_dotenv

load_dotenv()

# Initialize MongoDB (will be configured in create_app)
mongo = PyMongo()


def _build_mongo_uri(base_uri: str | None, db_name: str) -> str | None:
    """Attach a default database to Mongo URI when one is not present."""
    if not base_uri:
        return base_uri
    if "/?" in base_uri:
        return base_uri.replace("/?", f"/{db_name}?", 1)
    if base_uri.endswith("/"):
        return f"{base_uri}{db_name}"
    if base_uri.count("/") <= 2:
        return f"{base_uri}/{db_name}"
    return base_uri

def create_app():
    """
    Application factory pattern
    Creates and configures Flask app with all dependencies
    """
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
        static_url_path="/static",
    )
    mongo_uri = _build_mongo_uri(os.getenv('MONGO_URI'), 'programming_research')
    secret_key = os.getenv('SECRET_KEY') or secrets.token_hex(32)
    
    # Configuration
    app.config['MONGO_URI'] = mongo_uri
    app.config['SECRET_KEY'] = secret_key
    app.config['ADMIN_USERNAME'] = os.getenv('ADMIN_USERNAME', '')
    app.config['ADMIN_PASSWORD'] = os.getenv('ADMIN_PASSWORD', '')
    app.config['JSON_SORT_KEYS'] = False

    @app.template_filter('md')
    def render_markdown(text):
        return md_lib.markdown(text or "", extensions=['tables', 'fenced_code'])
    
    # Initialize MongoDB
    mongo.init_app(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.exercises import exercises_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.admin import admin_bp
    from app.routes import web_pages
    from app.routes import stats_api
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(exercises_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)

    web_pages.register_web_page_routes(app)
    stats_api.register_stats_routes(app)
    
    @app.route('/health')
    def health():
        """Health check endpoint"""
        try:
            # Check MongoDB connection
            if mongo.db is None:
                return {'status': 'unhealthy', 'error': 'MongoDB not initialized'}, 500
            mongo.db.command('ping')
            return {'status': 'healthy', 'mongodb': 'connected'}, 200
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}, 500
    
    return app
