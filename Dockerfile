FROM python:3.13-slim

# Sistem bağımlılıklarını yükle
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

# Render 10000 portunu kullandığı için onu açıyoruz
EXPOSE 10000

# Hem migrate yapıp hem serverı başlatan komut
# Canlıda gunicorn önerilir ama şimdilik runserver ile ayağa kaldıralım
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:10000"]
