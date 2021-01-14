import numpy as np
from collections import namedtuple

TWO_PI = np.pi * 2

Harmonic = namedtuple('Harmonic', ['freq', 'mag'])

class Synth:
    def __init__(
        self, n_harmonics, FRAME_LEN, DTYPE, STUPID_MATCH, 
        DO_SWIPE, 
    ):
        self.FRAME_LEN = FRAME_LEN
        self.STUPID_MATCH = STUPID_MATCH
        self.DO_SWIPE = DO_SWIPE
        self.signal_2d = np.zeros((n_harmonics, FRAME_LEN), DTYPE)
        self.harmonics = [
            Harmonic(261.63, 0) for i in range(n_harmonics)
        ]
        self.osc = [Osc(
            i, self, h
        ) for i, h in enumerate(self.harmonics)]
    
    def mix(self):
        return np.sum(self.signal_2d, 0)
    
    def getMag(self, harmonic):
        return harmonic.mag

    def eat(self, harmonics):
        if self.STUPID_MATCH:
            [osc.eat(*h, self.DO_SWIPE) for osc, h in zip(self.osc, harmonics)]

class Osc():
    def __init__(self, i, synth, harmonic):
        self.LINEAR = np.arange(synth.FRAME_LEN + 1) * TWO_PI
        self.freq = harmonic.freq
        self.mag = harmonic.mag
        self.phase = 0
        self.i = i
        self.synth = synth
    
    def eat(self, new_freq, new_mag, swipe = True):
        if swipe:
            tau = self.LINEAR * np.linspace(
                self.freq, new_freq, self.synth.FRAME_LEN + 1
            )
        else:
            tau = self.LINEAR * new_freq
        self.synth.signal_2d[self.i] = np.sin(
            tau[:-1] + self.phase
        ) * np.linspace(self.mag, new_mag, self.synth.FRAME_LEN)
        self.freq = new_freq
        self.mag = new_mag
        self.phase = (tau[-1] + self.phase) % TWO_PI
