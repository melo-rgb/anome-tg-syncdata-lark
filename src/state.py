import os

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "last_message_id.txt")


def load_last_id(path: str = STATE_FILE) -> int:
    try:
        with open(path, "r") as f:
            content = f.read().strip()
            return int(content) if content else 0
    except (FileNotFoundError, ValueError):
        return 0


def save_last_id(message_id: int, path: str = STATE_FILE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(str(message_id) + "\n")
