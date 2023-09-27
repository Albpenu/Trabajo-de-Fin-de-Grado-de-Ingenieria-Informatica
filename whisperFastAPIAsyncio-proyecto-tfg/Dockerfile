# Elijo la versión liviana de python 3.9-bullseye.
FROM python:3.9-slim-bullseye

# Creo un directorio de trabajo llamado python
WORKDIR /proyecto

# Copio el archivo requirements.txt al directorio de trabajo
COPY requirements.txt requirements.txt

# Actualizo el gestor de paquetes apt de linux
RUN apt-get update

# Instalo los requisitos del archivo requirements.txt
RUN pip install -r requirements.txt

# Descargo e instalo (o actualizo) la última versión disponible del modelo de ia Whisper
RUN pip install -U openai-whisper

# Instalo ffmpeg
RUN apt-get install -y ffmpeg

# Se copian los archivos de la aplicación al contenedor
COPY . .

# Expongo el puerto 5000
EXPOSE 5000

# Ejecuto el servidor FastAPI
CMD ["python", "main.py"]