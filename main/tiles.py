import random

from kivy.graphics import Color, Ellipse, InstructionGroup, Rectangle, Triangle

# Colors shared by the game board and the Level Editor
TILE_COLORS = {
    'wall': (0.45, 0.3, 0.15, 1),
    'food': (1, 0, 0, 0.45),
    'bonus': (1, 0.8, 0.1, 0.9),
    'slow': (0.2, 0.6, 1, 0.9),
    'shrink': (0.2, 1, 0.9, 0.9),
    'ghost': (0.8, 0.4, 1, 0.9),
    'deco': (0.9, 0.9, 0.9, 1),  # editor button only; each decoration gets its own color
    'start': (0.2, 0.9, 0.4, 1),
}
POWER_KINDS = ('slow', 'shrink', 'ghost')


def deco_color(cell):
    """Stable 'paint brush' color per cell, so decorations look the same every time they are drawn."""
    rnd = random.Random(cell[0] * 7919 + cell[1])
    return rnd.random(), rnd.random(), rnd.random(), 1


def tile_group(kind, cell, step, direction=(1, 0)):
    """Canvas instructions drawing one custom-level tile in its grid cell."""
    x, y = cell[0] * step, cell[1] * step
    cx, cy = x + step / 2, y + step / 2
    group = InstructionGroup()
    if kind == 'wall':
        group.add(Color(*TILE_COLORS['wall']))
        group.add(Rectangle(pos=(x, y), size=(step, step)))
    elif kind == 'deco':
        group.add(Color(*deco_color(cell)))
        group.add(Triangle(points=[x + 4, y + 4, x + step - 4, y + 4, cx, y + step - 4]))
    elif kind == 'start':
        # arrow pointing in the snake's starting direction
        dx, dy = direction
        r = step / 2 - 2
        group.add(Color(*TILE_COLORS['start']))
        group.add(Triangle(points=[cx + dx * r, cy + dy * r,
                                   cx - dx * r - dy * r, cy - dy * r + dx * r,
                                   cx - dx * r + dy * r, cy - dy * r - dx * r]))
    else:  # food, bonus and power-ups
        radius = 7 if kind == 'food' else 9
        group.add(Color(*TILE_COLORS[kind][:3], 0.95))
        group.add(Ellipse(pos=(cx - radius, cy - radius), size=(radius * 2, radius * 2)))
        if kind in POWER_KINDS:
            group.add(Color(1, 1, 1, 0.9))
            group.add(Ellipse(pos=(cx - 3, cy - 3), size=(6, 6)))
    return group
