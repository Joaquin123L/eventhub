# Imagen base optimizada y liviana
# Usamos 'python:3.12-slim' en lugar de 'python:3.12' para reducir significativamente el tamaño de la imagen.
FROM python:3.12-slim

# Variables de entornos
# Desactivar generación de archivos .pyc y buffer de stdout para logs limpios
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Crear directorio de trabajo en el contenedor
WORKDIR /app

# Copiar primero solo el archivo de dependencias
# Esto permite usar el cache de Docker si no cambia el requirements.txt.
COPY requirements.txt .

# Instalar dependencias de Python de forma eficiente
# --no-cache-dir evita que pip guarde caché en la imagen.
# upgrade pip para asegurarnos de no usar una versión vieja.
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el resto de la aplicación al contenedor
COPY . .

# Exponer el puerto que usará la app (Django usa el 8000 por defecto)
EXPOSE 8000

# Ejecuta las migraciones y luego levanta la app con Gunicorn en producción
CMD ["sh", "-c", "python manage.py migrate && gunicorn eventhub.wsgi:application --bind 0.0.0.0:8000"]
