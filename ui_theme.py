"""Visual theme and reusable UI widgets."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Callable


@dataclass(frozen=True)
class Theme:
    bg: str = "#0b1220"
    bg_soft: str = "#111a2e"
    card: str = "#162033"
    card_hover: str = "#1b2842"
    border: str = "#243352"
    border_glow: str = "#2dd4bf33"
    text: str = "#e8eef9"
    text_muted: str = "#8fa3c1"
    accent: str = "#2dd4bf"
    accent_soft: str = "#134e4a"
    violet: str = "#a78bfa"
    success: str = "#34d399"
    success_hover: str = "#10b981"
    danger: str = "#fb7185"
    danger_hover: str = "#f43f5e"
    warning: str = "#fbbf24"
    table_row: str = "#1a2540"
    table_alt: str = "#152038"
    font_ui: str = "Helvetica Neue"
    font_mono: str = "Menlo"


THEME = Theme()


def pick_font(preferred: str, fallbacks: tuple[str, ...] = ("Helvetica", "Arial")) -> str:
    import tkinter.font as tkfont

    root = tk._default_root
    if root is None:
        return preferred
    families = set(tkfont.families(root))
    if preferred in families:
        return preferred
    for name in fallbacks:
        if name in families:
            return name
    return "TkDefaultFont"


def apply_theme(root: tk.Tk) -> ttk.Style:
    theme = THEME
    root.configure(bg=theme.bg)
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=theme.bg, foreground=theme.text, font=(pick_font(theme.font_ui), 11))
    style.configure("TFrame", background=theme.bg)
    style.configure("Card.TFrame", background=theme.card)
    style.configure("TLabel", background=theme.bg, foreground=theme.text)
    style.configure("Muted.TLabel", background=theme.bg, foreground=theme.text_muted)
    style.configure("Card.TLabel", background=theme.card, foreground=theme.text)
    style.configure("CardMuted.TLabel", background=theme.card, foreground=theme.text_muted)
    style.configure("Hero.TLabel", background=theme.card, foreground=theme.text)
    style.configure("Accent.TLabel", background=theme.card, foreground=theme.accent)
    style.configure("Title.TLabel", background=theme.bg, foreground=theme.text, font=(pick_font(theme.font_ui), 22, "bold"))
    style.configure("Subtitle.TLabel", background=theme.bg, foreground=theme.text_muted, font=(pick_font(theme.font_ui), 11))

    style.configure(
        "Treeview",
        background=theme.table_row,
        fieldbackground=theme.table_row,
        foreground=theme.text,
        bordercolor=theme.border,
        lightcolor=theme.border,
        darkcolor=theme.border,
        rowheight=30,
        font=(pick_font(theme.font_ui), 10),
    )
    style.configure(
        "Treeview.Heading",
        background=theme.bg_soft,
        foreground=theme.accent,
        relief="flat",
        font=(pick_font(theme.font_ui), 10, "bold"),
    )
    style.map("Treeview", background=[("selected", theme.accent_soft)], foreground=[("selected", theme.text)])
    style.configure("Vertical.TScrollbar", background=theme.bg_soft, troughcolor=theme.card, bordercolor=theme.border)
    return style


class Card(tk.Frame):
    def __init__(self, parent: tk.Misc, *, padding: int = 20, glow: bool = False, **kwargs) -> None:
        super().__init__(
            parent,
            bg=THEME.card,
            highlightbackground=THEME.accent if glow else THEME.border,
            highlightthickness=1 if glow else 1,
            bd=0,
            **kwargs,
        )
        self._padding = padding
        self.body = tk.Frame(self, bg=THEME.card)
        self.body.pack(fill=tk.BOTH, expand=True, padx=padding, pady=padding)


class ActionButton(tk.Label):
    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
        *,
        color: str,
        hover: str,
        disabled_color: str = "#334155",
        text_color: str = "#04111f",
        disabled_text: str = "#64748b",
        width: int = 0,
    ) -> None:
        super().__init__(
            parent,
            text=text,
            bg=color,
            fg=text_color,
            font=(pick_font(THEME.font_ui), 12, "bold"),
            padx=18,
            pady=12,
            cursor="hand2",
        )
        if width > 0:
            self.configure(width=width)
        self._command = command
        self._color = color
        self._hover = hover
        self._disabled_color = disabled_color
        self._text_color = text_color
        self._disabled_text = disabled_text
        self._enabled = True
        self._font_size = 12

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def set_responsive(self, *, font_size: int, pady: int) -> None:
        self._font_size = font_size
        self.configure(font=(pick_font(THEME.font_ui), font_size, "bold"), pady=pady)

    def _on_enter(self, _event: tk.Event) -> None:
        if self._enabled:
            self.configure(bg=self._hover)

    def _on_leave(self, _event: tk.Event) -> None:
        if self._enabled:
            self.configure(bg=self._color, fg=self._text_color)
        else:
            self.configure(bg=self._disabled_color, fg=self._disabled_text)

    def _on_click(self, _event: tk.Event) -> None:
        if self._enabled:
            self._command()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if enabled:
            self.configure(bg=self._color, fg=self._text_color, cursor="hand2")
        else:
            self.configure(bg=self._disabled_color, fg=self._disabled_text, cursor="arrow")


class StatTile(tk.Frame):
    def __init__(self, parent: tk.Misc, title: str, accent: str) -> None:
        super().__init__(parent, bg=THEME.card, highlightbackground=THEME.border, highlightthickness=1)
        self.value_var = tk.StringVar(value="—")
        self._title_label = tk.Label(
            self,
            text=title,
            bg=THEME.card,
            fg=THEME.text_muted,
            font=(pick_font(THEME.font_ui), 10),
        )
        self._title_label.pack(anchor="e", padx=14, pady=(12, 2))
        self._value_label = tk.Label(
            self,
            textvariable=self.value_var,
            bg=THEME.card,
            fg=accent,
            font=(pick_font(THEME.font_mono), 18, "bold"),
        )
        self._value_label.pack(anchor="e", padx=14, pady=(0, 12))

    def set_responsive(self, *, title_size: int, value_size: int, pad_x: int) -> None:
        self._title_label.configure(font=(pick_font(THEME.font_ui), title_size))
        self._value_label.configure(font=(pick_font(THEME.font_mono), value_size, "bold"))
        self._title_label.pack_configure(padx=pad_x)
        self._value_label.pack_configure(padx=pad_x)


class PulseDot(tk.Canvas):
    def __init__(self, parent: tk.Misc, size: int = 14) -> None:
        super().__init__(parent, width=size, height=size, bg=THEME.card, highlightthickness=0, bd=0)
        self._size = size
        self._on = True
        self._item = self.create_oval(2, 2, size - 2, size - 2, fill=THEME.text_muted, outline="")
        self._animate()

    def set_active(self, active: bool) -> None:
        self._on = active
        if not active:
            self.itemconfigure(self._item, fill=THEME.text_muted)

    def _animate(self) -> None:
        if self._on:
            current = self.itemcget(self._item, "fill")
            nxt = THEME.accent if current != THEME.accent else THEME.success
            self.itemconfigure(self._item, fill=nxt)
        self.after(700, self._animate)


class GradientHeader(tk.Canvas):
    def __init__(self, parent: tk.Misc, height: int = 88) -> None:
        super().__init__(parent, height=height, highlightthickness=0, bd=0, bg=THEME.bg)
        self._height = height
        self.bind("<Configure>", self._draw)

    def _draw(self, _event: tk.Event | None = None) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 1)
        steps = 28
        for i in range(steps):
            ratio = i / max(steps - 1, 1)
            r = int(11 + ratio * 18)
            g = int(18 + ratio * 30)
            b = int(32 + ratio * 42)
            color = f"#{r:02x}{g:02x}{b:02x}"
            x0 = int(w * i / steps)
            x1 = int(w * (i + 1) / steps) + 1
            self.create_rectangle(x0, 0, x1, self._height, fill=color, outline=color)

        self.create_rectangle(0, self._height - 2, w, self._height, fill=THEME.accent, outline="")


def style_toplevel(window: tk.Toplevel) -> None:
    window.configure(bg=THEME.bg)
