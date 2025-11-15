from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import os
from werkzeug.middleware.proxy_fix import ProxyFix
import logging

logging.basicConfig(level=logging.INFO)

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

def init_db():
    """Initialize database tables. Called on first request."""
    global _db_initialized
    if not _db_initialized:
        with app.app_context():
            try:
                import models
                db.create_all()
                logging.info("Database tables created successfully")
                _db_initialized = True
            except Exception as e:
                logging.error(f"Failed to create database tables: {e}")
                raise

@app.before_request
def ensure_db_initialized():
    """Ensure database is initialized before handling any request."""
    init_db()
