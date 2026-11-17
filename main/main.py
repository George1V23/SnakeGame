import os
import sys

# The SDL2 bundled with Kivy can hang forever opening the PulseAudio driver on PipeWire systems;
# ALSA (routed through PipeWire/Pulse anyway) avoids that. Set before Kivy loads; an explicit env value wins.
if sys.platform.startswith("linux"):
    os.environ.setdefault("SDL_AUDIODRIVER", "alsa")

from kivy.app import App
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput

from kivy.config import Config
Config.set("input", "mouse", "mouse,disable_multitouch")  # disables Kivy's right/middle-click touch-circle simulator
Config.set("kivy", "exit_on_escape", "0")  # prevents ESC from closing the app

from graphics import Graphics
from levels import CAMPAIGN, MAZE_CHOICES


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
            spacing=10,
            size_hint=(None, None),
            size=(400, 500),
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

        # Player name used for the score records
        name_row = BoxLayout(orientation='horizontal', spacing=10, size_hint=(1, None), height=40)
        name_row.add_widget(Label(text="Player:", font_size=20, size_hint=(0.3, 1)))
        self.name_input = TextInput(
            text=self.graphics.records.player if self.graphics else "Player",
            font_size=20,
            multiline=False,
            write_tab=False,
            size_hint=(0.7, 1)
        )
        self.name_input.bind(on_text_validate=self.save_player_name)
        name_row.add_widget(self.name_input)
        self.menu_box.add_widget(name_row)

        # Speed 1-9 (Snake II style) and sound toggle
        settings_row = BoxLayout(orientation='horizontal', spacing=6, size_hint=(1, None), height=40)
        slower_btn = Button(text="-", font_size=24, size_hint=(None, 1), width=40)
        slower_btn.bind(on_release=lambda *a: self.change_speed(-1))
        self.speed_label = Label(font_size=20, size_hint=(None, 1), width=110)
        faster_btn = Button(text="+", font_size=24, size_hint=(None, 1), width=40)
        faster_btn.bind(on_release=lambda *a: self.change_speed(1))
        self.sound_btn = Button(font_size=18, background_color=(0.4, 0.4, 0.6, 1))
        self.sound_btn.bind(on_release=self.toggle_sound)
        for widget in (slower_btn, self.speed_label, faster_btn, self.sound_btn):
            settings_row.add_widget(widget)
        self.menu_box.add_widget(settings_row)

        # Maze choice: Campaign (all mazes, level by level) or one maze played endlessly
        self.maze_btn = Button(font_size=20, size_hint=(1, None), height=40, background_color=(0.5, 0.35, 0.2, 1))
        self.maze_btn.bind(on_release=self.next_maze)
        self.menu_box.add_widget(self.maze_btn)
        self._refresh_settings()

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

        # High Scores Button
        self.records_btn = Button(
            text="High Scores",
            font_size=24,
            size_hint=(1, None),
            height=50,
            background_color=(0.8, 0.6, 0.1, 1)
        )
        self.records_btn.bind(on_release=self.show_records)
        self.menu_box.add_widget(self.records_btn)

        # Controls description
        self.info_label = Label(
            text="WASD / Arrows move (hold = faster) | P Pause | M Sound | ESC Menu\n"
                 "Campaign: eat 10 food per level. Gold = timed bonus.\n"
                 "Power-ups: [color=3399ff]Slow[/color] | [color=33ffe6]Shrink[/color] | [color=cc66ff]Ghost[/color]\n"
                 "Edit Mode: Left = Obstacle | Right = Food | Middle = Remove | Scroll = Brush",
            markup=True,
            font_size=14,
            halign='center',
            color=(0.8, 0.8, 0.8, 1),
            size_hint=(1, None),
            height=90
        )
        self.menu_box.add_widget(self.info_label)

        self.add_widget(self.menu_box)

        # High score table panel
        self.records_box = BoxLayout(
            orientation='vertical',
            spacing=10,
            size_hint=(None, None),
            size=(700, 440),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.records_box.add_widget(Label(
            text="HIGH SCORES",
            font_size=40,
            bold=True,
            color=(1, 0.85, 0.2, 1),
            size_hint=(1, None),
            height=55
        ))
        self.records_table = Label(
            font_name='RobotoMono-Regular',
            font_size=15,
            halign='left',
            valign='top'
        )
        self.records_table.bind(size=self.records_table.setter('text_size'))
        self.records_box.add_widget(self.records_table)
        records_back_btn = Button(
            text="Back",
            font_size=20,
            size_hint=(None, None),
            size=(140, 45),
            pos_hint={'center_x': 0.5},
            background_color=(0.5, 0.5, 0.5, 1)
        )
        records_back_btn.bind(on_release=self.show_main_menu)
        self.records_box.add_widget(records_back_btn)

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

    def _refresh_settings(self):
        g = self.graphics
        self.speed_label.text = f"Speed {g.start_speed}"
        self.sound_btn.text = "Sound: On" if g.sounds.enabled else "Sound: Off"
        self.maze_btn.text = f"Maze: {g.mode}" + (" (all mazes)" if g.mode == CAMPAIGN else " (endless)")

    def _apply_settings(self, speed, mode):
        self.graphics.configure(speed, mode)
        self.graphics.setup_game()  # rebuild the waiting board with the new maze / speed
        self._refresh_settings()

    def change_speed(self, delta):
        self._apply_settings(self.graphics.start_speed + delta, self.graphics.mode)

    def next_maze(self, *args):
        index = MAZE_CHOICES.index(self.graphics.mode)
        self._apply_settings(self.graphics.start_speed, MAZE_CHOICES[(index + 1) % len(MAZE_CHOICES)])

    def toggle_sound(self, *args):
        self.graphics.set_sound(not self.graphics.sounds.enabled)
        self._refresh_settings()

    def save_player_name(self, *args):
        if self.graphics:
            self.graphics.records.player = self.name_input.text
            self.name_input.text = self.graphics.records.player

    def show_records(self, *args):
        """Show the persistent high score table."""
        self.save_player_name()
        records = self.graphics.records
        lines = [f"{'#':>2}  {'NAME':<12} {'SCORE':>6}  {'MODE':<11} {'SPD':>3} {'LVL':>3} {'LEN':>4}  DATE", ""]
        for rank, e in enumerate(records.top(), 1):
            lines.append(f"{rank:>2}  {e['name']:<12} {e['score']:>6}  {e.get('mode', CAMPAIGN):<11} "
                         f"{e.get('speed', '-'):>3} {e['level']:>3} {e['length']:>4}  {e['date']}")
        if len(lines) == 2:
            lines.append("No records yet - go eat something!")
        lines += ["", f"Games played: {records.games_played}"]
        self.records_table.text = "\n".join(lines)

        if self.menu_box in self.children:
            self.remove_widget(self.menu_box)
        if self.records_box not in self.children:
            self.add_widget(self.records_box)

    def start_play_mode(self, *args):
        """Switch to Game Play mode."""
        self.save_player_name()
        self.name_input.focus = False
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
        if self.records_box in self.children:
            self.remove_widget(self.records_box)
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


    """allowing touch events to pass through the disabled Menu overlay to the underlying Graphics widget"""
    def on_touch_down(self, touch):
        if self.disabled or self.opacity == 0:
            return False
        return super().on_touch_down(touch)
    def on_touch_move(self, touch):
        if self.disabled or self.opacity == 0:
            return False
        return super().on_touch_move(touch)
    def on_touch_up(self, touch):
        if self.disabled or self.opacity == 0:
            return False
        return super().on_touch_up(touch)


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
