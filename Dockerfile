# Base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (required for PyMuPDF)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose internal FastAPI port and external Hugging Face port
EXPOSE 8000
EXPOSE 7860

# Start FastAPI in the background, Streamlit in the foreground
CMD uvicorn main_api:app --host 0.0.0.0 --port 8000 & streamlit run frontend.py --server.port 7860 --server.address 0.0.0.0
