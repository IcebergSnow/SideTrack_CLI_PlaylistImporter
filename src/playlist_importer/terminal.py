"""Keep prompts and untrusted metadata separate from the playlist URL on stdout."""

import sys
import unicodedata


def safe_text(value: str) -> str:
    return " ".join("".join(c if not unicodedata.category(c).startswith("C") else " " for c in str(value)).split())


def progress(message: str) -> None:
    print(safe_text(message), file=sys.stderr, flush=True)


def ask(message: str) -> str:
    print(safe_text(message), end=" ", file=sys.stderr, flush=True)
    try:
        return input().strip()
    except EOFError as exc:
        raise KeyboardInterrupt from exc
