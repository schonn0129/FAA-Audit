# FAA DCT Compliance Engine - Backend
# Includes sentence-transformers for semantic embeddings

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for pdfplumber and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# sentence-transformers will pull PyTorch automatically
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model during build (optional but faster startup)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application code
COPY . .

# Create directories for data persistence
RUN mkdir -p /app/uploads /app/manuals /app/data

# Environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV EMBEDDING_ENABLED=true
ENV PYTHONUNBUFFERED=1

# Expose Flask port
EXPOSE 5000

# Run the Flask application
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
