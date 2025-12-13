FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

# Creamos directorios necesarios
RUN mkdir -p /app/data /app/staticfiles

# --- CAMBIOS NUEVOS ---
# Copiamos el script de entrada y le damos permisos
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Definimos el entrypoint. Cada vez que inicie, correrá este script primero
ENTRYPOINT ["/app/entrypoint.sh"]

EXPOSE 8000

# El comando final sigue siendo Gunicorn
CMD ["gunicorn", "mixtemiches_app.wsgi:application", "--bind", "0.0.0.0:8000"]