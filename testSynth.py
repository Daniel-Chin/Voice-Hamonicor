import pyaudio
import numpy as np
from harmonicSynth import HarmonicSynth, Harmonic, TWO_PI
from threading import Thread
from time import sleep

# FRAME_LEN = 11050
FRAME_LEN = 2048 * 2
SR = 22100
FRAME_TIME = FRAME_LEN / SR

DTYPE = (np.float32, pyaudio.paFloat32)

def onAudioOut(_, sample_count, *__):
    s.eat(hs)
    signal = s.mix()
    if sample_count != signal.size:
        print('Error 3498qfgj5', sample_count, signal.size)
        return (None, pyaudio.paAbort)
    return (signal, pyaudio.paContinue)

def main():
    global s, hs
    s = HarmonicSynth(1, SR, FRAME_LEN, DTYPE[0], True, True, .02)
    hs = [Harmonic(220, 1) for _ in range(1)]
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format = DTYPE[1], channels = 1, rate = SR, 
        output = True, frames_per_buffer = FRAME_LEN,
        stream_callback = onAudioOut, 
    )
    stream.start_stream()
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
