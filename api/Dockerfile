FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/app/ ./app/

# Copy tracking templates
COPY tracking/ ./tracking/

# Expose port
EXPOSE 8000

# Command will be overridden by docker-compose for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]