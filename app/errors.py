"""Shared exception helpers."""

from __future__ import annotations


def format_exception(exc: BaseException) -> str:
    """Flatten ExceptionGroup / TaskGroup errors into readable leaf messages."""
    leaves: list[str] = []

    def walk(err: BaseException) -> None:
        if isinstance(err, BaseExceptionGroup):
            for child in err.exceptions:
                walk(child)
            return
        message = str(err).strip()
        if not message or message.startswith("unhandled errors in a TaskGroup"):
            message = repr(err)
        leaves.append(f"{type(err).__name__}: {message}")

    walk(exc)
    # Deduplicate identical parallel failures
    unique: list[str] = []
    for item in leaves:
        if item not in unique:
            unique.append(item)
    return "; ".join(unique) if unique else repr(exc)
