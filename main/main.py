import os
import random
import kivy

from kivy.app import App
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.lang import Builder
from kivy.properties import BooleanProperty, NumericProperty, ListProperty
from kivy.uix.widget import Widget
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window

try:
    from main.snake import Snake, Node, Square, Triangle
    from main.graphics import Graphics, Drawing, PaintBrush, keyboard_handler
except ImportError:
    from snake import Snake, Node, Square, Triangle
    from graphics import Graphics, Drawing, PaintBrush, keyboard_handler


# Menu layout displayed before the game starts
class Menu(RelativeLayout):
    def __init__(self, graphics_instance=None, **kwargs):
        super().__init__(**kwargs)
        self.graphics = graphics_instance

        # Semi-transparent background overlay
        with self.canvas.before:
            from kivy.graphics import Color, Rectangle
            self._bg_color = Color(0, 0, 0, 0.75)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # Container for main menu elements
        self.menu_box = BoxLayout(
            orientation='vertical',
            spacing=15,
            size_hint=(None, None),
            size=(400, 360),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        # Title label
        self.title_label = Label(
            text="SNAKE GAME",
            font_size=48,
            bold=True,
            color=(0.2, 0.9, 0.4, 1),
            size_hint=(1, None),
            height=60
        )
        self.menu_box.add_widget(self.title_label)

        # Play Game Button
        self.play_btn = Button(
            text="Play Game",
            font_size=24,
            size_hint=(1, None),
            height=50,
            background_color=(0.2, 0.7, 0.3, 1)
        )
        self.play_btn.bind(on_release=self.start_play_mode)
        self.menu_box.add_widget(self.play_btn)

        # Edit Mode Button
        self.edit_btn = Button(
            text="Edit Mode (Environment)",
            font_size=24,
            size_hint=(1, None),
            height=50,
            background_color=(0.2, 0.5, 0.8, 1)
        )
        self.edit_btn.bind(on_release=self.start_edit_mode)
        self.menu_box.add_widget(self.edit_btn)

        # Controls description
        self.info_label = Label(
            text="Controls: WASD / Arrows to move\nPress 'P' to Pause\nEdit Mode: Left Click = Obstacle | Right Click = Food",
            font_size=14,
            halign='center',
            color=(0.8, 0.8, 0.8, 1),
            size_hint=(1, None),
            height=80
        )
        self.menu_box.add_widget(self.info_label)

        self.add_widget(self.menu_box)

        # Edit mode top toolbar overlay
        self.edit_bar = RelativeLayout(
            size_hint=(1, None),
            height=70,
            pos_hint={'top': 1, 'x': 0}
        )
        with self.edit_bar.canvas.before:
            from kivy.graphics import Color, Rectangle
            self._bar_color = Color(0, 0, 0, 0.65)
            self._bar_rect = Rectangle(pos=self.edit_bar.pos, size=self.edit_bar.size)
        self.edit_bar.bind(pos=self._update_bar_rect, size=self._update_bar_rect)

        self.edit_info = Label(
            text="[EDIT MODE] Left-Click: Obstacle (Square) | Right-Click: Food (Pulsating Circle) | Middle-Click: Remove | Scroll: Brush",
            font_size=13,
            color=(1, 1, 0.4, 1),
            pos_hint={'center_x': 0.42, 'center_y': 0.5}
        )
        self.edit_bar.add_widget(self.edit_info)

        self.start_from_edit_btn = Button(
            text="Start Game",
            font_size=16,
            size_hint=(None, None),
            size=(110, 40),
            pos_hint={'right': 0.88, 'center_y': 0.5},
            background_color=(0.2, 0.8, 0.3, 1)
        )
        self.start_from_edit_btn.bind(on_release=self.start_play_mode)
        self.edit_bar.add_widget(self.start_from_edit_btn)

        self.clear_btn = Button(
            text="Clear",
            font_size=14,
            size_hint=(None, None),
            size=(70, 40),
            pos_hint={'right': 0.98, 'center_y': 0.5},
            background_color=(0.8, 0.3, 0.2, 1)
        )
        self.clear_btn.bind(on_release=self.clear_environment)
        self.edit_bar.add_widget(self.clear_btn)

        self.menu_btn = Button(
            text="Menu",
            font_size=14,
            size_hint=(None, None),
            size=(70, 40),
            pos_hint={'x': 0.01, 'center_y': 0.5},
            background_color=(0.5, 0.5, 0.5, 1)
        )
        self.menu_btn.bind(on_release=self.show_main_menu)
        self.edit_bar.add_widget(self.menu_btn)

    def _update_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _update_bar_rect(self, *args):
        self._bar_rect.pos = self.edit_bar.pos
        self._bar_rect.size = self.edit_bar.size

    def start_play_mode(self, *args):
        """Switch to Game Play mode."""
        self.opacity = 0
        self.disabled = True
        if self.edit_bar in self.children:
            self.remove_widget(self.edit_bar)
        if self.graphics:
            self.graphics.edit_mode = False
            if not self.graphics.started:
                self.graphics.setup_game()

    def start_edit_mode(self, *args):
        """Switch to Edit Environment mode."""
        # Hide main menu box and show top edit toolbar
        if self.menu_box in self.children:
            self.remove_widget(self.menu_box)
        if self.edit_bar not in self.children:
            self.add_widget(self.edit_bar)

        # Allow clicks through to Graphics canvas
        self.opacity = 1
        self.disabled = False
        self._bg_color.a = 0.0  # make background fully transparent so user sees game canvas

        if self.graphics:
            self.graphics.edit_mode = True
            if self.graphics.start_label and self.graphics.start_label in self.graphics.children:
                self.graphics.remove_widget(self.graphics.start_label)
                self.graphics.start_label = None

    def show_main_menu(self, *args):
        """Return to the Main Menu."""
        if self.edit_bar in self.children:
            self.remove_widget(self.edit_bar)
        if self.menu_box not in self.children:
            self.add_widget(self.menu_box)

        self.opacity = 1
        self.disabled = False
        self._bg_color.a = 0.75

        if self.graphics:
            self.graphics.edit_mode = False

    def clear_environment(self, *args):
        if self.graphics:
            self.graphics.clear_environment()


# Main Application Root Container
class MainGameWidget(RelativeLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.graphics = Graphics()
        self.add_widget(self.graphics)

        self.menu = Menu(graphics_instance=self.graphics)
        self.add_widget(self.menu)


# Create the App class
class SnakeApp(App):
    def build(self):
        return MainGameWidget()


if __name__ == '__main__':
    SnakeApp().run()
