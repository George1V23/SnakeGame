import os
import random
import kivy

from kivy.app import App  # base Class of App inherits from the App class
from kivy.clock import Clock
from kivy.animation import Animation  # allows smooth animations
from kivy.lang import Builder  # allows loading in Kv Design language regardless filename
from kivy.properties import NumericProperty, ListProperty
from kivy.uix.widget import Widget  # elements of a graphical user interface that form part of the User Experience
from kivy.uix.relativelayout import RelativeLayout  # allows setting relative coordinates for children
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window  # used to get keyboard input

kv = Builder.load_file(os.path.join(os.path.dirname(__file__), "drawing.kv"))  # load kv file


# Create the Widget class
class PaintBrush(Widget):
    pass


# Create a square for drawing
class Square(Widget):
    color = ListProperty([1, 1, 1])


# Create a triangle for drawing
class Triangle(Widget):
    angle = NumericProperty(0)
    color = ListProperty([1, 1, 1])


# Node for Linked List
class Node:
    def __init__(self, widget=None, next_node=None, prev_node=None):
        self.widget = widget
        self.next = next_node
        self.prev = prev_node


# Linked list class representing the snake's body
class Snake:
    def __init__(self, color_factor=0.85, step=25):
        self.head = Node(Triangle())
        self.tail = Node(Square())
        self.head.next = self.tail
        self.tail.prev = self.head
        self.size = 1
        self.color_factor = color_factor
        self.step = step
        self._apply_color(self.tail)

    @staticmethod
    def _angle_to_direction(angle):
        if angle == 0:
            return (0, 1)
        elif angle == 90:
            return (-1, 0)
        elif angle == 180:
            return (0, -1)
        elif angle == 270:
            return (1, 0)
        return (0, 1)

    def _apply_color(self, node):
        if (self.head and self.head.widget and hasattr(self.head.widget, 'color')
                and node.widget and hasattr(node.widget, 'color')):
            head_color = self.head.widget.color
            tail_index = max(1, self.size)
            node.widget.color = [
                min(1.0, max(0.0, c * (self.color_factor ** tail_index)))
                for c in head_color[:3]
            ] + (list(head_color[3:]) if len(head_color) > 3 else [])

    def position_initial_tail(self):
        if not self.head or not self.head.widget or not self.tail or not self.tail.widget or self.head == self.tail:
            return
        angle = getattr(self.head.widget, 'angle', 0)
        dir_x, dir_y = self._angle_to_direction(angle)
        win_w = Window.width if Window else 800
        win_h = Window.height if Window else 600
        self.tail.widget.center = (
            (self.head.widget.center_x - dir_x * self.step) % win_w,
            (self.head.widget.center_y - dir_y * self.step) % win_h,
        )

    def _position_node(self, node):
        if not node or not node.widget or not node.prev or not node.prev.widget:
            return
        last = node.prev
        prev = last.prev
        win_w = Window.width if Window else 800
        win_h = Window.height if Window else 600

        if prev and prev.widget:
            diff_x = last.widget.center_x - prev.widget.center_x
            diff_y = last.widget.center_y - prev.widget.center_y
            if win_w > 0:
                if diff_x > win_w / 2:
                    diff_x -= win_w
                elif diff_x < -win_w / 2:
                    diff_x += win_w
            if win_h > 0:
                if diff_y > win_h / 2:
                    diff_y -= win_h
                elif diff_y < -win_h / 2:
                    diff_y += win_h
            if diff_x == 0 and diff_y == 0 and self.head and self.head.widget:
                angle = getattr(self.head.widget, 'angle', 0)
                dir_x, dir_y = self._angle_to_direction(angle)
                diff_x = -dir_x * self.step
                diff_y = -dir_y * self.step
        elif self.head and self.head.widget:
            angle = getattr(self.head.widget, 'angle', 0)
            dir_x, dir_y = self._angle_to_direction(angle)
            diff_x = -dir_x * self.step
            diff_y = -dir_y * self.step
        else:
            diff_x = 0
            diff_y = -self.step

        node.widget.center = (
            (last.widget.center_x + diff_x) % win_w,
            (last.widget.center_y + diff_y) % win_h,
        )

    def grow(self):
        node = Node(Square())
        self.tail.next = node
        node.prev = self.tail
        self.tail = node
        self.size += 1
        self._apply_color(node)
        self._position_node(node)

    def append(self, widget=None):
        return self.grow(widget)

    def add(self, widget=None):
        return self.grow(widget)

    def __len__(self):
        return self.size

    def __iter__(self):
        curr = self.head
        while curr:
            yield curr
            curr = curr.next

    def update_positions(self, new_head_center):
        curr = self.tail
        while curr and curr.prev:
            curr.widget.center = curr.prev.widget.center
            curr = curr.prev
        if self.head and self.head.widget:
            self.head.widget.center = new_head_center

    def check_collision(self):
        """
        Check if a collision has occurred between the head object and any subsequent objects in
        the linked widget structure.

        The method iterates through the linked list starting from the element following the head.
        If any widget's position has coordinates that overlap or are close to the head object's
        coordinates, a collision is detected. The check is based on absolute position differences
        below a minimal threshold.

        :returns: True if a collision is detected, otherwise False.
        :rtype: bool
        """
        if not self.head or not self.head.widget:
            return False
        hx, hy = self.head.widget.center_x, self.head.widget.center_y
        curr = self.head.next
        while curr:
            if curr.widget and abs(curr.widget.center_x - hx) < 1 and abs(curr.widget.center_y - hy) < 1:
                return True
            curr = curr.next
        return False



