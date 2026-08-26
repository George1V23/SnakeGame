import os
import random
import kivy

from kivy.app import App  # base Class of App inherits from the App class
from kivy.clock import Clock
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
        self.data = widget
        self.value = widget
        self.val = widget
        self.next = next_node
        self.prev = prev_node


# Linked list class representing the snake's body
class LinkedList:
    def __init__(self):
        self.head = None
        self.tail = None
        self.size = 0

    def append(self, widget):
        node = widget if isinstance(widget, Node) else Node(widget)
        if self.head is None:
            self.head = node
            self.tail = node
        else:
            self.tail.next = node
            node.prev = self.tail
            self.tail = node
        self.size += 1
        return node

    def add(self, widget):
        return self.append(widget)

    def __len__(self):
        return self.size

    def __iter__(self):
        curr = self.head
        while curr:
            yield curr
            curr = curr.next

    def update_positions(self, new_head_pos):
        curr = self.tail
        while curr and curr.prev:
            curr.widget.pos = curr.prev.widget.pos
            curr = curr.prev
        if self.head and self.head.widget:
            self.head.widget.pos = new_head_pos

    def check_collision(self):
        if not self.head or not self.head.widget:
            return False
        hx, hy = self.head.widget.x, self.head.widget.y
        curr = self.head.next
        while curr:
            if curr.widget and abs(curr.widget.x - hx) < 1 and abs(curr.widget.y - hy) < 1:
                return True
            curr = curr.next
        return False


SnakeLinkedList = LinkedList


# Layout class where PaintBrush() class is drawn
class Drawing(RelativeLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        Window.bind(on_key_down=self.on_key_down, on_key_up=self.on_key_up)

        self.step = 50
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

        self.triangle = None
        self.squares = []
        self.snake = None
        self.start_label = None
        self.press_key_label = None
        self.move_event = None

        self.setup_game()

    def setup_game(self):
        # Clean up existing snake and UI widgets if any
        if self.triangle and self.triangle in self.children:
            self.remove_widget(self.triangle)
        for sq in self.squares:
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

        self.triangle = Triangle()
        max_x = max(0, int(Window.width - self.triangle.width))
        max_y = max(0, int(Window.height - self.triangle.height))
        start_x = random.randint(0, max_x)
        start_y = random.randint(0, max_y)
        self.triangle.pos = (start_x, start_y)
        self.triangle.angle = initial_angle

        # Linked list for snake body (composed of head and tail formed with squares)
        self.snake = LinkedList()
        self.body = self.snake
        self.snake_body = self.snake
        self.snake.append(self.triangle)

        # Attach 3 square objects to the head
        self.squares = []
        for i in range(1, 4):
            sq = Square()
            sq.pos = (
                (start_x - i * self.direction[0] * self.step) % Window.width,
                (start_y - i * self.direction[1] * self.step) % Window.height,
            )
            self.squares.append(sq)
            self.snake.append(sq)
            self.add_widget(sq)

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
            self.triangle.angle = 0
            self.direction = move
        elif move == (-1, 0):
            self.triangle.angle = 90
            self.direction = move
        elif move == (0, -1):
            self.triangle.angle = 180
            self.direction = move
        elif move == (1, 0):
            self.triangle.angle = 270
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
        new_x = (self.triangle.x + self.direction[0] * self.step) % Window.width
        new_y = (self.triangle.y + self.direction[1] * self.step) % Window.height
        self.snake.update_positions((new_x, new_y))
        if self.check_collision():
            self.end_game()

    # On mouse press how PaintBrush behave
    def on_touch_down(self, touch):
        if super().on_touch_down(touch):
            return True
        pb = PaintBrush()
        pb.center = touch.pos
        self.add_widget(pb)
        re = Square()
        re.center = touch.pos
        self.add_widget(re)
        return True

    # On mouse movement how PaintBrush behave
    def on_touch_move(self, touch):
        if super().on_touch_move(touch):
            return True
        pb = PaintBrush()
        pb.center = touch.pos
        self.add_widget(pb)
        return True

    def on_touch_up(self, touch):
        if super().on_touch_up(touch):
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
    if codepoint in ('w', 'W') or key in (273, '273', 119, '119'):
        return (0, 1)
    elif codepoint in ('a', 'A') or key in (276, '276', 97, '97'):
        return (-1, 0)
    elif codepoint in ('s', 'S') or key in (274, '274', 115, '115'):
        return (0, -1)
    elif codepoint in ('d', 'D') or key in (275, '275', 100, '100'):
        return (1, 0)
    return (0, 0)


# Create the App class
class SnakeApp(App):

    def build(self):
        return Drawing()


if __name__ == '__main__':
    SnakeApp().run()
