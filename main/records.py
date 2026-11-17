import os
import time

from kivy.app import App
from kivy.storage.jsonstore import JsonStore

MAX_RECORDS = 10
MAX_NAME_LENGTH = 12
DEFAULT_SETTINGS = {"speed": 3, "maze": "Campaign", "sound": True}


def data_dir():
    """Folder for saved data: the app's user data directory, or this module's folder outside the app."""
    app = App.get_running_app()
    return app.user_data_dir if app else os.path.dirname(os.path.abspath(__file__))


# Persistent player records (top scores + stats + menu settings) stored as JSON
class ScoreRecords:
    def __init__(self, filename="snake_records.json"):
        self.store = JsonStore(os.path.join(data_dir(), filename))

    @property
    def player(self):
        return self.store.get("player")["name"] if self.store.exists("player") else "Player"

    @player.setter
    def player(self, name):
        self.store.put("player", name=name.strip()[:MAX_NAME_LENGTH] or "Player")

    def setting(self, key):
        settings = self.store.get("settings") if self.store.exists("settings") else {}
        return settings.get(key, DEFAULT_SETTINGS[key])

    def set_setting(self, key, value):
        settings = dict(self.store.get("settings")) if self.store.exists("settings") else {}
        settings[key] = value
        self.store.put("settings", **settings)

    @property
    def games_played(self):
        return self.store.get("stats")["games_played"] if self.store.exists("stats") else 0

    def top(self):
        return self.store.get("records")["entries"] if self.store.exists("records") else []

    @property
    def best(self):
        entries = self.top()
        return entries[0]["score"] if entries else 0

    def submit(self, score, level, length, mode, speed):
        """Record a finished game; return its 1-based rank, or None if it did not make the table."""
        self.store.put("stats", games_played=self.games_played + 1)
        if score <= 0:
            return None

        entry = {
            "name": self.player,
            "score": score,
            "level": level,
            "length": length,
            "mode": mode,
            "speed": speed,
            "date": time.strftime("%Y-%m-%d %H:%M"),
        }
        # Stable sort: on equal scores the older record keeps the higher rank.
        entries = sorted(self.top() + [entry], key=lambda e: e["score"], reverse=True)[:MAX_RECORDS]
        self.store.put("records", entries=entries)
        return next((i for i, e in enumerate(entries, 1) if e is entry), None)
