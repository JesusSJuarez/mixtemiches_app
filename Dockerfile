# Usamos una imagen ligera de Python compatible con tus requerimientos
FROM python:3.11-slim

# Evita que Python genere archivos .pyc y buffer de salida
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo en el contenedor
WORKDIR /app

# Instalamos dependencias del sistema necesarias para Pillow y compilación
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiamos e instalamos los requerimientos
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código
COPY . /app/

# Creamos un directorio para la base de datos (para persistencia)
RUN mkdir -p /app/data

# NOTA: Para producción real, deberías configurar STATIC_ROOT en settings.py
# y usar whitenoise o nginx. Por ahora, asumimos que manejas estáticos o usas DEBUG.

# Exponemos el puerto
EXPOSE 8000

# Comando para iniciar la aplicación usando Gunicorn
# Ajustamos bind a 0.0.0.0 para que sea accesible desde fuera del contenedor
CMD ["gunicorn", "mixtemiches_app.wsgi:application", "--bind", "0.0.0.0:8000"]