# Layout class where PaintBrush() class is drawn
class Drawing(RelativeLayout):
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

        self.started = False
        self.game_started = False
        self.frozen = True

        self.snake = None
        self.triangle = None
        self.head = None
        self.snakeTail = []
        self.start_label = None
        self.press_key_label = None
        self.move_event = None

        self.setup_game()

    def setup_game(self):
        # Clean up existing snake and UI widgets if any
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

        self.game_over = False
        self.game_over_label = None
        self.restart_button = None
        self.play_again_button = None

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
        max_x = max(0, int(Window.width - self.head.width))
        max_y = max(0, int(Window.height - self.head.height))
        start_x = random.randint(0, max_x)
        start_y = random.randint(0, max_y)
        self.head.pos = (start_x, start_y)
        self.head.angle = initial_angle
        self.snake.position_initial_tail()

        # Attach 2 additional square objects to the snake tail (making 3 squares total)
        for _ in range(2):
            self.snake.grow()
        self.snakeTail = []
        for node in self.snake:
            if node != self.snake.head and node.widget:
                self.snakeTail.append(node.widget)
                self.add_widget(node.widget)

        self.add_widget(self.triangle)

        # Prompt label before the game starts
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

    def start_game(self, move=None):
        if self.started or self.game_over:
            return
        self.started = True
        self.game_started = True
        self.frozen = False
        if self.start_label:
            self.remove_widget(self.start_label)
            self.start_label = None
            self.press_key_label = None
        if move and move != (0, 0):
            if not (move[0] == -self.direction[0] and move[1] == -self.direction[1]):
                self.set_direction(move)
        if not self.move_event:
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
        if self.move_event:
            Clock.unschedule(self.move_event)
            self.move_event = Clock.schedule_interval(self.move_step, self.current_speed)

    def _boost_speed(self, dt=0):
        if not self.game_over and self.active_key_direction is not None:
            self.set_speed(self.max_speed)

    def check_collision(self):
        return self.snake.check_collision()

    def end_game(self):
        self.game_over = True
        if self.start_label:
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
        if self.game_over or not self.started:
            return
        new_center_x = (self.head.center_x + self.direction[0] * self.step) % Window.width
        new_center_y = (self.head.center_y + self.direction[1] * self.step) % Window.height
        self.snake.update_positions((new_center_x, new_center_y))
        if self.check_collision():
            self.end_game()

    def _remove_touch_graphics(self, touch):
        """
        Remove Kivy's red transparent circle-point graphics from the window canvas.
        """
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

    def _start_pulsating(self, touch):
        """
        Make the red transparent circle-point from right-click pulsate on the window canvas.
        """
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

        # Middle click: remove Kivy's red transparent circle-point
        if hasattr(touch, 'button') and touch.button == 'middle':
            self._remove_touch_graphics(touch)
            return True

        # Right click: make Kivy's red transparent circle-point pulsate on window canvas
        if hasattr(touch, 'button') and touch.button == 'right':
            self._start_pulsating(touch)
            return True

        # Left click (default touch): draw a square widget at touch position
        if not hasattr(touch, 'button') or touch.button == 'left':
            re = Square()
            re.center = touch.pos  # center square at click position
            self.add_widget(re)  # add square widget to canvas
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
        if self.game_over:
            return
        move = keyboard_handler(*args)
        print(move)
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
        if self.game_over:
            return
        move = keyboard_handler(*args)
        if move == self.active_key_direction or move != (0, 0):
            self.active_key_direction = None
            if self.speed_boost_event:
                Clock.unschedule(self.speed_boost_event)
                self.speed_boost_event = None
            self.set_speed(self.base_speed)


def keyboard_handler(instance, key, scancode=None, codepoint=None, modifiers=None):
    print("key event: %s" % [instance, key, scancode, codepoint, modifiers])
    if codepoint in ('w', 'W') or key in (273, '273'):
        return (0, 1)
    elif codepoint in ('a', 'A') or key in (276, '276'):
        return (-1, 0)
    elif codepoint in ('s', 'S') or key in (274, '274'):
        return (0, -1)
    elif codepoint in ('d', 'D') or key in (275, '275'):
        return (1, 0)
    return (0, 0)


# Create the App class
class SnakeApp(App):

    def build(self):
        return Drawing()


if __name__ == '__main__':
    SnakeApp().run()
