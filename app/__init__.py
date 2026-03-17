"""
CodeLearn Platform - App Factory
Flask application factory pattern for modular architecture
"""

from flask import Flask
from flask_pymongo import PyMongo
import os
import markdown as md_lib
from dotenv import load_dotenv

load_dotenv()

# Initialize MongoDB (will be configured in create_app)
mongo = PyMongo()


def _build_mongo_uri(base_uri: str, db_name: str) -> str:
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
    
    # Configuration
    app.config['MONGO_URI'] = mongo_uri
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
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
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(exercises_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)

    # Legacy-compatible page endpoints migrated from monolith.
    app.add_url_rule('/', endpoint='index', view_func=web_pages.index)
    app.add_url_rule('/static-mode', endpoint='static_mode', view_func=web_pages.static_mode)
    app.add_url_rule('/interactive-mode', endpoint='interactive_mode', view_func=web_pages.interactive_mode)
    app.add_url_rule('/submit', endpoint='submit', view_func=web_pages.submit, methods=['POST'])
    app.add_url_rule('/db-status', endpoint='db_status', view_func=web_pages.db_status)
    app.add_url_rule('/admin-login', endpoint='admin_login', view_func=web_pages.admin_login, methods=['GET', 'POST'])
    app.add_url_rule('/admin-logout', endpoint='admin_logout', view_func=web_pages.admin_logout)
    app.add_url_rule('/admin-dashboard', endpoint='admin_dashboard', view_func=web_pages.admin_dashboard)
    app.add_url_rule('/complete', endpoint='session_complete', view_func=web_pages.session_complete)
    app.add_url_rule('/research-info', endpoint='research_info', view_func=web_pages.research_info)
    app.add_url_rule('/methodology', endpoint='methodology_page', view_func=web_pages.methodology_page)
    app.add_url_rule('/learn/<topic_id>', endpoint='topic_page', view_func=web_pages.topic_page)
    app.add_url_rule('/quiz/<topic_id>', endpoint='topic_quiz', view_func=web_pages.topic_quiz, methods=['GET', 'POST'])
    app.add_url_rule('/export-research-dataset', endpoint='export_research_dataset', view_func=web_pages.export_research_dataset)
    app.add_url_rule('/export-session-summary', endpoint='export_session_summary', view_func=web_pages.export_session_summary)
    
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
