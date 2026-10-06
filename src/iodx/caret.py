from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Caret:
    """Source range occupied by an IODX syntax node.

    Lines and columns are one-based. Offsets are zero-based and the end offset is
    exclusive.
    """

    begin_line: int
    begin_column: int
    end_line: int
    end_column: int
    begin_offset: int
    end_offset: int

    def __post_init__(self) -> None:
        if self.begin_line == 0:
            self.begin_line = 1
        if self.begin_column == 0:
            self.begin_column = 1

    @classmethod
    def start_end(cls, start: Caret, end: Caret) -> Caret:
        return cls(
            begin_line=start.begin_line,
            begin_column=start.begin_column,
            end_line=end.end_line,
            end_column=end.end_column,
            begin_offset=start.begin_offset,
            end_offset=end.end_offset,
        )

    def format_begin(self) -> str:
        return f"{self.begin_line}:{self.begin_column}"

    def __str__(self) -> str:
        return (
            f"{self.begin_line}:{self.begin_column} .. "
            f"{self.end_line}:{self.end_column} "
            f"[{self.begin_offset}-{self.end_offset}]"
        )
