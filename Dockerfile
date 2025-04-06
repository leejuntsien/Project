# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create SSL directory with proper permissions
RUN mkdir -p /app/ssl && chmod 700 /app/ssl

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Expose ports
EXPOSE 8501
EXPOSE 5000
EXPOSE 5443

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Add SSL directory permissions and Streamlit config
RUN mkdir -p ~/.streamlit \
    && echo "[server]" > ~/.streamlit/config.toml \
    && echo "enableCORS = false" >> ~/.streamlit/config.toml \
    && echo "enableXsrfProtection = true" >> ~/.streamlit/config.toml

# Run the application
CMD ["python", "run_servers.py"]
