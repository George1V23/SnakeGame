import os

from kivy.core.window import Window
from kivy.metrics import dp
from kivy.utils import platform

# Whole-number scale from screen density (1 on a normal desktop, ~3 on a phone). Keeping it an integer keeps
# every grid size exact, so collision edges that should just touch never overlap by a rounding error.
UI_SCALE = max(1, round(dp(1)))
STEP = 25 * UI_SCALE  # grid cell size in pixels

# Touch controls (swipe, D-pad, on-screen Pause/Sound). SNAKE_TOUCH=1 enables them on desktop for testing.
IS_TOUCH = platform in ('android', 'ios') or os.environ.get("SNAKE_TOUCH") == "1"


def field_size():
    """Playfield in pixels: whole grid cells only, so wrapping around the edges stays on the grid."""
    width = Window.width if Window and Window.width > 0 else 800
    height = Window.height if Window and Window.height > 0 else 600
    return max(STEP, width // STEP * STEP), max(STEP, height // STEP * STEP)
