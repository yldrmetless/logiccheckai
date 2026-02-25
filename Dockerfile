FROM python:3.13-slim

# Sistem bağımlılıklarını yükle (Postgres bağlantısı için gerekli)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizinini ayarla
WORKDIR /app

# Bağımlılıkları kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını kopyala
COPY . .

# Django'yu başlat (Port 8000)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
