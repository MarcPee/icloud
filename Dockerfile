# Dockerfile voor iCloud to My Cloud Home Sync
FROM python:3.10-slim

# Installeer afhankelijkheden voor SMB (smbclient)
RUN apt-get update && apt-get install -y \
    libkrb5-dev \
    && rm -rf /var/lib/apt/lists/*

# Werkdirectory
WORKDIR /app

# Kopieer bestanden
COPY requirements.txt .
COPY icloud_to_mycloud.py .
COPY .env.example .

# Installeer Python-pakketten
RUN pip install --no-cache-dir -r requirements.txt

# Maak het script uitvoerbaar
RUN chmod +x icloud_to_mycloud.py

# Standaard commando
ENTRYPOINT ["python", "icloud_to_mycloud.py"]
