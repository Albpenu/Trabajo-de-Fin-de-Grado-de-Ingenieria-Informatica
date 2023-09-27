from celery import Celery
import redis
import time
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from worker import procesar_archivo, transcription_results
import uvicorn
import yt_dlp

app = FastAPI()

# Configuración de Jinja2Templates
templates = Jinja2Templates(directory="templates")

# Configuración de Celery
celery_app = Celery('app', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

# Crear una conexión a Redis con contraseña
r = redis.Redis(host='localhost', port=6379, password='1234')


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", context={"request": request})


#  Ignorar la solicitud de favicon.ico en la aplicación FastAPI agregando una ruta para manejarla específicamente
#  y devolviendo una respuesta vacía
@app.get("/favicon.ico")
async def favicon():
    return ""


@app.post("/transcripcion_grabacion", response_class=HTMLResponse)
async def transcripcion_grabacion(request: Request, audiograbado: UploadFile = File(...)):
    # Guardo el archivo en una ubicación (la raiz del directorio actual) temporal
    localizacion_archivo = f"uploads/{audiograbado.filename}"

    with open(localizacion_archivo, "wb+") as file_object:
        file_object.write(await audiograbado.read())

    # Obtener el nombre del archivo y su formato
    nombre_archivo = audiograbado.filename.split(".")

    # Guardar el tiempo de inicio
    tiempo_inicio = int(time.time())

    # Encolar la tarea de procesamiento
    task = procesar_archivo.delay(localizacion_archivo)
    task_id = task.id

    # Obtener los resultados de la transcripción desde la variable global
    resultados = task.get()

    # Guardar el tiempo de finalización
    tiempo_final = int(time.time())

    # Calcular el tiempo de transcripción en segundos
    tiempo_transcripcion = tiempo_final - tiempo_inicio

    # Renderizar la página de "Resultados"
    return templates.TemplateResponse("resultados.html",
                                      {"request": request, "nombreArchivo": nombre_archivo[0],
                                                      "formato": nombre_archivo[1], "idioma": resultados["idioma"],
                                                      "transcripcion": resultados['transcripcion'],
                                       "tiempoTranscripcion": tiempo_transcripcion})


@app.post("/transcripcion_archivo", response_class=HTMLResponse)
async def transcripcion_archivo(request: Request, archivo_audio: UploadFile = File(...)):
    # Guardo el archivo en una ubicación (la raiz del directorio actual) temporal
    localizacion_archivo = f"uploads/{archivo_audio.filename}"

    with open(localizacion_archivo, "wb+") as file_object:
        file_object.write(await archivo_audio.read())

    # Obtener el nombre del archivo y su formato
    nombre_archivo = archivo_audio.filename.split(".")

    # Guardar el tiempo de inicio
    tiempo_inicio = int(time.time())

    # Encolar la tarea de procesamiento
    task = procesar_archivo.delay(localizacion_archivo)
    task_id = task.id

    # Obtener los resultados de la transcripción desde la variable global
    resultados = task.get()

    # Guardar el tiempo de finalización
    tiempo_final = int(time.time())

    # Calcular el tiempo de transcripción en segundos
    tiempo_transcripcion = tiempo_final - tiempo_inicio

    # Renderizar la página de "Resultados"
    return templates.TemplateResponse("resultados.html",
                                      {"request": request, "nombreArchivo": nombre_archivo[0],
                                                      "formato": nombre_archivo[1], "idioma": resultados["idioma"],
                                                      "transcripcion": resultados['transcripcion'],
                                       "tiempoTranscripcion": tiempo_transcripcion})


@app.post("/transcripcion_video", response_class=HTMLResponse)
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

    # Encolar la tarea de procesamiento
    task = procesar_archivo.delay("audio.mp3")
    task_id = task.id

    # Obtener los resultados de la transcripción desde la variable global
    resultados = task.get()

    # Guardar el tiempo de finalización
    tiempo_final = int(time.time())

    # Calcular el tiempo de transcripción en segundos
    tiempo_transcripcion = tiempo_final - tiempo_inicio

    # Renderizar la página de "Resultados"
    return templates.TemplateResponse("resultados.html",
                                      {"request": request, "nombreArchivo": title,
                                                      "formato": "mp3", "idioma": resultados["idioma"],
                                                      "transcripcion": resultados['transcripcion'],
                                       "tiempoTranscripcion": tiempo_transcripcion})


@app.get("/procesando")
async def show_procesando(request: Request, task_id: str):
    return templates.TemplateResponse("procesando.html", {"request": request, "task_id": task_id})


@app.post("/resultados")
async def get_results(request: Request, localizacion_archivo: str):
    # Obtener los resultados de la transcripción desde la variable global
    resultados = transcription_results.get(localizacion_archivo)

    if resultados:
        nombreArchivo = localizacion_archivo
        idioma = resultados["idioma"]
        transcripcion = resultados["transcripcion"]
    else:
        nombreArchivo = "No disponible"
        idioma = "No disponible"
        transcripcion = "No disponible"

    # Renderizar la página de "Resultados"
    return templates.TemplateResponse("resultados.html", {"request": request, "nombreArchivo": nombreArchivo, "idioma": idioma, "transcripcion": transcripcion})


@app.get("/taskstatus")
def get_task_status(task_id: str):
    # Obtener estado de la tarea Celery
    result = procesar_archivo.AsyncResult(task_id)
    return {"status": result.status}


# La función se ejecutará una vez que la aplicación FastAPI se haya iniciado
# y establecerá la configuración de Celery indicada
@app.on_event("startup")
async def startup_event():
    celery_app.conf.task_routes = {'worker.transcribe_file': {'queue': 'transcription_queue'}}
    celery_app.conf.task_default_queue = 'default'
    celery_app.conf.worker_prefetch_multiplier = 1

# Para ejecutarlo en local y depurarlo
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
