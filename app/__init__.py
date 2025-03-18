from flask import Flask
from .config.settings import FLASK_APP_NAME, DEBUG
from .routes.main_routes import main_routes
from .routes.label_routes import label_routes
from .routes.template_routes import template_routes

def create_app():
    """Create and configure the Flask application."""
    app = Flask(FLASK_APP_NAME)
    app.debug = DEBUG

    # Register blueprints
    app.register_blueprint(main_routes)
    app.register_blueprint(label_routes)
    app.register_blueprint(template_routes)

    return app