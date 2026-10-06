from __future__ import annotations

from .caret import Caret


class IodxParseError(ValueError):
    """A syntax or literal error with its location in the IODX source."""

    def __init__(self, message: str, caret: Caret | None = None) -> None:
        super().__init__(message)
        self.caret = caret
