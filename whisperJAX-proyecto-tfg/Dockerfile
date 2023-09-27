FROM tensorflow/tensorflow:2.12.0-gpu

# Creo un directorio de trabajo
WORKDIR /proyecto

# Actualizo los paquetes y ////////////////preprocesado del audio antes de transcribirlo
RUN apt-get update && \
    apt-get install python3 && \
    apt-get install -y redis-server && \
    apt-get install -y ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

# Copio el archivo requirements.txt al directorio de trabajo
COPY requirements.txt .

# Instalo o actualizo los requisitos/dependencias/paquetes especificados en el archivo requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Instalo la biblioteca de aprendizaje automático JAX junto con CUDA
RUN pip install --upgrade "jax[cuda11_pip]" -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html

# Instalo el modelo Whisper JAX
RUN pip install git+https://github.com/sanchit-gandhi/whisper-jax.git

# Se copian los archivos de la aplicación al contenedor O: COPY main.py .
COPY . .

# Se establece el puerto por defecto en el contenedor
EXPOSE 9000

# Ejecuto el servidor FastAPI
CMD ["python", "main.py"]