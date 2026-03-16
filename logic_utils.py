def get_range_for_difficulty(difficulty: str):
    """Return (low, high) inclusive range for a given difficulty."""
    raise NotImplementedError("Refactor this function from app.py into logic_utils.py")


def parse_guess(raw: str):
    """
    Parse user input into an int guess.

    Returns: (ok: bool, guess_int: int | None, error_message: str | None)
    """
    raise NotImplementedError("Refactor this function from app.py into logic_utils.py")


def check_guess(guess, secret):
    """
    Compare guess to secret and return (outcome, message).

    outcome examples: "Win", "Too High", "Too Low"
    """
    raise NotImplementedError("Refactor this function from app.py into logic_utils.py")


def update_score(current_score: int, outcome: str, attempt_number: int):
    """Update score based on outcome and attempt number."""
    raise NotImplementedError("Refactor this function from app.py into logic_utils.py")


def reset_game(state: dict, low: int, high: int) -> dict:
    """
    Reset game state for a new game.

    Mutates and returns the state dict with:
      - attempts reset to 0
      - a new random secret in [low, high]
      - status set to "playing"
      - history cleared
    """
    import random
    state["attempts"] = 0
    state["secret"] = random.randint(low, high)
    state["status"] = "playing"
    state["history"] = []
    return state
