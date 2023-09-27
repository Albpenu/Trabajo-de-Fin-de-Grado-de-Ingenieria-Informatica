import os
import time
from flask import Flask, request, render_template
import whisper
import torch
from whisper.tokenizer import LANGUAGES
from deep_translator import GoogleTranslator
import yt_dlp

app = Flask(__name__)
app.config['ALLOWED_EXTENSIONS'] = {'wav', 'mp3', 'ogg', 'flac'}

# Comprobar si hay disponible una GPU NVIDIA
torch.cuda.is_available()
device = "cuda" if torch.cuda.is_available() else "cpu"

# Cargar el modelo Whisper. Inicializar el modelo de tamaño medio, lento, pero preciso en idiomas diferentes al inglés,
# moviéndolo a GPU si CUDA está disponible
model = whisper.load_model("medium").to(device)


@app.route("/")
def home():
    return render_template("index.html")


# Definir la función que procesará las archivos
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

    # Eliminar el archivo del disco
    os.remove(localizacion_archivo)

    # Devolvemos la transcripción y el idioma
    return idioma_detectado, transcripcion['text']


@app.route('/transcripcion_grabacion', methods=['POST'])
def transcripcion_grabacion():

    audiograbado = request.files['audiograbado']

    if audiograbado and allowed_file(audiograbado.filename):
        # Guardo el archivo en una ubicación (la raiz del directorio actual) temporal
        localizacion_archivo = f"./{audiograbado.filename}"

        with open(localizacion_archivo, "wb+") as file_object:
            file_object.write(audiograbado.read())

        # Obtener el nombre del archivo y su formato
        nombre_archivo = audiograbado.filename.split(".")

        # Guardar el tiempo de inicio
        tiempo_inicio = int(time.time())

        # Se obtienen los valores de idioma y transcripción de la función procesar_archivo
        idioma_detectado, transcripcion = procesar_archivo(localizacion_archivo)

        # Guardar el tiempo de finalización
        tiempo_final = int(time.time())
        # Calcular el tiempo de transcripción en segundos
        tiempo_transcripcion = tiempo_final - tiempo_inicio

        # Renderizar la plantilla
        return render_template("resultado.html", nombreArchivo=nombre_archivo[0], formato=nombre_archivo[1],
                               idioma=idioma_detectado, transcripcion=transcripcion, tiempoTranscripcion=tiempo_transcripcion)
    else:
        return "Error: Archivo no válido."


@app.route('/transcripcion_archivo', methods=['POST'])
def transcripcion_archivo():

    archivo_audio = request.files['archivo_audio']

    if archivo_audio and allowed_file(archivo_audio.filename):
        # Guardo el archivo en una ubicación (la raiz del directorio actual) temporal
        localizacion_archivo = f"./{archivo_audio.filename}"

        with open(localizacion_archivo, "wb+") as file_object:
            file_object.write(archivo_audio.read())

        # Obtener el nombre del archivo y su formato
        nombre_archivo = archivo_audio.filename.split('.')

        # Guardar el tiempo de inicio
        tiempo_inicio = int(time.time())

        # Se obtienen los valores de idioma y transcripción de la función procesar_archivo
        idioma_detectado, transcripcion = procesar_archivo(localizacion_archivo)

        # Guardar el tiempo de finalización
        tiempo_final = int(time.time())

        # Calcular el tiempo de transcripción en segundos
        tiempo_transcripcion = tiempo_final - tiempo_inicio

        return render_template("resultado.html", nombreArchivo=nombre_archivo[0], formato=nombre_archivo[1],
                           idioma=idioma_detectado, transcripcion=transcripcion,
                           tiempoTranscripcion=tiempo_transcripcion)
    else:
        return "Error: Archivo no válido."


@app.route('/transcripcion_video', methods=['POST'])
def transcripcion_video():
    url = request.form['url']

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

    # Se obtienen los valores de idioma y transcripción de la función procesar_archivo
    idioma_detectado, transcripcion = procesar_archivo("audio.mp3")

    # Guardar el tiempo de finalización
    tiempo_final = int(time.time())

    # Calcular el tiempo de transcripción en segundos
    tiempo_transcripcion = tiempo_final - tiempo_inicio

    return render_template("resultado.html", nombreArchivo=title, formato="mp3", idioma=idioma_detectado,
                           transcripcion=transcripcion, tiempoTranscripcion=tiempo_transcripcion)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# Para ejecutarlo en local y depurarlo
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)