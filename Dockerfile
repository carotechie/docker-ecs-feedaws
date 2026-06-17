# 1. Imagen base liviana de Python
FROM python:3.12-slim

# 2. Carpeta de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiamos solo el archivo de dependencias primero (mejor cache de Docker)
COPY requirements.txt .

# 4. Instalamos dependencias
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiamos el resto del código de la app
COPY . .

# 6. Puerto en el que escucha la app
EXPOSE 8080

# 7. Comando de arranque (gunicorn para producción)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
