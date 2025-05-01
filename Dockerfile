FROM python:3.12-slim

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Set working directory
WORKDIR /app

# Copy dependency file and install
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Expose the port for Cloud Run
EXPOSE $PORT

# Use shell form to allow environment variable expansion
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]