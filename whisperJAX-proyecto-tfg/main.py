#import yt_dlp
from celery import Celery
import os
import time

from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from tempfile import NamedTemporaryFile
import uvicorn
from fastapi.templating import Jinja2Templates
from deep_translator import GoogleTranslator

from whisper_jax import FlaxWhisperPipline

# Configurar la aplicación FastAPI
app = FastAPI()

# Configurar Jinja2
templates = Jinja2Templates(directory="templates")

# Configurar Celery con Redis
celery_app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

# Configurar Whisper JAX. Inicializar el modelo de tamaño grande v2
whisperjax_pipeline = FlaxWhisperPipline("openai/whisper-large-v2")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", context={"request": request})


# Definir la ruta que maneja las solicitudes de envío de archivos
@app.post('/transcripcion_grabacion', response_class=HTMLResponse)
async def transcripcion_grabacion(request: Request, audiograbado: UploadFile = File(...)):

    # Compruebo que se trata de un archivo de audio y limito su tamaño a un máximo de 100Mb
    if audiograbado.content_type.startswith('audio/'):
        if audiograbado.__sizeof__() > 100000000:
            return {"error": "Archivo demasiado grande. Supera los 100MB. Pruebe otro"}
        else:
            # Guardo el archivo en una ubicación (la raiz del directorio actual) temporal
            localizacion_archivo = f"./{audiograbado.filename}"
            with open(localizacion_archivo, "wb+") as archivo:
                archivo.write(await audiograbado.read())

            # Añadir la tarea de procesamiento a la cola de Celery
            tarea_transcripcion_audio.delay(audiograbado.filename)

            # Renderizar una página de carga mientras se procesa el audio
            return templates.TemplateResponse("procesando.html", {"request": request, "task_id": task.id})
    else:
        return {"error": "Tipo de archivo no permitido"}


@app.post('/transcripcion_archivo', response_class=HTMLResponse)
async def transcripcion_archivo(request: Request, archivo_audio: UploadFile = File(...)):

    # Compruebo que se trata de un archivo de audio y limito su tamaño a un máximo de 100Mb
    if archivo_audio.content_type.startswith('audio/'):
        if archivo_audio.__sizeof__() > 100000000:
            return {"error": "Archivo demasiado grande. Supera los 100MB. Pruebe otro"}
        else:
            # Guardo el archivo en una ubicación (la raiz del directorio actual) temporal
            localizacion_archivo = f"./{archivo_audio.filename}"
            with open(localizacion_archivo, "wb+") as archivo:
                archivo.write(await archivo_audio.read())

            # Añadir la tarea de procesamiento a la cola de Celery
            tarea_transcripcion_audio.delay(archivo_audio.filename)

            # Renderizar una página de carga mientras se procesa el audio
            return templates.TemplateResponse("procesando.html", {"request": request, "task_id": task.id})
    else:
        return {"error": "Tipo de archivo no permitido"}


@app.post('/transcripcion_video', response_class=HTMLResponse)
async def transcripcion_video(request: Request, url: str = Form(...)):
    
    # Configuración de yt-dlp
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "audio.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    # Descarga el audio del video
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Obtiene el título del video
    with yt_dlp.YoutubeDL() as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get("title", None)

    # Guardar el tiempo de inicio
    tiempo_inicio = int(time.time())

    # Añadir la tarea de procesamiento a la cola de Celery
    resultados_tarea = tarea_transcripcion_audio.delay("audio.mp3")

    # Obtener los resultados de la transcripción desde la variable global
    nombre_archivo, transcripcion, idioma_detectado = resultados_tarea.get()

    # Guardar el tiempo de finalización
    tiempo_final = int(time.time())

    # Calcular el tiempo de transcripción en segundos
    tiempo_transcripcion = tiempo_final - tiempo_inicio

    return templates.TemplateResponse("result.html",
                                      {"request": request,
                                       "nombreArchivo": nombre_archivo,
                                       # "formato": ,
                                       "transcripcion": transcripcion,
                                       "idioma": idioma_detectado,
                                       "tiempoTranscripcion": tiempo_transcripcion})


@celery_app.task
def tarea_transcripcion_audio(localizacion_archivo):

    # Leer el archivo de audio
    with open(localizacion_archivo, 'rb') as f:
        datos_audio = f.read()

    # Obtener el nombre del archivo y su formato
    nombre_archivo = datos_audio.filename.split(".")

    # Obtener la transcripción y el idioma del archivo de audio
    transcripcion = whisperjax_pipeline.transcribe_audio(localizacion_archivo)
    traductor = GoogleTranslator(source='auto', target='es')
    idioma_detectado = traductor.translate(whisperjax_pipeline.detect_language(localizacion_archivo))

    # Eliminar el archivo del disco
    os.remove(localizacion_archivo)

    # Devolvemos el nombre, la transcripción y el idioma
    return nombre_archivo, transcripcion, idioma_detectado


@app.get("/resultados/{task_id}", response_class=HTMLResponse)
async def obtener_resultados(task_id: str):
    # Guardar el tiempo de inicio
    tiempo_inicio = int(time.time())

    # Obtener el resultado de la tarea de Celery
    resultado = tarea_transcripcion_audio.AsyncResult(task_id)

    # Guardar el tiempo de finalización
    tiempo_final = int(time.time())

    # Calcular el tiempo de transcripción en segundos
    tiempo_transcripcion = tiempo_final - tiempo_inicio

    if task_id is None:
        # Si no hay tareas en la cola, devolver una página de error
        return templates.TemplateResponse('error.html')

    if resultado.ready():
        # Si la tarea ha terminado, devolver el resultado
        nombre_archivo, transcripcion, idioma_detectado = resultado.get()
        return templates.TemplateResponse("result.html",
                                          {"request": request,
                                           "nombreArchivo": nombre_archivo,
                                           #"formato": ,
                                           "transcripcion": transcripcion,
                                           "idioma": idioma_detectado,
                                           "tiempoTranscripcion": tiempo_transcripcion})
    else:
        # Renderizar una página de carga mientras se procesa el audio
        return templates.TemplateResponse("procesando.html", {"request": request, "task_id": task_id})

# Para ejecutarlo en local y depurarlo
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
