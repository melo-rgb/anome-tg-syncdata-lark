import os

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "last_message_id.txt")


def load_last_id() -> int:
    try:
        with open(STATE_FILE, "r") as f:
            content = f.read().strip()
            return int(content) if content else 0
    except (FileNotFoundError, ValueError):
        return 0


def save_last_id(message_id: int) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        f.write(str(message_id) + "\n")
