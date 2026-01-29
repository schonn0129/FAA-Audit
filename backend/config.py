"""
Configuration settings for the FAA Audit application.
"""

import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database configuration
DATABASE_PATH = os.path.join(BASE_DIR, 'faa_audit.db')
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'

# Upload configuration
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
ALLOWED_EXTENSIONS = {'pdf'}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Embedding configuration for semantic matching
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
EMBEDDING_ENABLED = os.getenv('EMBEDDING_ENABLED', 'true').lower() == 'true'
SEMANTIC_WEIGHT = float(os.getenv('SEMANTIC_WEIGHT', '0.5'))  # Balance between deterministic and semantic scoring
