#!/bin/bash

# Detener el script si hay errores
set -e

echo "--- Iniciando configuración de MixteMiches ---"

# 1. PERSISTENCIA DE BASE DE DATOS (Truco del enlace simbólico)
# Si la carpeta de datos montada existe, enlazamos el db.sqlite3 de ahí
# a la ubicación donde Django lo espera (/app/db.sqlite3).
if [ -d "/app/data" ]; then
    echo "Configurando persistencia de base de datos..."
    # Si no existe el archivo en el volumen, lo creamos vacío para poder enlazarlo
    if [ ! -f "/app/data/db.sqlite3" ]; then
        touch /app/data/db.sqlite3
    fi
    # Creamos un enlace simbólico: Django escribe en /app/db.sqlite3 -> Realmente escribe en /app/data/db.sqlite3
    ln -sf /app/data/db.sqlite3 /app/db.sqlite3
fi

# 2. RECOLECCIÓN DE ARCHIVOS ESTÁTICOS
# Nota: Asegúrate de tener STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') en tu settings.py
echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

# 3. MIGRACIONES DE BASE DE DATOS
echo "Ejecutando migraciones..."
python manage.py migrate

echo "--- Configuración terminada. Iniciando Servidor ---"

# Ejecuta el comando pasado al contenedor (gunicorn)
exec "$@"