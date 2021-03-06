print('importing...')
import pyaudio
import numpy as np
from numpy.fft import rfft
import scipy.signal
from time import sleep
from threading import Lock
import wave
try:
    from harmonicSynth import HarmonicSynth, Harmonic
    from blindDescend import blindDescend
    from yin import yin
    from streamProfiler import StreamProfiler
except ImportError as e:
    module_name = str(e).split('No module named ', 1)[1].strip().strip('"\'')
    print(f'Missing module {module_name}. Please download at')
    print(f'https://github.com/Daniel-Chin/Python_Lib/blob/master/{module_name}.py')
    input('Press Enter to quit...')
    raise e

PAGE_LEN = 512
# PAGE_LEN = 1024
N_HARMONICS = 60
STUPID_MATCH = True
USE_HANN = True
AUTOTUNE = True
DO_SWIPE = False
CROSSFADE_LEN = .3
STRICT_HARMO = True

WRITE_FILE = None
# import random
# WRITE_FILE = f'demo.wav'

SR = 22050
DTYPE = (np.int16, pyaudio.paInt16)
DTYPE = (np.int32, pyaudio.paInt32)
# DTYPE = (np.float32, pyaudio.paFloat32)
TWO_PI = np.pi * 2
IMAGINARY_LADDER = np.linspace(0, TWO_PI * 1j, PAGE_LEN)
HANN = scipy.signal.get_window('hann', PAGE_LEN, True)

def findPeaks(energy):
    slope = np.sign(energy[1:] - energy[:-1])
    extrema = slope[1:] - slope[:-1]
    return np.argpartition(
        (extrema == -2) * energy[1:-1], - N_HARMONICS,
    )[- N_HARMONICS:] + 1

def sft(signal, freq_bin):
    # Slow Fourier Transform
    return np.abs(np.sum(signal * np.exp(IMAGINARY_LADDER * freq_bin))) / PAGE_LEN

def refineGuess(guess, signal):
    def loss(x):
        if x < 0:
            return 0
        return - sft(signal, x)
    freq_bin, loss = blindDescend(loss, .01, .4, guess)
    return freq_bin * SR / PAGE_LEN, - loss

streamOutContainer = []
terminate_flag = 0
terminateLock = Lock()
synth = None
profiler = StreamProfiler(PAGE_LEN / SR)

def main():
    global terminate_flag, synth, f
    print('main')
    terminateLock.acquire()
    synth = HarmonicSynth(
        N_HARMONICS, SR, PAGE_LEN, DTYPE[0], STUPID_MATCH, 
        DO_SWIPE, CROSSFADE_LEN, 
    )
    pa = pyaudio.PyAudio()
    if WRITE_FILE is None:
        streamOutContainer.append(pa.open(
            format = DTYPE[1], channels = 1, rate = SR, 
            output = True, frames_per_buffer = PAGE_LEN,
        ))
    else:
        f = wave.open(WRITE_FILE, 'wb')
        f.setnchannels(1)
        f.setsampwidth(4)
        f.setframerate(SR)
    streamIn = pa.open(
        format = DTYPE[1], channels = 1, rate = SR, 
        input = True, frames_per_buffer = PAGE_LEN,
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
        if WRITE_FILE is None:
            streamOutContainer[0].stop_stream()
            streamOutContainer[0].close()
        else:
            f.close()
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

        if sample_count > PAGE_LEN:
            print('Discarding audio page!')
            in_data = in_data[-PAGE_LEN:]

        profiler.gonna('hann')
        raw_page = np.frombuffer(
            in_data, dtype = DTYPE[0]
        )
        if USE_HANN:
            page = HANN * raw_page
        else:
            page = raw_page
        
        if STRICT_HARMO:
            profiler.gonna('yin')
            f0 = yin(page, SR, PAGE_LEN)
            f0_ = autotune(f0, 0)[0]
            profiler.gonna('sft')
            harmonics = [
                Harmonic(f0_ * i, sft(page, f0 * i * PAGE_LEN / SR)) 
                for i in range(1, 1 + N_HARMONICS)
            ]
        else:
            profiler.gonna('fft')
            energy = np.abs(rfft(page))
            profiler.gonna('sft')
            harmonics = [
                Harmonic(*autotune(*refineGuess(x, page))) for x, _ in 
                zip(findPeaks(energy), range(N_HARMONICS))
            ]
        profiler.gonna('eat')
        synth.eat(harmonics)

        profiler.gonna('mix')
        mixed = synth.mix()
        if WRITE_FILE is None:
            streamOutContainer[0].write(mixed, PAGE_LEN)
        else:
            f.writeframes(mixed)

        profiler.display(same_line=True)
        profiler.gonna('idle')
        return (None, pyaudio.paContinue)
    except:
        terminateLock.release()
        import traceback
        traceback.print_exc()
        return (None, pyaudio.paAbort)

def autotune(freq, mag):
    if not AUTOTUNE:
        return freq, mag
    pitch = np.log(freq) * 17.312340490667562 - 36.37631656229591
    return np.exp((round(pitch) + 36.37631656229591) * 0.05776226504666211), mag

main()
