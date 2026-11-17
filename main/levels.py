# Classic-style campaign: each level has a maze layout (wall cells on the snake's grid) and a faster speed.
# After the last layout the mazes repeat, while the speed keeps increasing up to FASTEST_INTERVAL.

FOODS_PER_LEVEL = 10
BASE_INTERVAL = 0.3     # seconds per move on level 1
FASTEST_INTERVAL = 0.07
SPEED_FACTOR = 0.88     # each level moves ~12% faster


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


def _four_rooms(cols, rows):
    """Closed box split by a cross; each inner wall has a passage in the middle of every room side."""
    inner_v = {(cols // 2, r) for r in range(rows) if abs(r - rows // 4) > 1 and abs(r - 3 * rows // 4) > 1}
    inner_h = {(c, rows // 2) for c in range(cols) if abs(c - cols // 4) > 1 and abs(c - 3 * cols // 4) > 1}
    return _border(cols, rows) | inner_v | inner_h


LEVELS = [
    ("Open Field", _open_field),
    ("The Box", _the_box),
    ("Tunnels", _tunnels),
    ("Crossroads", _crossroads),
    ("Doorways", _doorways),
    ("Four Rooms", _four_rooms),
]


def level_name(level):
    return LEVELS[(level - 1) % len(LEVELS)][0]


def level_walls(level, cols, rows):
    """Set of (col, row) grid cells occupied by walls on this level."""
    return LEVELS[(level - 1) % len(LEVELS)][1](cols, rows)


def level_interval(level):
    return max(FASTEST_INTERVAL, BASE_INTERVAL * SPEED_FACTOR ** (level - 1))
