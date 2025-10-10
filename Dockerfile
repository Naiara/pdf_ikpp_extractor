FROM python:3.11-slim

WORKDIR /app

# Install system deps for pdfplumber/pdfminer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2 \
    libxslt1.1 \
    poppler-utils \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

## Copy only runtime files to the image to avoid including tests or sample PDFs
COPY app /app/app
COPY cli.py /app/cli.py
COPY README.md /app/README.md
COPY requirements.txt /app/requirements.txt

ENV PORT=8083
EXPOSE 8083

# use shell so $PORT is expanded from environment
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
