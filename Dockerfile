# Imagen base completa
FROM python:3.12

# Copia todo el contexto, incluso archivos innecesarios
COPY . .

# Instala dependencias sin usar cache ni limpieza
RUN pip install -r requirements.txt

# Variables de entornos
# Desactivar generación de archivos .pyc y buffer de stdout para logs limpios
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Exponer el puerto que usará la app (Django usa el 8000 por defecto)
EXPOSE 8000

# Comando para ejecutar la app usando el servidor de desarrollo de Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]