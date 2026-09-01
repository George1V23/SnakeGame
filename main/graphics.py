import os
import random
import kivy

from kivy.clock import Clock
from kivy.animation import Animation
from kivy.lang import Builder
from kivy.properties import BooleanProperty, NumericProperty, ListProperty
from kivy.uix.widget import Widget
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window

try:
    from main.snake import Snake, Node, Square, Triangle
except ImportError:
    from snake import Snake, Node, Square, Triangle

# Load kv file
kv_file = os.path.join(os.path.dirname(__file__), "drawing.kv")
if os.path.exists(kv_file):
    Builder.load_file(kv_file)


# Create the PaintBrush widget class
class PaintBrush(Widget):
    pass


# Layout class where the game graphics, snake, obstacles, and food are drawn
class Graphics(RelativeLayout):
    edit_mode = BooleanProperty(False)
    is_paused = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        Window.bind(on_key_down=self.on_key_down, on_key_up=self.on_key_up)

        self.step = 25
        self.base_speed = 0.4
        self.max_speed = 0.08
        self.current_speed = self.base_speed
        self.active_key_direction = None
        self.speed_boost_event = None

        self.game_over = False
        self.game_over_label = None
        self.restart_button = None
        self.play_again_button = None
        self.pause_label = None

        self.started = False
        self.game_started = False
        self.frozen = True

        self.snake = None
        self.triangle = None
        self.head = None
        self.snakeTail = []
        self.obstacles = []
        self.foods = []
        self.start_label = None
        self.press_key_label = None
        self.move_event = None

        self.setup_game()

    def setup_game(self):
        # Clean up existing snake widgets
        if self.triangle and self.triangle in self.children:
            self.remove_widget(self.triangle)
        for sq in self.snakeTail:
            if sq in self.children:
                self.remove_widget(sq)
        if self.start_label and self.start_label in self.children:
            self.remove_widget(self.start_label)
        if self.game_over_label and self.game_over_label in self.children:
            self.remove_widget(self.game_over_label)
        if self.restart_button and self.restart_button in self.children:
            self.remove_widget(self.restart_button)
        if self.pause_label and self.pause_label in self.children:
            self.remove_widget(self.pause_label)

        self.game_over = False
        self.game_over_label = None
        self.restart_button = None
        self.play_again_button = None
        self.pause_label = None
        self.is_paused = False

        self.started = False
        self.game_started = False
        self.frozen = True

        self.current_speed = self.base_speed
        self.active_key_direction = None

        if self.move_event:
            Clock.unschedule(self.move_event)
            self.move_event = None
        if self.speed_boost_event:
            Clock.unschedule(self.speed_boost_event)
            self.speed_boost_event = None

        # Random initial orientation: (direction, angle)
        orientations = [
            ((0, 1), 0),
            ((-1, 0), 90),
            ((0, -1), 180),
            ((1, 0), 270),
        ]
        self.direction, initial_angle = random.choice(orientations)

        # Linked list for snake body (composed of head and tail formed with squares)
        self.snake = Snake(step=self.step)
        self.triangle = self.snake.head.widget
        self.head = self.triangle
        win_w = Window.width if Window and Window.width > 0 else 800
        win_h = Window.height if Window and Window.height > 0 else 600
        max_x = max(0, int(win_w - self.head.width))
        max_y = max(0, int(win_h - self.head.height))
        start_x = random.randint(0, max_x) if max_x > 0 else 100
        start_y = random.randint(0, max_y) if max_y > 0 else 100
        self.head.pos = (start_x, start_y)
        self.head.angle = initial_angle
        self.snake.position_initial_tail()

        # Attach 2 additional square objects to the snake tail (making 3 squares total)
        self.snakeTail = []
        for _ in range(2):
            self.snake.grow()

        for node in self.snake:
            if node != self.snake.head and node.widget:
                self.snakeTail.append(node.widget)
                self.add_widget(node.widget)

        self.add_widget(self.triangle)

        # Prompt label before the game starts (if not in edit mode)
        if not self.edit_mode:
            self.start_label = Label(
                text="press any key",
                font_size=40,
                color=(1, 1, 1, 1),
                pos_hint={'center_x': 0.5, 'center_y': 0.5}
            )
            self.press_key_label = self.start_label
            self.add_widget(self.start_label)

    def restart_game(self, *args):
        self.setup_game()

    def reset_game(self, *args):
        self.setup_game()

    def clear_environment(self):
        """Clear all obstacles, food, and brush widgets from the canvas."""
        for obs in list(self.obstacles):
            if obs in self.children:
                self.remove_widget(obs)
        self.obstacles.clear()

        win = self.get_root_window() or Window
        for food in list(self.foods):
            de = food.get('drawelement')
            if de is not None and win:
                try:
                    Animation.stop_all(de[1])
                    win.canvas.after.remove(de[0])
                    win.canvas.after.remove(de[1])
                except Exception:
                    pass
            widget = food.get('widget')
            if widget and widget in self.children:
                self.remove_widget(widget)
        self.foods.clear()

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
        if self.started or self.game_over:
            return
        self.started = True
        self.game_started = True
        self.frozen = False
        if self.start_label:
            if self.start_label in self.children:
                self.remove_widget(self.start_label)
            self.start_label = None
            self.press_key_label = None
        if move and move != (0, 0):
            if not (move[0] == -self.direction[0] and move[1] == -self.direction[1]):
                self.set_direction(move)
        if not self.move_event and not self.is_paused:
            self.move_event = Clock.schedule_interval(self.move_step, self.current_speed)

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

    def check_collision(self):
        return self.snake.check_collision()

    def check_obstacle_collision(self):
        """Check if snake head collided with any obstacle Square."""
        if not self.head:
            return False
        hx, hy = self.head.center_x, self.head.center_y
        for obs in self.obstacles:
            if abs(obs.center_x - hx) < 25 and abs(obs.center_y - hy) < 25:
                return True
        return False

    def check_food_collision(self):
        """Check if snake head reached any pulsating food circle."""
        if not self.head:
            return
        hx, hy = self.head.center_x, self.head.center_y
        win = self.get_root_window() or Window

        for food in list(self.foods):
            cx, cy = food['center']
            # Collision distance threshold with food
            if abs(cx - hx) < 25 and abs(cy - hy) < 25:
                # Snake eats food -> snake grows
                new_node = self.snake.grow()
                if new_node and new_node.widget:
                    self.snakeTail.append(new_node.widget)
                    self.add_widget(new_node.widget)

                # Remove food from canvas and list
                de = food.get('drawelement')
                if de is not None and win:
                    try:
                        Animation.stop_all(de[1])
                        win.canvas.after.remove(de[0])
                        win.canvas.after.remove(de[1])
                    except Exception:
                        pass
                widget = food.get('widget')
                if widget and widget in self.children:
                    self.remove_widget(widget)

                self.foods.remove(food)

    def end_game(self):
        self.game_over = True
        if self.start_label and self.start_label in self.children:
            self.remove_widget(self.start_label)
            self.start_label = None
            self.press_key_label = None
        if self.move_event:
            Clock.unschedule(self.move_event)
            self.move_event = None
        if self.speed_boost_event:
            Clock.unschedule(self.speed_boost_event)
            self.speed_boost_event = None
        if not self.game_over_label:
            self.game_over_label = Label(
                text="Game Over",
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
            self.play_again_button = self.restart_button
            self.add_widget(self.restart_button)

    def move_step(self, dt=0):
        if self.game_over or not self.started or self.is_paused:
            return
        win_w = Window.width if Window and Window.width > 0 else 800
        win_h = Window.height if Window and Window.height > 0 else 600
        new_center_x = (self.head.center_x + self.direction[0] * self.step) % win_w
        new_center_y = (self.head.center_y + self.direction[1] * self.step) % win_h
        self.snake.update_positions((new_center_x, new_center_y))

        # Check self collision
        if self.check_collision():
            self.end_game()
            return

        # Check obstacle collision
        if self.check_obstacle_collision():
            self.end_game()
            return

        # Check food collision (grows snake)
        self.check_food_collision()

    def _remove_touch_graphics(self, touch):
        """Remove Kivy's red transparent circle-point graphics from the window canvas and delete items at position."""
        if hasattr(touch, 'multitouch_sim'):
            touch.multitouch_sim = False
        win = self.get_root_window() or Window
        if hasattr(touch, 'clear_graphics'):
            touch.clear_graphics(win)
        elif '_drawelement' in touch.ud:
            de = touch.ud.pop('_drawelement', None)
            if de is not None and win:
                try:
                    win.canvas.after.remove(de[0])
                    win.canvas.after.remove(de[1])
                except Exception:
                    pass

        # Also remove any obstacles or food clicked by middle button
        tx, ty = touch.pos
        for obs in list(self.obstacles):
            if abs(obs.center_x - tx) < 20 and abs(obs.center_y - ty) < 20:
                if obs in self.children:
                    self.remove_widget(obs)
                self.obstacles.remove(obs)

        for food in list(self.foods):
            cx, cy = food['center']
            if abs(cx - tx) < 20 and abs(cy - ty) < 20:
                de = food.get('drawelement')
                if de is not None and win:
                    try:
                        Animation.stop_all(de[1])
                        win.canvas.after.remove(de[0])
                        win.canvas.after.remove(de[1])
                    except Exception:
                        pass
                self.foods.remove(food)

    def _start_pulsating(self, touch):
        """Make the red transparent circle-point from right-click pulsate on the window canvas as food."""
        de = touch.ud.get('_drawelement')
        if not de or len(de) < 2:
            return
        color, ellipse = de[0], de[1]

        # Stop existing animations on the ellipse if any
        Animation.stop_all(ellipse)

        cx = ellipse.pos[0] + ellipse.size[0] / 2.0
        cy = ellipse.pos[1] + ellipse.size[1] / 2.0

        min_size = 12
        max_size = 28
        min_pos = (cx - min_size / 2.0, cy - min_size / 2.0)
        max_pos = (cx - max_size / 2.0, cy - max_size / 2.0)

        anim = (
            Animation(size=(max_size, max_size), pos=max_pos, duration=0.5, t='in_out_sine') +
            Animation(size=(min_size, min_size), pos=min_pos, duration=0.5, t='in_out_sine')
        )
        anim.repeat = True
        anim.start(ellipse)

        # Record as food item
        food_entry = {
            'center': (cx, cy),
            'drawelement': de,
            'ellipse': ellipse,
            'color': color
        }
        # Replace or add entry
        self.foods.append(food_entry)

    # Handle touch down / mouse click events
    def on_touch_down(self, touch):
        # Allow child UI widgets (e.g. restart button) to process touch first
        if super().on_touch_down(touch):
            return True

        # Mouse scrolling: draw PaintBrush little triangles with random coloring from drawing.kv
        if touch.is_mouse_scrolling or (hasattr(touch, 'button') and 'scroll' in str(touch.button)):
            pb = PaintBrush()
            pb.center = touch.pos  # place paintbrush triangle at scroll position
            self.add_widget(pb)  # add paintbrush widget to canvas
            return True

        # Middle click: remove Kivy's red transparent circle-point and items
        if hasattr(touch, 'button') and touch.button == 'middle':
            self._remove_touch_graphics(touch)
            return True

        # Right click: place pulsating circle (food)
        if hasattr(touch, 'button') and touch.button == 'right':
            self._start_pulsating(touch)
            return True

        # Left click (default touch): draw a square widget (obstacle) at touch position
        if not hasattr(touch, 'button') or touch.button == 'left':
            re = Square()
            re.center = touch.pos  # center square at click position
            self.add_widget(re)  # add square widget to canvas
            self.obstacles.append(re)  # record as obstacle
            return True

        return True

    # Handle touch move / mouse drag events
    def on_touch_move(self, touch):
        # Allow child UI widgets to process touch move first
        if super().on_touch_move(touch):
            return True
        # Middle click: ensure red transparent circle-point is removed on drag
        if hasattr(touch, 'button') and touch.button == 'middle':
            self._remove_touch_graphics(touch)
            return True
        # Do not draw paintbrush on drag so left-click square remains as is
        return True

    # Handle touch up / mouse release events
    def on_touch_up(self, touch):
        # Allow child UI widgets to process touch up first
        if super().on_touch_up(touch):
            return True
        # Middle click: remove graphics on release
        if hasattr(touch, 'button') and touch.button == 'middle':
            self._remove_touch_graphics(touch)
            return True
        # Right click: ensure pulsation continues around final position after release
        if hasattr(touch, 'button') and touch.button == 'right':
            self._start_pulsating(touch)
            return True
        return super().on_touch_up(touch)

    def on_keyboard_closed(self):
        pass

    def on_key_down(self, *args):
        # Check for pause key 'P'
        instance = args[0] if len(args) > 0 else None
        key = args[1] if len(args) > 1 else None
        codepoint = args[3] if len(args) > 3 else None

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
            self.start_game(move)
        else:
            # Restrict 180-degree instant reversal opposite to current direction
            if move[0] == -self.direction[0] and move[1] == -self.direction[1]:
                return
            self.set_direction(move)

        # Handle longer press acceleration
        if self.active_key_direction == move:
            self.set_speed(self.max_speed)
        else:
            self.active_key_direction = move
            if self.speed_boost_event:
                Clock.unschedule(self.speed_boost_event)
            self.speed_boost_event = Clock.schedule_once(self._boost_speed, 0.25)

    def on_key_up(self, *args):
        if self.game_over or self.is_paused:
            return
        move = keyboard_handler(*args)
        if move == self.active_key_direction or move != (0, 0):
            self.active_key_direction = None
            if self.speed_boost_event:
                Clock.unschedule(self.speed_boost_event)
                self.speed_boost_event = None
            self.set_speed(self.base_speed)


def keyboard_handler(instance, key, scancode=None, codepoint=None, modifiers=None):
    if codepoint in ('w', 'W') or key in (273, '273'):
        return (0, 1)
    elif codepoint in ('a', 'A') or key in (276, '276'):
        return (-1, 0)
    elif codepoint in ('s', 'S') or key in (274, '274'):
        return (0, -1)
    elif codepoint in ('d', 'D') or key in (275, '275'):
        return (1, 0)
    return (0, 0)


# Backward compatibility alias
Drawing = Graphics
