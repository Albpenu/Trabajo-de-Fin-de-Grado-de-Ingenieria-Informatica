import asyncio
import os
import yt_dlp
import time
from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse
import uvicorn
import whisper
import torch
from fastapi.templating import Jinja2Templates
from whisper.tokenizer import LANGUAGES
from deep_translator import GoogleTranslator

app = FastAPI()
templates = Jinja2Templates(directory="templates")
cola = asyncio.Queue()

# Comprobar si hay disponible una GPU NVIDIA
torch.cuda.is_available()
device = "cuda" if torch.cuda.is_available() else "cpu"

# Cargar el modelo Whisper. Inicializar el modelo de tamaño medio, lento, pero preciso en idiomas diferentes al inglés,
# moviéndolo a GPU si CUDA está disponible
model = whisper.load_model("medium").to(device)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", context={"request": request})


#  Ignorar la solicitud de favicon.ico en la aplicación FastAPI agregando una ruta para manejarla específicamente
#  y devolviendo una respuesta vacía
@app.get("/favicon.ico")
async def favicon():
    return ""


# Definir la función que procesará las solicitudes
async def procesar_archivo(localizacion_archivo, cola: asyncio.Queue):

    # Cargar audio y rellenarlo/recortarlo para que se ajuste a trozos de 30 segundos
    audio = whisper.load_audio(localizacion_archivo)  # str, bytes or os.PathLike
    audio = whisper.pad_or_trim(audio)
    # Hacer un espectrograma log-Mel y pasar al mismo dispositivo que el modelo
    mel = whisper.log_mel_spectrogram(audio).to(model.device)

    # Detectar el idioma hablado
    _, probs = model.detect_language(mel)
    traductor = GoogleTranslator(source='auto', target='es')
    idioma_detectado = traductor.translate(LANGUAGES[max(probs, key=probs.get)].title())

    # Decodificamos el audio
    # options = whisper.DecodingOptions(fp16 = False)
    # transcripcion = whisper.decode(model, mel, options)
    transcripcion = model.transcribe(localizacion_archivo)

    # Agregar los elementos a la cola asíncrona
    await cola.put(idioma_detectado)
    await cola.put(transcripcion)

    # Eliminar el archivo del disco
    os.remove(localizacion_archivo)

    # Devolvemos la transcripción y el idioma
    return idioma_detectado, transcripcion['text']


@app.post('/transcripcion_grabacion', response_class=HTMLResponse)
async def transcripcion_grabacion(request: Request, audiograbado: UploadFile = File(...)):
    # Guardo el archivo en una ubicación (la raiz del directorio actual) temporal
    localizacion_archivo = f"./{audiograbado.filename}"

    with open(localizacion_archivo, "wb+") as file_object:
        file_object.write(await audiograbado.read())

    # Obtener el nombre del archivo y su formato
    nombre_archivo = audiograbado.filename.split(".")

    # Guardar el tiempo de inicio
    tiempo_inicio = int(time.time())

    # Se invoca a la función procesar_archivo y se espera a que se complete antes de continuar
    await procesar_archivo(localizacion_archivo, cola)
    # Obtener los elementos de la cola asíncrona
    idioma_detectado = await cola.get()
    transcripcion = await cola.get()

    # Guardar el tiempo de finalización
    tiempo_final = int(time.time())
    # Calcular el tiempo de transcripción en segundos
    tiempo_transcripcion = tiempo_final - tiempo_inicio

    # Renderizar la plantilla
    return templates.TemplateResponse("resultado.html", {"request": request, "nombreArchivo": nombre_archivo[0],
                                                      "formato": nombre_archivo[1], "idioma": idioma_detectado,
                                                      "transcripcion": transcripcion['text'],
                                                         "tiempoTranscripcion": tiempo_transcripcion})


@app.post('/transcripcion_archivo', response_class=HTMLResponse)
async def transcripcion_archivo(request: Request, archivo_audio: UploadFile = File(...)):

    localizacion_archivo = f"./{archivo_audio.filename}"

    with open(localizacion_archivo, "wb+") as file_object:
        file_object.write(await archivo_audio.read())

    # Obtener el nombre del archivo y su formato
    nombre_archivo = archivo_audio.filename.split('.')

    # Guardar el tiempo de inicio
    tiempo_inicio = int(time.time())

    await procesar_archivo(localizacion_archivo, cola)
    idioma_detectado = await cola.get()
    transcripcion = await cola.get()

    # Guardar el tiempo de finalización
    tiempo_final = int(time.time())

    # Calcular el tiempo de transcripción en segundos
    tiempo_transcripcion = tiempo_final - tiempo_inicio

    return templates.TemplateResponse("resultado.html", {"request": request, "nombreArchivo": nombre_archivo[0],
                                                         "formato": nombre_archivo[1], "idioma": idioma_detectado,
                                                         "transcripcion": transcripcion['text'], "tiempoTranscripcion": tiempo_transcripcion})


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

    await procesar_archivo("audio.mp3", cola)
    idioma_detectado = await cola.get()
    transcripcion = await cola.get()

    # Guardar el tiempo de finalización
    tiempo_final = int(time.time())

    # Calcular el tiempo de transcripción en segundos
    tiempo_transcripcion = tiempo_final - tiempo_inicio

    return templates.TemplateResponse("resultado.html", {"request": request, "nombreArchivo": title,
                                                         "formato": "mp3", "idioma": idioma_detectado,
                                                         "transcripcion": transcripcion['text'],
                                                         "tiempoTranscripcion": tiempo_transcripcion})

# Para ejecutarlo en local y depurarlo
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
