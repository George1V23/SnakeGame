from kivy.metrics import dp, sp
from kivy.uix.button import Button
from kivy.uix.relativelayout import RelativeLayout

# (direction, label, (column, row) in the 3x3 pad)
PAD_BUTTONS = [
    ((0, 1), "Up", (1, 2)),
    ((-1, 0), "Left", (0, 1)),
    ((1, 0), "Right", (2, 1)),
    ((0, -1), "Down", (1, 0)),
]


# Translucent on-screen direction pad; holding a direction boosts like holding a key
class DPad(RelativeLayout):
    def __init__(self, on_press_direction, on_release_direction, **kwargs):
        size = dp(150)
        super().__init__(size_hint=(None, None), size=(size, size), **kwargs)
        cell = size / 3
        for move, label, (col, row) in PAD_BUTTONS:
            btn = Button(text=label, font_size=sp(13), bold=True,
                         size_hint=(None, None), size=(cell, cell), pos=(col * cell, row * cell),
                         background_normal='', background_color=(1, 1, 1, 0.22))
            btn.bind(on_press=lambda b, m=move: on_press_direction(m),
                     on_release=lambda b: on_release_direction())
            self.add_widget(btn)
