import numpy as np
from numpy.fft import rfft
import scipy.signal
from collections import namedtuple
from time import sleep
try:
    from blindDescend import blindDescend
except ImportError:
    print('Missing module "blindDescend". Please download at')
    print('https://github.com/Daniel-Chin/Python_Lib/blob/master/blindDescend.py')
    input('Press Enter to quit...')

FRAME_LEN = 1024
STUPID_MATCH = True

SR = 44100
DTYPE = (np.float32, pyaudio.paFloat32)
TWO_PI = np.pi * 2
IMAGINARY_LADDER = np.linspace(0, TWO_PI * j, FRAME_LEN)
HANN = scipy.signal.get_window('hann', FRAME_LEN, True)

Harmonic = namedtuple('Harmonic', ['freq', 'mag'])

class Synth:
    def __init__(self, n_harmonics):
        self.signal_2d = np.zeros((n_harmonics, FRAME_LEN), DTYPE[0])
        self.harmonics = [
            Harmonic(261.63, 0) for i in range(n_harmonics)
        ]
        self.osc = [Osc(
            i, self.signal_2d, h
        ) for i, h in enumerate(self.harmonics)]
    
    def mix(self):
        return np.sum(self.signal_2d, 0)
    
    def getMag(self, harmonic):
        return harmonic.mag

    def eat(self, harmonics):
        if STUPID_MATCH:
            harmonics.sort(self.getMag)
            [osc.eat(h) for osc, h in zip(self.osc, harmonics)]

class Osc():
    def __init__(self, i, signal_2d, harmonic):
        self.LINEAR = np.arange(FRAME_LEN + 1) * TWO_PI
        self.freq = harmonic.freq
        self.mag = harmonic.mag
        self.phase = 0
        self.i = i
        self.signal_2d = signal_2d
    
    def eat(self, new_freq, new_mag, swipe = True):
        if swipe:
            tau = self.LINEAR * np.linspace(self.freq, new_freq, FRAME_LEN + 1)
        else:
            tau = self.LINEAR * new_freq
        self.signal_2d[self.i] = np.sin(
            tau[:-1] + self.phase
        ) * np.linspace(self.mag, new_mag, FRAME_LEN)
        self.freq = new_freq
        self.mag = new_mag
        self.phase = (tau[-1] + self.phase) % TWO_PI

def findPeaks(energy):
    slope = np.sign(energy[1:] - energy[:-1])
    extrema = slope[1:] - slope[:-1]
    energy = energy[1:-1]
    return reversed(np.argsort(energy[extrema == -2]) + 1)

def sft(signal, freq_bin):
    # Slow Fourier Transform
    return np.abs(np.sum(signal * np.exp(IMAGINARY_LADDER * freq_bin))) / FRAME_LEN

def refineGuess(guess, signal):
    def loss(x):
        return - sft(signal, x)
    return blindDescend(loss, .01, .4, guess)

streamOutContainer = []
terminate_flag = 0
terminateLock = Lock()

def main():
    global terminate_flag
    terminateLock.acquire()
    pa = pyaudio.PyAudio()
    streamOutContainer.append(pa.open(
        format = DTYPE[1], channels = 1, rate = SR, 
        output = True, frames_per_buffer = FRAME_LEN,
    ))
    streamIn = pa.open(
        format = DTYPE[1], channels = 1, rate = SR, 
        input = True, frames_per_buffer = FRAME_LEN,
        stream_callback = onAudioIn, 
    )
    streamIn.start_stream()
    try:
        while streamIn.is_active():
            sleep(10)
    except KeyboardInterrupt:
        print('Ctrl+C received. Shutting down. ')
    finally:
        print('Releasing resources... ')
        terminate_flag = 1
        terminateLock.acquire()
        terminateLock.release()
        streamOutContainer[0].stop_stream()
        streamOutContainer[0].close()
        while streamIn.is_active():
            sleep(.1)   # not perfect
        streamIn.stop_stream()
        streamIn.close()
        pa.terminate()
        print('Resources released. ')

def onAudioIn(in_data, sample_count, *_):
    global terminate_flag

    try:
        if terminate_flag == 1:
            terminate_flag = 2
            terminateLock.release()
            print('PA handler terminating. ')
            # Sadly, there is no way to notify main thread after returning. 
            return (None, pyaudio.paComplete)

        if sample_count > FRAME_LEN:
            print('Discarding audio frame!')
            in_data = in_data[-FRAME_LEN:]

        frame = np.frombuffer(
            in_data, dtype = DTYPE[0]
        )

        streamOutContainer[0].write(frame_out, FRAME_LEN)
        return (None, pyaudio.paContinue)
    except:
        terminateLock.release()
        import traceback
        traceback.print_exc()
        return (None, pyaudio.paAbort)

main()
