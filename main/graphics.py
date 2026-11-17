import os
import random
import time

from kivy.clock import Clock
from kivy.animation import Animation
from kivy.lang import Builder
from kivy.properties import BooleanProperty, NumericProperty
from kivy.uix.widget import Widget
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse

from snake import Snake, Square
from levels import FOODS_PER_LEVEL, level_interval, level_name, level_walls
from records import ScoreRecords

# Load kv file for widget visuals
try:
    Builder.load_file("drawing.kv")
except FileNotFoundError:
    kv_file = os.path.join(os.path.dirname(__file__), "drawing.kv")
    if os.path.exists(kv_file):
        Builder.load_file(kv_file)

BOOST_INTERVAL = 0.08   # move interval while a direction key is held
FOOD_POINTS = 10        # per regular food, multiplied by the level
LEVEL_CLEAR_POINTS = 50 # per level cleared, multiplied by the level
BONUS_EVERY = 4         # a timed bonus food appears after every 4 regular foods
BONUS_MOVES = 40        # bonus food lifetime counted in snake moves, so pausing freezes it
WALL_COLOR = [0.45, 0.3, 0.15]
LEVEL_START_DELAY = 0.7 # ignore keys briefly after a level change so a held key does not start it


# Create the PaintBrush widget class
class PaintBrush(Widget):
    pass


