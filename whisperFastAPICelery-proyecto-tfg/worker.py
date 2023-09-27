from celery import Celery
import whisper
import torch
import os
from whisper.tokenizer import LANGUAGES
from deep_translator import GoogleTranslator
from fastapi.templating import Jinja2Templates

celery_app = Celery('worker', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

# Comprobar si hay disponible una GPU NVIDIA
torch.cuda.is_available()
device = "cuda" if torch.cuda.is_available() else "cpu"

# Cargar el modelo Whisper. Inicializar el modelo de tamaño medio, lento, pero preciso en idiomas diferentes al inglés,
# moviéndolo a GPU si CUDA está disponible
model = whisper.load_model("medium").to(device)

# Configuración de Jinja2Templates
templates = Jinja2Templates(directory="templates")

# Variable global para almacenar los resultados de transcripción
transcription_results = {}


@celery_app.task
def procesar_archivo(localizacion_archivo):
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

    # Eliminar el archivo después de usar Whisper
    os.remove(localizacion_archivo)

    # Almacenar los resultados en la variable global
    resultados = {"nombreArchivo": localizacion_archivo, "transcripcion": transcripcion['text'], "idioma": idioma_detectado}

    # Redirigir a la página de resultados en la misma pestaña
    url = f"/resultados?localizacion_archivo={localizacion_archivo}"
    return resultados