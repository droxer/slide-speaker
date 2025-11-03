from typing import Any


def compute_step_percentage(state: dict[str, Any] | None) -> int:
    """Compute overall completion percentage from a state dict.

    Counts steps with status != 'skipped' as total; counts 'completed' as done.
    Returns an integer 0-100.
    """
    if not state:
        return 0
    steps = (state.get("steps") or {}) if isinstance(state, dict) else {}
    if not isinstance(steps, dict):
        return 0
    total = len(
        [
            s
            for s in steps.values()
            if isinstance(s, dict) and s.get("status") != "skipped"
        ]
    )
    if total == 0:
        return 0
    completed = sum(
        1
        for s in steps.values()
        if isinstance(s, dict) and s.get("status") == "completed"
    )
    return int((completed / total) * 100)
