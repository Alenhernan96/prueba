# Usa una imagen oficial de Python 3.10
FROM python:3.10-slim

# Variables de entorno para no generar prompts de instalación
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libzbar0 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Crea un directorio de trabajo
WORKDIR /app

# Copia el requirements.txt
COPY requirements.txt .

# Instala las dependencias de Python
RUN pip install --upgrade pip setuptools wheel
RUN pip install --prefer-binary -r requirements.txt

# Copia todo el código de la aplicación
COPY . .

# Expone el puerto que usa Render
EXPOSE 10000
ENV PORT 10000

# Comando por defecto para correr Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]