# Layout class where the game graphics, snake, obstacles, and food are drawn
class Graphics(RelativeLayout):
    edit_mode = BooleanProperty(False)
    is_paused = BooleanProperty(False)
    score = NumericProperty(0)
    level = NumericProperty(1)
    foods_eaten = NumericProperty(0)  # regular foods eaten in the current level
    best = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Bind keyboard methods to Window
        Window.bind(on_key_down=self.on_key_down, on_key_up=self.on_key_up)

        self.step = 25
        self.base_speed = level_interval(1)
        self.max_speed = BOOST_INTERVAL
        self.current_speed = self.base_speed
        self.active_key_direction = None
        self.speed_boost_event = None
        self.turns = []  # queued direction changes, applied one per move
        self.start_allowed_at = 0

        self.game_over = False
        self.game_over_label = None
        self.restart_button = None
        self.pause_label = None

        self.started = False

        self.snake = None
        self.head = None
        self.snakeTail = []
        self.obstacles = []  # user-placed in Edit Mode
        self.walls = []      # level maze
        self.foods = []
        self.brushes = []  # stores PaintBrush widgets so Edit Mode can remove/clear them
        self.start_label = None
        self.move_event = None

        self.records = ScoreRecords()
        self.best = self.records.best

        # Heads-up display with score / level / best
        self.hud = Label(
            font_size=18,
            bold=True,
            color=(1, 1, 1, 0.9),
            size_hint=(1, None),
            height=30,
            pos_hint={'x': 0, 'top': 1}
        )
        self.add_widget(self.hud)
        self.bind(score=self._update_hud, level=self._update_hud, foods_eaten=self._update_hud,
                  best=self._update_hud, edit_mode=self._update_hud)

        self.setup_game()

    # ---------- grid helpers ----------

    @staticmethod
    def _window_size():
        win_w = Window.width if Window and Window.width > 0 else 800
        win_h = Window.height if Window and Window.height > 0 else 600
        return win_w, win_h

    def _grid(self):
        win_w, win_h = self._window_size()
        return max(1, int(win_w // self.step)), max(1, int(win_h // self.step))

    def _cell_center(self, cell):
        return (cell[0] + 0.5) * self.step, (cell[1] + 0.5) * self.step

    def _cell_of(self, pos):
        return int(pos[0] // self.step), int(pos[1] // self.step)

    def _blocked_cells(self):
        return {self._cell_of(w.center) for w in self.walls + self.obstacles}

    # ---------- game / level setup ----------

    def setup_game(self):
        """Start a new run from level 1."""
        self.score = 0
        self.level = 1
        self._prepare_level()

    def restart_game(self, *args):
        self.setup_game()

    def _prepare_level(self, headline=""):
        """Reset the board and snake for the current level; the score is kept."""
        for widget in (self.start_label, self.game_over_label, self.restart_button, self.pause_label):
            if widget and widget in self.children:
                self.remove_widget(widget)
        self.start_label = None
        self.game_over_label = None
        self.restart_button = None
        self.pause_label = None

        self.game_over = False
        self.is_paused = False
        self.started = False
        self.foods_eaten = 0
        self.turns = []

        self.base_speed = level_interval(self.level)
        self.max_speed = min(BOOST_INTERVAL, self.base_speed)
        self.current_speed = self.base_speed
        self.active_key_direction = None
        self._stop_clocks()

        # Clean up existing snake widgets
        if self.head and self.head in self.children:
            self.remove_widget(self.head)
        for sq in self.snakeTail:
            if sq in self.children:
                self.remove_widget(sq)

        self._build_walls()

        # Drop generated food; food placed in Edit Mode stays until eaten or cleared
        for food in list(self.foods):
            if food['kind'] != 'custom':
                self._remove_food(food)

        # Linked list for snake body (composed of head and tail formed with squares)
        self.snake = Snake(step=self.step)
        self.head = self.snake.head.widget
        self.head.center, (self.direction, self.head.angle) = self._find_spawn()
        self.snake.position_initial_tail()

        # Attach 2 additional square objects to the snake tail (making 3 squares total)
        for _ in range(2):
            self.snake.grow()
        self.snakeTail = [node.widget for node in self.snake if node is not self.snake.head]
        for sq in self.snakeTail:
            self.add_widget(sq)
        self.add_widget(self.head)

        # Keep the HUD drawn above the board
        self.remove_widget(self.hud)
        self.add_widget(self.hud)
        self._update_hud()

        # Prompt label before the level starts (if not in edit mode)
        if not self.edit_mode:
            text = f"Level {self.level}: {level_name(self.level)}\n[size=28]press any key[/size]"
            if headline:
                text = f"[color=66ff88]{headline}[/color]\n" + text
            self.start_label = Label(
                text=text,
                markup=True,
                halign='center',
                font_size=40,
                color=(1, 1, 1, 1),
                pos_hint={'center_x': 0.5, 'center_y': 0.5}
            )
            self.add_widget(self.start_label)

    def _build_walls(self):
        for wall in self.walls:
            if wall in self.children:
                self.remove_widget(wall)
        self.walls = []
        cols, rows = self._grid()
        for cell in level_walls(self.level, cols, rows):
            # bulge fills the 5px gaps visually; the 20px collision box keeps neighbouring lanes free
            wall = Square(color=WALL_COLOR, show_collision_margin=False, bulge=(self.step - 20) / 2)
            wall.center = self._cell_center(cell)
            self.add_widget(wall)
            self.walls.append(wall)

    def _find_spawn(self):
        """Pick a cell and orientation with free room for the body behind and a runway ahead."""
        orientations = [
            ((0, 1), 0),
            ((-1, 0), 90),
            ((0, -1), 180),
            ((1, 0), 270),
        ]
        cols, rows = self._grid()
        blocked = self._blocked_cells()
        for _ in range(500):
            cell = (random.randrange(cols), random.randrange(rows))
            (dx, dy), angle = random.choice(orientations)
            path = {((cell[0] + dx * k) % cols, (cell[1] + dy * k) % rows) for k in range(-3, 7)}
            if not path & blocked:
                return self._cell_center(cell), ((dx, dy), angle)
        return self._cell_center((cols // 2, rows // 2)), random.choice(orientations)

    def _update_hud(self, *args):
        self.hud.opacity = 0 if self.edit_mode else 1
        self.hud.text = (
            f"Score: {self.score}     Level {self.level}: {level_name(self.level)}     "
            f"Food: {self.foods_eaten}/{FOODS_PER_LEVEL}     Best: {max(self.best, self.score)}"
        )

    def _stop_clocks(self):
        if self.move_event:
            Clock.unschedule(self.move_event)
            self.move_event = None
        if self.speed_boost_event:
            Clock.unschedule(self.speed_boost_event)
            self.speed_boost_event = None

    def clear_environment(self):
        """Clear all editable environment objects: obstacles, food, and PaintBrush marks."""
        for obs in list(self.obstacles):
            if obs in self.children:
                self.remove_widget(obs)
        self.obstacles.clear()

        # Remove all PaintBrush widgets created by mouse scrolling in Edit Mode.
        for brush in list(self.brushes):
            if brush in self.children:
                self.remove_widget(brush)
        self.brushes.clear()

        for food in list(self.foods):
            self._remove_food(food)

    # ---------- food ----------

    def _spawn_food(self, center, kind='normal'):
        """Draw a pulsating food circle. kind: 'normal' / 'custom' (red) or 'bonus' (gold, timed)."""
        cx, cy = center
        min_size, max_size = (18, 34) if kind == 'bonus' else (12, 28)
        min_pos = (cx - min_size / 2.0, cy - min_size / 2.0)
        max_pos = (cx - max_size / 2.0, cy - max_size / 2.0)

        with self.canvas.after:
            color = Color(1, 0.8, 0.1, 0.9) if kind == 'bonus' else Color(1, 0, 0, 0.45)
            ellipse = Ellipse(pos=min_pos, size=(min_size, min_size))

        # Animate the ellipse size around the same center to create a pulsating effect.
        duration = 0.25 if kind == 'bonus' else 0.5
        anim = (
            Animation(size=(max_size, max_size), pos=max_pos, duration=duration, t='in_out_sine') +
            Animation(size=(min_size, min_size), pos=min_pos, duration=duration, t='in_out_sine')
        )
        anim.repeat = True
        anim.start(ellipse)

        food = {'center': (cx, cy), 'drawelement': (color, ellipse), 'kind': kind}
        if kind == 'bonus':
            food['moves_left'] = BONUS_MOVES
        self.foods.append(food)
        return food

    def _spawn_random_food(self, kind='normal'):
        """Place food on a random free grid cell (not on walls, obstacles, the snake, or other food)."""
        cols, rows = self._grid()
        blocked = (self._blocked_cells() |
                   {self._cell_of(node.widget.center) for node in self.snake} |
                   {self._cell_of(food['center']) for food in self.foods})
        free = [(c, r) for c in range(cols) for r in range(rows) if (c, r) not in blocked]
        if free:
            self._spawn_food(self._cell_center(random.choice(free)), kind)

    def _remove_food(self, food):
        color, ellipse = food['drawelement']
        Animation.cancel_all(ellipse)
        self.canvas.after.remove(color)
        self.canvas.after.remove(ellipse)
        if food in self.foods:
            self.foods.remove(food)

    def _ensure_food(self):
        if not any(food['kind'] != 'bonus' for food in self.foods):
            self._spawn_random_food('normal')

    def _tick_bonus_food(self):
        """Count down bonus food lifetime; it blinks before disappearing."""
        for food in [f for f in self.foods if f['kind'] == 'bonus']:
            food['moves_left'] -= 1
            if food['moves_left'] <= 0:
                self._remove_food(food)
            elif food['moves_left'] <= 10:
                food['drawelement'][0].a = 0.9 if food['moves_left'] % 2 else 0.2

    # ---------- game flow ----------

    def toggle_pause(self):
        """Toggle pause mode when pressing 'P'."""
        if self.game_over or not self.started:
            return
        self.is_paused = not self.is_paused
        if self.is_paused:
            if self.move_event:
                Clock.unschedule(self.move_event)
                self.move_event = None
            if not self.pause_label:
                self.pause_label = Label(
                    text="PAUSED\nPress 'P' to resume",
                    font_size=36,
                    color=(1, 1, 0, 1),
                    halign='center',
                    pos_hint={'center_x': 0.5, 'center_y': 0.5}
                )
                self.add_widget(self.pause_label)
        else:
            if self.pause_label:
                if self.pause_label in self.children:
                    self.remove_widget(self.pause_label)
                self.pause_label = None
            if not self.move_event:
                self.move_event = Clock.schedule_interval(self.move_step, self.current_speed)

    def start_game(self, move=None):
        """Start the prepared level; return True if the snake is now moving."""
        if self.started or self.game_over or time.monotonic() < self.start_allowed_at:
            return False
        self.started = True
        if self.start_label:
            if self.start_label in self.children:
                self.remove_widget(self.start_label)
            self.start_label = None
        if move and move != (0, 0):
            if not (move[0] == -self.direction[0] and move[1] == -self.direction[1]):
                self.set_direction(move)
        self._ensure_food()
        if not self.move_event and not self.is_paused:
            self.move_event = Clock.schedule_interval(self.move_step, self.current_speed)
        return True

    def set_direction(self, move):
        if move == (0, 1):
            self.head.angle = 0
            self.direction = move
        elif move == (-1, 0):
            self.head.angle = 90
            self.direction = move
        elif move == (0, -1):
            self.head.angle = 180
            self.direction = move
        elif move == (1, 0):
            self.head.angle = 270
            self.direction = move

    def set_speed(self, speed):
        if self.game_over or self.current_speed == speed:
            return
        self.current_speed = speed
        if self.move_event and not self.is_paused:
            Clock.unschedule(self.move_event)
            self.move_event = Clock.schedule_interval(self.move_step, self.current_speed)

    def _boost_speed(self, dt=0):
        if not self.game_over and self.active_key_direction is not None:
            self.set_speed(self.max_speed)

    @staticmethod
    def _widgets_collide(first, second):
        """Return True when two widgets' real rectangular bounds overlap."""
        if not first or not second:
            return False

        return (
            first.x < second.right and
            first.right > second.x and
            first.y < second.top and
            first.top > second.y
        )

    def check_obstacle_collision(self):
        """Check if snake head rectangle overlaps any wall or obstacle square rectangle."""
        if not self.head:
            return False
        return any(self._widgets_collide(self.head, obs) for obs in self.walls + self.obstacles)

    def check_food_collision(self):
        """Swallow any food the head reaches; the snake grows once the food is digested."""
        if not self.head:
            return

        for food in list(self.foods):
            cx, cy = food["center"]

            # Food collision uses the food circle center against the real head rectangle.
            if not (self.head.x <= cx <= self.head.right and self.head.y <= cy <= self.head.top):
                continue

            self._remove_food(food)
            self.snake.swallow()
            if food['kind'] == 'bonus':
                self.score += self.level * (20 + 2 * food['moves_left'])
                continue

            self.score += FOOD_POINTS * self.level
            self.foods_eaten += 1
            if self.foods_eaten % BONUS_EVERY == 0 and not any(f['kind'] == 'bonus' for f in self.foods):
                self._spawn_random_food('bonus')

        if self.foods_eaten >= FOODS_PER_LEVEL:
            self.level_complete()
        else:
            self._ensure_food()

    def level_complete(self):
        cleared = self.level
        self.score += LEVEL_CLEAR_POINTS * cleared
        self.level += 1
        self.start_allowed_at = time.monotonic() + LEVEL_START_DELAY
        self._prepare_level(headline=f"Level {cleared} clear!  +{LEVEL_CLEAR_POINTS * cleared}")

    def end_game(self):
        self.game_over = True
        if self.start_label and self.start_label in self.children:
            self.remove_widget(self.start_label)
            self.start_label = None
        self._stop_clocks()

        length = len(self.snake) + len(self.snake.meals)  # food still being digested counts
        rank = self.records.submit(self.score, self.level, length)
        self.best = self.records.best
        if rank == 1:
            headline = "NEW HIGH SCORE!"
        elif rank:
            headline = f"#{rank} in the records"
        else:
            headline = ""

        if not self.game_over_label:
            text = (f"Game Over\n[size=24]Score: {self.score}    Level: {self.level}    "
                    f"Length: {length}[/size]")
            if headline:
                text += f"\n[size=30][color=ffd633]{headline}[/color][/size]"
            text += "\n[size=16]ESC: menu[/size]"
            self.game_over_label = Label(
                text=text,
                markup=True,
                halign='center',
                font_size=50,
                color=(1, 0, 0, 1),
                pos_hint={'center_x': 0.5, 'center_y': 0.5}
            )
            self.add_widget(self.game_over_label)
        if not self.restart_button:
            self.restart_button = Button(
                text="Play Again",
                font_size=20,
                size_hint=(None, None),
                size=(150, 50),
                pos_hint={'right': 1, 'y': 0}
            )
            self.restart_button.bind(on_release=self.restart_game)
            self.add_widget(self.restart_button)

    def move_step(self, dt=0):
        if self.game_over or not self.started or self.is_paused:
            return
        if self.turns:
            self.set_direction(self.turns.pop(0))
        win_w, win_h = self._window_size()
        new_center_x = (self.head.center_x + self.direction[0] * self.step) % win_w
        new_center_y = (self.head.center_y + self.direction[1] * self.step) % win_h
        for node in self.snake.update_positions((new_center_x, new_center_y), self.current_speed):
            self.snakeTail.append(node.widget)
            self.add_widget(node.widget)

        # Check self collision, then walls/obstacles
        if self.snake.check_collision() or self.check_obstacle_collision():
            self.end_game()
            return

        self._tick_bonus_food()
        self.check_food_collision()

    # ---------- edit mode ----------

    def _remove_touch_graphics(self, touch):
        """Remove editable object under the cursor: obstacle, food, or PaintBrush."""
        tx, ty = touch.pos

        # Remove PaintBrush triangle near the middle-click position.
        for brush in list(self.brushes):
            if abs(brush.center_x - tx) < 25 and abs(brush.center_y - ty) < 25:
                if brush in self.children:
                    self.remove_widget(brush)
                self.brushes.remove(brush)

        # Remove obstacle square near the middle-click position.
        for obs in list(self.obstacles):
            if abs(obs.center_x - tx) < 20 and abs(obs.center_y - ty) < 20:
                if obs in self.children:
                    self.remove_widget(obs)
                self.obstacles.remove(obs)

        # Remove food circle near the middle-click position.
        for food in list(self.foods):
            cx, cy = food['center']
            if abs(cx - tx) < 20 and abs(cy - ty) < 20:
                self._remove_food(food)

    # Handle touch down / mouse click events
    def on_touch_down(self, touch):
        # Allow child UI widgets, such as Play Again, to process touch first.
        if super().on_touch_down(touch):
            return True

        # Play mode must not place edit objects.
        if not self.edit_mode:
            return False

        # Mouse scrolling in Edit Mode: draw PaintBrush little triangles.
        if touch.is_mouse_scrolling or (hasattr(touch, 'button') and 'scroll' in str(touch.button)):
            pb = PaintBrush()
            pb.center = touch.pos
            self.add_widget(pb)
            self.brushes.append(pb)  # remember brush widgets so Clear/Middle-click can remove them
            return True

        # Middle click in Edit Mode: remove objects at the clicked position.
        if touch.button == 'middle':
            self._remove_touch_graphics(touch)
            return True

        # Right click in Edit Mode: place one app-owned pulsating food circle.
        if touch.button == 'right':
            self._spawn_food(touch.pos, kind='custom')
            return True

        # Left click in Edit Mode: place one square obstacle.
        if touch.button == 'left':
            re = Square()
            re.center = touch.pos
            re.show_collision_margin = True  # show editable obstacle collision boundary
            self.add_widget(re)
            self.obstacles.append(re)
            return True

        return True

    # Handle touch move / mouse drag events
    def on_touch_move(self, touch):
        if super().on_touch_move(touch):
            return True

        # No edit drawing/removing while playing.
        if not self.edit_mode:
            return False

        if hasattr(touch, 'button') and touch.button == 'middle':
            self._remove_touch_graphics(touch)
            return True

        return True

    # Handle touch up / mouse release events
    def on_touch_up(self, touch):
        if super().on_touch_up(touch):
            return True

        # Do not create food/obstacles on release; creation happens only on touch down.
        if not self.edit_mode:
            return False

        return True

    # ---------- keyboard ----------

    def _menu_visible(self):
        menu = getattr(self.parent, 'menu', None)
        return menu is not None and menu.opacity > 0

    def on_key_down(self, *args):
        key = args[1] if len(args) > 1 else None
        codepoint = args[3] if len(args) > 3 else None

        # ESC in Play Game or Edit Mode: stop gameplay and return to Main Menu.
        if key in (27, '27'):
            self.setup_game()
            if hasattr(self, 'parent') and hasattr(self.parent, 'menu') and self.parent.menu:
                self.parent.menu.show_main_menu()
            return

        # While the menu / edit toolbar is shown, keys belong to it (e.g. typing the player name).
        if self._menu_visible():
            return

        if codepoint in ('p', 'P') or key in (112, '112'):
            self.toggle_pause()
            return

        if self.game_over or self.is_paused:
            return

        move = keyboard_handler(*args)
        if move == (0, 0):
            return

        if not self.started:
            # Restrict 180-degree instant reversal opposite to current orientation
            if move[0] == -self.direction[0] and move[1] == -self.direction[1]:
                return
            if not self.start_game(move):
                return
        else:
            # Queue turns so two quick presses within one move cannot reverse the snake into itself
            last = self.turns[-1] if self.turns else self.direction
            if move[0] == -last[0] and move[1] == -last[1]:
                return
            if move != last and len(self.turns) < 2:
                self.turns.append(move)

        # Handle longer press acceleration
        if self.active_key_direction == move:
            self.set_speed(self.max_speed)
        else:
            self.active_key_direction = move
            if self.speed_boost_event:
                Clock.unschedule(self.speed_boost_event)
            self.speed_boost_event = Clock.schedule_once(self._boost_speed, 0.25)

    def on_key_up(self, *args):
        if self.game_over or self.is_paused or self._menu_visible():
            return
        move = keyboard_handler(*args)
        if move == self.active_key_direction or move != (0, 0):
            self.active_key_direction = None
            if self.speed_boost_event:
                Clock.unschedule(self.speed_boost_event)
                self.speed_boost_event = None
            self.set_speed(self.base_speed)


def keyboard_handler(instance, key, scancode=None, codepoint=None, modifiers=None):
    # Normalize key values because Kivy may pass ints, strings, or keycode tuples.
    if isinstance(key, tuple):
        key = key[0]
    key = int(key) if str(key).isdigit() else key

    if codepoint in ('w', 'W') or key in (119, 273): # w=119, up=273
        return (0, 1)
    elif codepoint in ('a', 'A') or key in (97, 276): # a=97, left=276
        return (-1, 0)
    elif codepoint in ('s', 'S') or key in (115, 274): # s=115, down=274
        return (0, -1)
    elif codepoint in ('d', 'D') or key in (100, 275): # d=100, right=275
        return (1, 0)

    return (0, 0)
