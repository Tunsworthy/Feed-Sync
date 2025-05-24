FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY app.py .
COPY .env .
COPY credentials.json ./credentials.json  # Your Google service account file

CMD ["python", "app.py"]
