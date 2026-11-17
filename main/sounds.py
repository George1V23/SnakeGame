import os
import struct
import wave

from kivy.core.audio import SoundLoader

from records import data_dir

RATE = 22050
VOLUME = 0.2
# Monophonic beeps in the spirit of the Nokia games: name -> [(frequency Hz, seconds), ...]
TONES = {
    "eat": [(880, 0.05)],
    "bonus": [(660, 0.05), (990, 0.09)],
    "power": [(523, 0.05), (659, 0.05), (784, 0.09)],
    "level": [(523, 0.08), (659, 0.08), (784, 0.08), (1047, 0.16)],
    "over": [(392, 0.12), (330, 0.12), (262, 0.28)],
}


def _write_wav(path, notes):
    """Write a square-wave melody, with a short fade per note to avoid clicks."""
    frames = bytearray()
    amplitude = int(32767 * VOLUME)
    for freq, seconds in notes:
        count = int(RATE * seconds)
        fade = min(200, count // 4)
        half_period = RATE / (2 * freq)
        for i in range(count):
            level = min(1.0, i / fade, (count - i) / fade) if fade else 1.0
            sign = 1 if int(i / half_period) % 2 == 0 else -1
            frames += struct.pack("<h", int(sign * amplitude * level))
    with wave.open(path, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(bytes(frames))


# Generated sound effects (no audio assets needed); silently disabled if no audio provider exists
class Sounds:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self._sounds = {}
        folder = os.path.join(data_dir(), "sounds")
        os.makedirs(folder, exist_ok=True)
        for name, notes in TONES.items():
            path = os.path.join(folder, f"{name}.wav")
            if not os.path.exists(path):
                _write_wav(path, notes)
            self._sounds[name] = SoundLoader.load(path)

    def play(self, name):
        sound = self._sounds.get(name)
        if self.enabled and sound:
            sound.stop()
            sound.play()
