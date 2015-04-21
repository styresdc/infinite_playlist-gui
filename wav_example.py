import pyaudio
import wave

CHUNK = 1024
wf = wave.open("lateralus30.wav")
p = pyaudio.PyAudio()
print wf.getnchannels()
stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True)
data = wf.readframes(CHUNK)
while data != '':
    stream.write(data)
    data = wf.readframes(CHUNK)

stream.stop_stream()
stream.close()
p.terminate()
