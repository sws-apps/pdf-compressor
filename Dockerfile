FROM python:3.11-slim

# Install system dependencies including Ghostscript
RUN apt-get update && apt-get install -y \
    ghostscript \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY static/ ./static/

# Expose port (Railway/Heroku will override with $PORT)
EXPOSE 8080

# Copy run script
COPY run.py .

# Start the application
CMD ["python", "run.py"]