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
from editor import LevelEditor
from levels import CAMPAIGN, CUSTOM_SLOTS, MAZE_CHOICES, is_custom


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
            size=(400, 520),
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

        # Level Editor Button
        self.edit_btn = Button(
            text="Level Editor",
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
                 "Editor: Left = paint tool | Right = Food | Middle = Erase | Wheel = tool\n"
                 "[color=40a626]Grass[/color] slows the snake down",
            markup=True,
            font_size=14,
            halign='center',
            color=(0.8, 0.8, 0.8, 1),
            size_hint=(1, None),
            height=110
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

    def _update_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _refresh_settings(self):
        g = self.graphics
        self.speed_label.text = f"Speed {g.start_speed}"
        self.sound_btn.text = "Sound: On" if g.sounds.enabled else "Sound: Off"
        if g.mode == CAMPAIGN:
            note = " (all mazes)"
        elif is_custom(g.mode):
            note = " (your level)"
        else:
            note = " (endless)"
        self.maze_btn.text = f"Maze: {g.mode}{note}"

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
        self._hide()
        if self.parent:
            self.parent.close_editor()
        if self.graphics and not self.graphics.started:
            self.graphics.setup_game()

    def start_edit_mode(self, *args):
        """Open the Level Editor on the selected custom slot (or the first one)."""
        self.save_player_name()
        self.name_input.focus = False
        self._hide()
        if self.parent:
            mode = self.graphics.mode
            self.parent.open_editor(mode if is_custom(mode) else CUSTOM_SLOTS[0])

    def play_custom_level(self, slot):
        """Editor 'Play': select the edited slot as the maze and start it."""
        self.graphics.configure(self.graphics.start_speed, slot)
        self._refresh_settings()
        if self.parent:
            self.parent.close_editor()
        self.graphics.setup_game()
        self._hide()

    def _hide(self):
        self.opacity = 0
        self.disabled = True

    def show_main_menu(self, *args):
        """Return to the Main Menu."""
        if self.parent:
            self.parent.close_editor()
        if self.records_box in self.children:
            self.remove_widget(self.records_box)
        if self.menu_box not in self.children:
            self.add_widget(self.menu_box)

        self.opacity = 1
        self.disabled = False

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

        # Level Editor sits between the board and the menu; it is only in the tree while open
        self.editor = LevelEditor(
            records=self.graphics.records,
            on_play=lambda slot: self.menu.play_custom_level(slot),
            on_menu=lambda: self.menu.show_main_menu(),
            step=self.graphics.step
        )

        self.menu = Menu(graphics_instance=self.graphics)
        self.add_widget(self.menu)

    def open_editor(self, slot):
        self.graphics.edit_mode = True  # board ignores keys while editing
        self.editor.open(slot)
        if self.editor.parent is None:
            self.add_widget(self.editor, index=1)  # above the board, below the menu

    def close_editor(self):
        if self.editor.parent is not None:
            self.remove_widget(self.editor)
        self.graphics.edit_mode = False


# Create the App class
class SnakeApp(App):
    def build(self):
        return MainGameWidget()


if __name__ == '__main__':
    SnakeApp().run()
