# Elijo la versión completa de python 3.9-bullseye.
FROM python:3.9-bullseye

# Creo un directorio de trabajo llamado python
WORKDIR /python

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

COPY . .

# Expongo el puerto 3000
EXPOSE 3000

# Ejecuto el servidor Flask
CMD [ "python", "main.py"]