import os
import logging
from datetime import datetime
from flask import Flask
from config import config_by_name
from app.extensions import db, migrate, login_manager, csrf, init_redis
from app.utilities.helpers import format_datetime, status_badge_class
from app.utilities.errors import register_error_handlers
from app.routes import auth_bp, admin_bp, student_bp, main_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(config_name=None) -> Flask:
    """Application factory for Assignment Group Portal."""
    if not config_name:
        config_name = os.getenv("FLASK_ENV", "development").lower()

#    app = Flask(__name__,template_folder="../../frontend/templates",static_folder="../../frontend/static")
    app = Flask(__name__,template_folder="/frontend/templates",static_folder="/frontend/static")
    config_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db, directory="database/migrations")
    login_manager.init_app(app)
    csrf.init_app(app)

    # Initialize Redis with connection check & mock fallback
    with app.app_context():
        init_redis(app)

    # Register template filters
    app.jinja_env.filters["datetime"] = format_datetime
    app.jinja_env.filters["status_badge"] = status_badge_class

    # Register context processors
    @app.context_processor
    def inject_global_vars():
        return {
            "app_name": app.config.get("APP_NAME", "Assignment Group Portal"),
            "current_year": datetime.now().year,
        }

    # Register custom error handlers
    register_error_handlers(app)

    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)

    logger.info(f"Initialized {app.config.get('APP_NAME')} with config '{config_name}'")
    return app

