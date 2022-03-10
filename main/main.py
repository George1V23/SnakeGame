import kivy

kivy.require('1.9.0')  # this restricts the kivy version

from kivy.app import App  # base Class of App inherits from the App class
from kivy.lang import Builder  # allows loading in Kv Design language regardless filename
from kivy.uix.widget import Widget  # elements of a graphical user interface that form part of the User Experience
from kivy.uix.relativelayout import RelativeLayout  # allows setting relative coordinates for children
from kivy.core.window import Window  # used to get keyboard input
from kivy.graphics import Rectangle

kv = Builder.load_file("drawing.kv")  # load kv file


# Create the Widget class
class PaintBrush(Widget):
    pass


# Create a square for drawing
class Square(Widget):
    #canvas = Rectangle(pos=(0, 0), size=(50, 50))
    #rect.Color(1, 1, 1)
    pass



# Layout class where PaintBrush() class is drawn
class Drawing(RelativeLayout):
    def __init__(self):
        super().__init__()

        #self.keyboard = Window.request_keyboard(self.on_keyboard_closed, self)
        #self.keyboard.bind(on_key_down=self.on_key_down)
        Window.bind(on_key_down=self.on_key_down)

    # On mouse press how PaintBrush behave
    def on_touch_down(self, touch):
        pb = PaintBrush()
        pb.center = touch.pos
        self.add_widget(pb)
        re = Square()
        self.add_widget(re)

    # On mouse movement how PaintBrush behave
    def on_touch_move(self, touch):
        pb = PaintBrush()
        pb.center = touch.pos
        self.add_widget(pb)

    def on_keyboard_closed(self):
        #re = Square()
        #self.add_widget(re)
        #Rectangle(pos=(0, 0), size=(50, 50))
        pass

    def on_key_down(self, *args):
        move = keyboard_handler(args[0], args[1], args[2], args[3], args[4])
        print(move)
        # re = Square()
        # self.add_widget(re)
        pass


def keyboard_handler(instance, key, scancode, codepoint, modifiers):
    print("key event: %s" % [instance, key, scancode, codepoint, modifiers])
    if codepoint == 'w' or key == '273':
        return (0, 1)
    elif codepoint == 'a' or key == '276':
        return (-1, 0)
    elif codepoint == 's' or key == '274':
        return (0, -1)
    elif codepoint == 'd' or key == '275':
        return (1, 0)
    return (0, 0)


# Create the App class
class SnakeApp(App):

    def build(self):
        #Window.bind(on_key_down=keyboard_handler)
        return Drawing()


if __name__ == '__main__':
    SnakeApp().run()
