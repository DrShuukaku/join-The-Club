from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import os
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

class Base(DeclarativeBase):
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    logging.error("DATABASE_URL environment variable is not set!")
    logging.error("Please configure your PostgreSQL database in Replit.")
    raise RuntimeError("DATABASE_URL environment variable is required. Please set up your PostgreSQL database.")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    "pool_recycle": 300,
}
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

db = SQLAlchemy(app, model_class=Base)

_db_initialized = False

def run_migrations():
    """Add any missing columns to existing tables without dropping data."""
    migrations = [
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS category VARCHAR(100) NOT NULL DEFAULT 'general'",
        "ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS fingerprint_file_data BYTEA",
        "ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS fingerprint_file_name VARCHAR(255)",
        "ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS fingerprint_file_type VARCHAR(100)",
    ]
    with db.engine.connect() as conn:
        for statement in migrations:
            try:
                conn.execute(db.text(statement))
            except Exception as e:
                logging.warning(f"Migration skipped or failed: {e}")
        conn.commit()

    admin_emails = [e.strip().lower() for e in os.environ.get('ADMIN_EMAILS', '').split(',') if e.strip()]
    if admin_emails:
        try:
            from models import User
            for email in admin_emails:
                user = User.query.filter_by(email=email).first()
                if user and not user.is_admin:
                    user.is_admin = True
                    db.session.commit()
                    logging.info(f"Admin privileges restored for {email}")
        except Exception as e:
            logging.warning(f"Admin email sync failed: {e}")

    logging.info("Database migrations applied successfully")

def init_db():
    """Initialize database tables. Called on first request."""
    global _db_initialized
    if not _db_initialized:
        with app.app_context():
            try:
                import models
                try:
                    db.create_all()
                except Exception:
                    db.session.rollback()
                run_migrations()
                logging.info("Database tables created successfully")
                _db_initialized = True
            except Exception as e:
                logging.error(f"Failed to initialize database: {e}")
                raise

@app.context_processor
def inject_now():
    return {'now': datetime.now}

@app.before_request
def ensure_db_initialized():
    """Ensure database is initialized before handling any request."""
    init_db()

@app.errorhandler(500)
def internal_error(error):
    """Log internal server errors with full details."""
    logging.error(f"Internal Server Error: {error}", exc_info=True)
    return f"<h1>Internal Server Error</h1><p>Error details: {str(error)}</p><pre>{error.__class__.__name__}</pre>", 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Log all unhandled exceptions."""
    logging.error(f"Unhandled exception: {e}", exc_info=True)
    return f"<h1>Error</h1><p>{str(e)}</p>", 500
