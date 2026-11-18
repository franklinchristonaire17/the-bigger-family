import os
import sys

# Ensure parent directory is in sys.path so app and database can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import init_db

# Initialize database schemas if not already done
try:
    init_db()
except Exception:
    pass

# Vercel WSGI entry point
# Exports the Flask application instance as 'app'
