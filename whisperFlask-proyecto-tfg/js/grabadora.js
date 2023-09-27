let mediaRecorder;
let chunks = [];

function cambiarEstado(evento){
    let texto = evento.innerHTML;
    
    if(texto == 'Grabar audio') 
    {
        
        //Grabando
		navigator.mediaDevices.getUserMedia({ audio: true })
		.then(stream => {
			mediaRecorder = new MediaRecorder(stream);
			mediaRecorder.start();
			evento.innerHTML = 'Parar grabación';
			chunks = [];
			mediaRecorder.addEventListener("dataavailable", event => {
				chunks.push(event.data);
			});
		})
		.catch(error => {
			console.log(error);
		});
    }
    else 
    {
       
        //Grabación pausada
        let reproductor = document.getElementById('reproductor');
        reproductor.style.display === 'none' ? reproductor.style.display === 'block' : reproductor.style.display = 'none';

		mediaRecorder.stop();
		evento.innerHTML = 'Grabar audio';
		const blob = new Blob(chunks, { type: "audio/ogg; codecs=opus" });
		const audioURL = URL.createObjectURL(blob);
		document.getElementById("recordedAudio").src = audioURL;
        
    }
  }