import pyaudio
import numpy as np
from harmonicSynth import Synth, Harmonic, TWO_PI
from threading import Thread
from time import sleep

FRAME_LEN = 1024
# FRAME_LEN = 2048*4
SR = 22100
FRAME_TIME = FRAME_LEN / SR

DTYPE = (np.float32, pyaudio.paFloat32)

class MyT(Thread):
    def run(self):
        while True:
            self.s.eat(self.hs)
            signal = self.s.mix()
            # signal = DTYPE[0](np.sin(np.arange(FRAME_LEN) * TWO_PI * 220 / SR))
            try:
                self.stream.write(signal, FRAME_LEN)
            except OSError:
                print('thread exits')
                return
            sleep(FRAME_TIME)

def main():
    s = Synth(3, SR, FRAME_LEN, DTYPE[0], True, True)
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format = DTYPE[1], channels = 1, rate = SR, 
        output = True, frames_per_buffer = FRAME_LEN,
    )
    hs = [Harmonic(220, 1) for _ in range(3)]
    thread = MyT()
    thread.hs = hs
    thread.s = s
    thread.stream = stream
    thread.start()
    try:
        from console import console
        console({**locals(), **globals()})
    finally:
        print('Releasing resources... ')
        stream.stop_stream()
        stream.close()
        pa.terminate()
        print('Resources released. ')

main()
