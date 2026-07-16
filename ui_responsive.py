"""Responsive layout helpers and breakpoints."""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Literal

LayoutMode = Literal["compact", "medium", "wide"]

COMPACT_WIDTH = 640
MEDIUM_WIDTH = 900
COMPACT_HEIGHT = 560
NARROW_FOOTER_WIDTH = 520

# (row, column, columnspan)
STAT_LAYOUTS: dict[LayoutMode, list[tuple[int, int, int]]] = {
    "wide": [(0, 0, 1), (0, 1, 1), (0, 2, 1), (0, 3, 1), (0, 4, 1)],
    "medium": [(0, 0, 1), (0, 1, 1), (0, 2, 1), (1, 1, 1), (1, 2, 1)],
    "compact": [(0, 0, 1), (0, 1, 1), (1, 0, 1), (1, 1, 1), (2, 0, 2)],
}

VISIBLE_TREE_COLUMNS: dict[LayoutMode, tuple[str, ...]] = {
    "wide": ("day", "hours", "standard", "overtime", "money", "sessions", "details"),
    "medium": ("day", "hours", "standard", "overtime", "money", "sessions", "details"),
    "compact": ("day", "hours", "money", "details"),
}

TREE_HEADINGS = {
    "day": "اليوم",
    "hours": "الساعات",
    "standard": "عادية",
    "overtime": "إضافية",
    "money": "المبلغ $",
    "sessions": "جلسات",
    "details": "تفاصيل",
}

PADDING_X = {"compact": 12, "medium": 18, "wide": 24}
TIMER_FONT = {"compact": 34, "medium": 44, "wide": 54}
TITLE_FONT = {"compact": 18, "medium": 21, "wide": 24}
STAT_VALUE_FONT = {"compact": 14, "medium": 16, "wide": 18}
BUTTON_FONT = {"compact": 10, "medium": 11, "wide": 12}
BUTTON_PADY = {"compact": 10, "medium": 11, "wide": 12}


def layout_mode(width: int) -> LayoutMode:
    if width < COMPACT_WIDTH:
        return "compact"
    if width < MEDIUM_WIDTH:
        return "medium"
    return "wide"


def content_padding(mode: LayoutMode) -> int:
    return PADDING_X[mode]


class ResizeWatcher:
    """Debounced window resize handler."""

    def __init__(self, root: tk.Tk, on_resize: Callable[[int, int, LayoutMode], None], *, delay_ms: int = 80) -> None:
        self._root = root
        self._on_resize = on_resize
        self._delay_ms = delay_ms
        self._after_id: str | None = None
        self._last_mode: LayoutMode | None = None
        self._last_size: tuple[int, int] = (0, 0)
        root.bind("<Configure>", self._handle_configure, add="+")

    def _handle_configure(self, event: tk.Event) -> None:
        if event.widget is not self._root:
            return

        if self._after_id is not None:
            self._root.after_cancel(self._after_id)

        width = max(event.width, 1)
        height = max(event.height, 1)
        self._after_id = self._root.after(self._delay_ms, lambda: self._emit(width, height))

    def _emit(self, width: int, height: int) -> None:
        self._after_id = None
        mode = layout_mode(width)
        if (width, height) == self._last_size and mode == self._last_mode:
            return
        self._last_size = (width, height)
        self._last_mode = mode
        self._on_resize(width, height, mode)

    def trigger_now(self) -> None:
        self._root.update_idletasks()
        width = max(self._root.winfo_width(), 1)
        height = max(self._root.winfo_height(), 1)
        mode = layout_mode(width)
        self._last_size = (width, height)
        self._last_mode = mode
        self._on_resize(width, height, mode)
