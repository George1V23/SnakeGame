import random

from kivy.graphics import Color, Ellipse, InstructionGroup, Rectangle, Triangle

# Colors shared by the game board and the Level Editor, chosen to match what each tile does
TILE_COLORS = {
    'wall': (0.45, 0.3, 0.15, 1),    # brown brick: blocks the snake
    'food': (1, 0, 0, 0.45),         # red apple: grow
    'bonus': (1, 0.8, 0.1, 0.9),     # gold: extra points
    'slow': (0.2, 0.6, 1, 0.9),      # cold blue: slow motion
    'shrink': (0.2, 1, 0.9, 0.9),    # cyan: cut the tail
    'ghost': (0.8, 0.4, 1, 0.9),     # spectral purple: pass through walls
    'grass': (0.25, 0.65, 0.15, 1),  # green: slows the snake while it crawls through
    'start': (0.95, 0.95, 0.95, 1),  # white marker: where the snake starts
}
POWER_KINDS = ('slow', 'shrink', 'ghost')
GRASS_BLADES = 6


def tile_group(kind, cell, step, direction=(1, 0)):
    """Canvas instructions drawing one custom-level tile in its grid cell."""
    x, y = cell[0] * step, cell[1] * step
    cx, cy = x + step / 2, y + step / 2
    group = InstructionGroup()
    if kind == 'wall':
        group.add(Color(*TILE_COLORS['wall']))
        group.add(Rectangle(pos=(x, y), size=(step, step)))
    elif kind == 'grass':
        _add_grass(group, cell, x, y, step)
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


def _add_grass(group, cell, x, y, step):
    """A soil-green patch with thin leaning blades; seeded per cell so it looks the same on every redraw."""
    rnd = random.Random(cell[0] * 7919 + cell[1])
    r, g, b, _ = TILE_COLORS['grass']
    group.add(Color(r * 0.6, g * 0.6, b * 0.6, 0.55))
    group.add(Rectangle(pos=(x, y), size=(step, step)))
    for i in range(GRASS_BLADES):
        base_x = x + 2 + (step - 4) * (i + rnd.uniform(0.1, 0.9)) / GRASS_BLADES
        half_width = rnd.uniform(1.0, 1.8)
        height = rnd.uniform(step * 0.45, step * 0.9)
        lean = rnd.uniform(-step * 0.18, step * 0.18)
        shade = rnd.uniform(0.8, 1.25)
        group.add(Color(min(1, r * shade), min(1, g * shade), min(1, b * shade), 1))
        group.add(Triangle(points=[base_x - half_width, y + 1, base_x + half_width, y + 1,
                                   base_x + lean, y + 1 + height]))
