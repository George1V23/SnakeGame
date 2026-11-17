import os
import time

from kivy.app import App
from kivy.storage.jsonstore import JsonStore

MAX_RECORDS = 10
MAX_NAME_LENGTH = 12


# Persistent player records (top scores + stats) stored as JSON in the app's user data directory
class ScoreRecords:
    def __init__(self, filename="snake_records.json"):
        app = App.get_running_app()
        folder = app.user_data_dir if app else os.path.dirname(os.path.abspath(__file__))
        self.store = JsonStore(os.path.join(folder, filename))

    @property
    def player(self):
        return self.store.get("player")["name"] if self.store.exists("player") else "Player"

    @player.setter
    def player(self, name):
        self.store.put("player", name=name.strip()[:MAX_NAME_LENGTH] or "Player")

    @property
    def games_played(self):
        return self.store.get("stats")["games_played"] if self.store.exists("stats") else 0

    def top(self):
        return self.store.get("records")["entries"] if self.store.exists("records") else []

    @property
    def best(self):
        entries = self.top()
        return entries[0]["score"] if entries else 0

    def submit(self, score, level, length):
        """Record a finished game; return its 1-based rank, or None if it did not make the table."""
        self.store.put("stats", games_played=self.games_played + 1)
        if score <= 0:
            return None

        entry = {
            "name": self.player,
            "score": score,
            "level": level,
            "length": length,
            "date": time.strftime("%Y-%m-%d %H:%M"),
        }
        # Stable sort: on equal scores the older record keeps the higher rank.
        entries = sorted(self.top() + [entry], key=lambda e: e["score"], reverse=True)[:MAX_RECORDS]
        self.store.put("records", entries=entries)
        return next((i for i, e in enumerate(entries, 1) if e is entry), None)
