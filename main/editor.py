from kivy.core.window import Window
from kivy.graphics import Color, InstructionGroup, Line, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton

from levels import CUSTOM_SLOTS, MAZES, maze_walls
from tiles import TILE_COLORS, tile_group

BOARD_COLOR = (0.2, 0.5, 0.5, 1)  # same as the game board in drawing.kv
BAR_HEIGHT = 34
TOOLS = [  # (tile kind, button label)
    ('wall', "Wall"),
    ('food', "Food"),
    ('bonus', "Bonus"),
    ('slow', "Slow"),
    ('shrink', "Shrink"),
    ('ghost', "Ghost"),
    ('deco', "Decor"),
    ('start', "Start"),
]
MAX_UNDO = 200


# Bar with a dark translucent background
class _Bar(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='horizontal', spacing=3, padding=2,
                         size_hint=(1, None), height=BAR_HEIGHT, **kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 0.7)
            self._bg = Rectangle()
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size


# Full-screen grid editor for the custom level slots
class LevelEditor(FloatLayout):
    """
    Mouse: left = paint the selected tool (drag to paint walls), right = food, middle = erase (drag),
    wheel = change tool. Keys: 1-8 tools, Ctrl+Z undo, Tab hide/show the bars.
    """

    def __init__(self, records, on_play, on_menu, step=25, **kwargs):
        super().__init__(**kwargs)
        self.records = records
        self.on_play = on_play
        self.on_menu = on_menu
        self.step = step
        self.slot = CUSTOM_SLOTS[0]
        self.tool = 'wall'
        self.cells = {}      # (col, row) -> tile kind; one tile per cell
        self.start = None    # ((col, row), (dx, dy)) snake start, or None for a random safe spawn
        self.history = []    # undo strokes: [(key, old, new), ...]; key is a cell or 'start'
        self.stroke = None
        self.template_index = 0
        self._tiles = {}     # key -> InstructionGroup on the tile layer

        with self.canvas.before:
            Color(*BOARD_COLOR)
            self._bg = Rectangle()
        self._grid_layer = InstructionGroup()
        self._tile_layer = InstructionGroup()
        self._cursor_color = Color(1, 1, 1, 0)
        self._cursor = Line(width=1.5, rectangle=(0, 0, step, step))
        self.canvas.before.add(self._grid_layer)
        self.canvas.before.add(self._tile_layer)
        self.canvas.before.add(self._cursor_color)
        self.canvas.before.add(self._cursor)
        self.bind(pos=self._draw_board, size=self._draw_board)

        # Top bar: tool palette
        self.tool_bar = _Bar(pos_hint={'x': 0, 'top': 1})
        self.tool_buttons = {}
        for number, (kind, label) in enumerate(TOOLS, 1):
            btn = ToggleButton(text=f"{number} {label}", group='editor_tool', allow_no_selection=False,
                               font_size=14, bold=True, background_color=TILE_COLORS[kind][:3] + (1,))
            btn.bind(on_release=lambda b, k=kind: self.select_tool(k))
            self.tool_bar.add_widget(btn)
            self.tool_buttons[kind] = btn

        # Bottom bar: actions and mouse hints
        self.action_bar = _Bar(pos_hint={'x': 0, 'y': 0})
        self.slot_btn = self._action("", self.next_slot, (0.3, 0.3, 0.6, 1), 95)
        self.template_btn = self._action("", self.apply_next_template, (0.5, 0.35, 0.2, 1), 150)
        self._action("Undo", self.undo, (0.4, 0.4, 0.4, 1), 60)
        self._action("Clear", self.clear, (0.8, 0.3, 0.2, 1), 60)
        self._action("Play", lambda *a: self.on_play(self.slot), (0.2, 0.75, 0.3, 1), 60)
        self._action("Menu", lambda *a: self.on_menu(), (0.5, 0.5, 0.5, 1), 60)
        self.hint = Label(font_size=11, halign='left', valign='middle', color=(1, 1, 0.6, 1))
        self.hint.bind(size=self.hint.setter('text_size'))
        self.action_bar.add_widget(self.hint)

        self.add_widget(self.tool_bar)
        self.add_widget(self.action_bar)
        self.template_btn.text = f"Maze: {MAZES[self.template_index][0]}"

        Window.bind(mouse_pos=self._on_mouse_pos, on_key_down=self._on_key_down)
        self.select_tool('wall')

    def _action(self, text, callback, color, width):
        btn = Button(text=text, font_size=13, size_hint=(None, 1), width=width, background_color=color)
        btn.bind(on_release=lambda *a: callback())
        self.action_bar.add_widget(btn)
        return btn

    @property
    def active(self):
        return self.parent is not None

    # ---------- slots ----------

    def open(self, slot):
        """Load a slot for editing."""
        self.slot = slot
        level = self.records.load_level(slot)
        self.cells = level['cells']
        self.start = level['start']
        self.history = []
        self.slot_btn.text = f"Slot: {slot}"
        self._redraw_tiles()

    def save(self):
        self.records.save_level(self.slot, self.cells, self.start)

    def next_slot(self):
        index = CUSTOM_SLOTS.index(self.slot)
        self.open(CUSTOM_SLOTS[(index + 1) % len(CUSTOM_SLOTS)])

    # ---------- drawing ----------

    def _grid_size(self):
        # Window based, like the game board, so edited cells map 1:1 onto the playfield
        return max(1, int(Window.width // self.step)), max(1, int(Window.height // self.step))

    def _draw_board(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size
        cols, rows = self._grid_size()
        self._grid_layer.clear()
        self._grid_layer.add(Color(1, 1, 1, 0.08))
        for c in range(1, cols):
            self._grid_layer.add(Line(points=[c * self.step, 0, c * self.step, rows * self.step]))
        for r in range(1, rows):
            self._grid_layer.add(Line(points=[0, r * self.step, cols * self.step, r * self.step]))
        self._grid_layer.add(Color(1, 1, 1, 0.25))  # playfield edge (the snake wraps around it)
        self._grid_layer.add(Line(rectangle=(0, 0, cols * self.step, rows * self.step)))

    def _redraw_tiles(self):
        self._tile_layer.clear()
        self._tiles = {}
        for cell in self.cells:
            self._draw_tile(cell)
        self._draw_tile('start')

    def _draw_tile(self, key):
        group = self._tiles.pop(key, None)
        if group is not None:
            self._tile_layer.remove(group)
        if key == 'start':
            group = tile_group('start', self.start[0], self.step, self.start[1]) if self.start else None
        else:
            group = tile_group(self.cells[key], key, self.step) if key in self.cells else None
        if group is not None:
            self._tile_layer.add(group)
            self._tiles[key] = group

    def _on_mouse_pos(self, window, pos):
        if not self.active:
            return
        c, r = self._cell_of(pos)
        self._cursor.rectangle = (c * self.step, r * self.step, self.step, self.step)

    # ---------- editing ----------

    def select_tool(self, kind):
        self.tool = kind
        for k, btn in self.tool_buttons.items():
            btn.state = 'down' if k == kind else 'normal'
            btn.color = (1, 1, 0.3, 1) if k == kind else (1, 1, 1, 1)
        self._cursor_color.rgba = TILE_COLORS[kind][:3] + (1,)
        label = dict(TOOLS)[kind]
        self.hint.text = (f"Left: {label}   Right: Food   Middle: Erase\n"
                          f"Wheel / 1-8: tool   Ctrl+Z: undo   Tab: hide bars")

    def cycle_tool(self, offset):
        kinds = [k for k, _ in TOOLS]
        self.select_tool(kinds[(kinds.index(self.tool) + offset) % len(kinds)])

    def _cell_of(self, pos):
        return int(pos[0] // self.step), int(pos[1] // self.step)

    def _change(self, key, new):
        old = self.start if key == 'start' else self.cells.get(key)
        if old == new:
            return
        if self.stroke is not None:
            self.stroke.append((key, old, new))
        self._write(key, new)

    def _write(self, key, value):
        if key == 'start':
            self.start = value
        elif value is None:
            self.cells.pop(key, None)
        else:
            self.cells[key] = value
        self._draw_tile(key)

    def _apply(self, action, pos, first_touch):
        cell = self._cell_of(pos)
        cols, rows = self._grid_size()
        if not (0 <= cell[0] < cols and 0 <= cell[1] < rows):
            return
        on_start = self.start is not None and self.start[0] == cell
        if action == 'erase':
            self._change(cell, None)
            if on_start:
                self._change('start', None)
        elif action == 'start':
            if not first_touch:
                return
            if on_start:  # clicking the start again turns it 90 degrees counter-clockwise
                dx, dy = self.start[1]
                self._change('start', (cell, (-dy, dx)))
            else:
                self._change(cell, None)
                self._change('start', (cell, (1, 0)))
        else:
            self._change(cell, action)
            if on_start:
                self._change('start', None)

    def _begin_stroke(self):
        self.stroke = []

    def _end_stroke(self):
        if self.stroke:
            self.history.append(self.stroke)
            del self.history[:-MAX_UNDO]
            self.save()
        self.stroke = None

    def undo(self):
        if not self.history:
            return
        for key, old, _new in reversed(self.history.pop()):
            self._write(key, old)
        self.save()

    def clear(self):
        self._begin_stroke()
        for cell in list(self.cells):
            self._change(cell, None)
        self._change('start', None)
        self._end_stroke()

    def apply_next_template(self):
        """Replace the walls with a built-in maze (undoable); press again for the next maze."""
        name = MAZES[self.template_index][0]
        cols, rows = self._grid_size()
        maze = maze_walls(name, cols, rows)
        self._begin_stroke()
        for cell, kind in list(self.cells.items()):
            if kind == 'wall' and cell not in maze:
                self._change(cell, None)
        for cell in maze:
            self._change(cell, 'wall')
            if self.start and self.start[0] == cell:
                self._change('start', None)
        self._end_stroke()
        self.template_index = (self.template_index + 1) % len(MAZES)
        self.template_btn.text = f"Maze: {MAZES[self.template_index][0]}"

    # ---------- input ----------

    def _bars_hit(self, pos):
        return any(bar.parent is self and bar.collide_point(*pos) for bar in (self.tool_bar, self.action_bar))

    def on_touch_down(self, touch):
        if super().on_touch_down(touch) or self._bars_hit(touch.pos):
            return True
        button = getattr(touch, 'button', 'left')
        if button in ('scrollup', 'scrollleft'):
            self.cycle_tool(-1)
            return True
        if button in ('scrolldown', 'scrollright'):
            self.cycle_tool(1)
            return True

        action = {'middle': 'erase', 'right': 'food'}.get(button, self.tool)
        touch.ud['editor_action'] = action
        self._begin_stroke()
        self._apply(action, touch.pos, first_touch=True)
        return True

    def on_touch_move(self, touch):
        action = touch.ud.get('editor_action')
        if action is None:
            return super().on_touch_move(touch)
        if not self._bars_hit(touch.pos):
            self._apply(action, touch.pos, first_touch=False)
        return True

    def on_touch_up(self, touch):
        if touch.ud.get('editor_action') is None:
            return super().on_touch_up(touch)
        self._end_stroke()
        return True

    def _on_key_down(self, window, key, scancode=None, codepoint=None, modifiers=None):
        if not self.active:
            return False
        modifiers = modifiers or []
        if key == 122 and 'ctrl' in modifiers:  # Ctrl+Z
            self.undo()
            return True
        if key == 9:  # Tab toggles the bars to reach the cells beneath them
            for bar in (self.tool_bar, self.action_bar):
                if bar.parent is self:
                    self.remove_widget(bar)
                else:
                    self.add_widget(bar)
            return True
        if codepoint and codepoint.isdigit() and 1 <= int(codepoint) <= len(TOOLS):
            self.select_tool(TOOLS[int(codepoint) - 1][0])
            return True
        return False
