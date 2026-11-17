# Classic-style mazes (wall cells on the snake's grid) and Snake II-style speed levels 1-9.
# Campaign mode plays the mazes in order, one speed level faster each time; after the last maze they repeat.
# Single-maze mode is the classic endless game on one maze at a fixed speed.

FOODS_PER_LEVEL = 10
MAX_SPEED = 9
SLOWEST_INTERVAL = 0.32  # seconds per move at speed 1
SPEED_FACTOR = 0.82      # each speed level moves ~18% faster (speed 9 ~ 0.065s)
CAMPAIGN = "Campaign"


def _hbar(row, c0, c1, gap=0):
    mid = (c0 + c1) // 2
    return {(c, row) for c in range(c0, c1) if not (gap and abs(c - mid) < gap)}


def _vbar(col, r0, r1, gap=0):
    mid = (r0 + r1) // 2
    return {(col, r) for r in range(r0, r1) if not (gap and abs(r - mid) < gap)}


def _border(cols, rows, door=0):
    """Walls around the playfield; `door` opens a gap in the middle of each side so the snake can wrap."""
    return (_hbar(0, 0, cols, door) | _hbar(rows - 1, 0, cols, door) |
            _vbar(0, 0, rows, door) | _vbar(cols - 1, 0, rows, door))


def _open_field(cols, rows):
    return set()


def _the_box(cols, rows):
    return _border(cols, rows)


def _tunnels(cols, rows):
    return (_hbar(rows // 3, cols // 5, cols - cols // 5) |
            _hbar(rows - 1 - rows // 3, cols // 5, cols - cols // 5))


def _crossroads(cols, rows):
    return (_vbar(cols // 2, rows // 5, rows - rows // 5, gap=2) |
            _hbar(rows // 2, cols // 5, cols - cols // 5, gap=2))


def _doorways(cols, rows):
    return _border(cols, rows, door=3) | _tunnels(cols, rows)


def _apartment(cols, rows):
    """Closed box split by a cross; each inner wall has a passage in the middle of every room side."""
    inner_v = {(cols // 2, r) for r in range(rows) if abs(r - rows // 4) > 1 and abs(r - 3 * rows // 4) > 1}
    inner_h = {(c, rows // 2) for c in range(cols) if abs(c - cols // 4) > 1 and abs(c - 3 * cols // 4) > 1}
    return _border(cols, rows) | inner_v | inner_h


def _mill(cols, rows):
    """Pinwheel of four hooked arms around an open centre (Snake Xenzia's 'Mill')."""
    cx, cy = cols // 2, rows // 2
    arm = max(3, rows // 2 - 3)
    hook = arm // 2
    base = [(1, k) for k in range(2, arm + 1)] + [(-j, arm) for j in range(1, hook + 1)]
    cells = set()
    for dx, dy in base:
        for _ in range(4):  # rotate each arm cell by 90 degrees around the centre
            cells.add((cx + dx, cy + dy))
            dx, dy = -dy, dx
    return cells


def _rails(cols, rows):
    """Long horizontal rails, alternately open on the right and left, forming a zig-zag track."""
    spacing = max(3, rows // 6)
    gap = 5
    cells = set()
    for i, r in enumerate(range(spacing, rows - 1, spacing)):
        cells |= _hbar(r, 0, cols - gap) if i % 2 == 0 else _hbar(r, gap, cols)
    return cells


MAZES = [
    ("Open Field", _open_field),
    ("The Box", _the_box),
    ("Tunnels", _tunnels),
    ("Mill", _mill),
    ("Rails", _rails),
    ("Apartment", _apartment),
    ("Crossroads", _crossroads),
    ("Doorways", _doorways),
]
MAZE_CHOICES = [CAMPAIGN] + [name for name, _ in MAZES]


def level_name(level):
    return MAZES[(level - 1) % len(MAZES)][0]


def maze_walls(name, cols, rows):
    """Set of (col, row) grid cells occupied by walls in the named maze."""
    return dict(MAZES)[name](cols, rows)


def speed_interval(speed):
    """Seconds per move for a speed level 1..MAX_SPEED."""
    return SLOWEST_INTERVAL * SPEED_FACTOR ** (min(MAX_SPEED, max(1, speed)) - 1)
