import os
import random
import kivy

from kivy.app import App  # base Class of App inherits from the App class
from kivy.lang import Builder  # allows loading in Kv Design language regardless filename
from kivy.properties import NumericProperty, ListProperty
from kivy.uix.widget import Widget  # elements of a graphical user interface that form part of the User Experience
from kivy.uix.relativelayout import RelativeLayout  # allows setting relative coordinates for children
from kivy.core.window import Window  # used to get keyboard input

kv = Builder.load_file(os.path.join(os.path.dirname(__file__), "drawing.kv"))  # load kv file


# Create the Widget class
class PaintBrush(Widget):
    pass


# Create a square for drawing
class Square(Widget):
    pass


# Create a triangle for drawing
class Triangle(Widget):
    angle = NumericProperty(0)
    color = ListProperty([1, 1, 1])


# Layout class where PaintBrush() class is drawn
class Drawing(RelativeLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        Window.bind(on_key_down=self.on_key_down)

        self.triangle = Triangle()
        max_x = max(0, int(Window.width - self.triangle.width))
        max_y = max(0, int(Window.height - self.triangle.height))
        self.triangle.pos = (random.randint(0, max_x), random.randint(0, max_y))
        self.add_widget(self.triangle)

    # On mouse press how PaintBrush behave
    def on_touch_down(self, touch):
        pb = PaintBrush()
        pb.center = touch.pos
        self.add_widget(pb)
        re = Square()
        re.center = touch.pos
        self.add_widget(re)

    # On mouse movement how PaintBrush behave
    def on_touch_move(self, touch):
        pb = PaintBrush()
        pb.center = touch.pos
        self.add_widget(pb)

    def on_keyboard_closed(self):
        pass

    def on_key_down(self, *args):
        move = keyboard_handler(args[0], args[1], args[2], args[3], args[4])
        print(move)
        if move == (0, 1):
            self.triangle.angle = 0
        elif move == (-1, 0):
            self.triangle.angle = 90
        elif move == (0, -1):
            self.triangle.angle = 180
        elif move == (1, 0):
            self.triangle.angle = 270

        step = 10
        self.triangle.x = (self.triangle.x + move[0] * step) % Window.width
        self.triangle.y = (self.triangle.y + move[1] * step) % Window.height


def keyboard_handler(instance, key, scancode, codepoint, modifiers):
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
