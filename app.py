"""Work-hours tracker with a polished, responsive dark UI."""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from core import (
    HourAdjustment,
    Session,
    Settings,
    adjustments_for_day,
    allocate_session_breakdown,
    calculate_day_summary,
    calculate_period_summary,
    format_hours,
    period_bounds_for_date,
    sessions_for_day,
)
from excel_sync import (
    EXCEL_FILE,
    ExcelSyncError,
    export_full_backup,
    restore_json_from_excel,
    sync_status_text,
    sync_to_excel_if_needed,
)
from storage import (
    DATA_FILE,
    dump_state,
    load_data,
    load_payload,
    new_adjustment_id,
    new_session_id,
    save_data,
)
from ui_responsive import (
    BUTTON_FONT,
    BUTTON_PADY,
    COMPACT_HEIGHT,
    NARROW_FOOTER_WIDTH,
    STAT_LAYOUTS,
    STAT_VALUE_FONT,
    TIMER_FONT,
    TITLE_FONT,
    TREE_HEADINGS,
    VISIBLE_TREE_COLUMNS,
    LayoutMode,
    ResizeWatcher,
    content_padding,
)
from ui_theme import THEME, ActionButton, Card, GradientHeader, PulseDot, StatTile, apply_theme, pick_font, style_toplevel


class SalaryTrackerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Hekal · متتبع ساعات العمل")
        self.root.geometry("940x820")
        self.root.minsize(360, 480)
        apply_theme(root)

        self._scroll_enabled = False
        self._layout_mode: LayoutMode = "wide"
        self._all_tree_columns = (
            "day",
            "hours",
            "standard",
            "overtime",
            "money",
            "sessions",
            "details",
        )

        self.settings, self.sessions, self.adjustments, self.active_session_id = load_data()
        self._build_ui()
        self._resize_watcher = ResizeWatcher(self.root, self._apply_responsive_layout)
        self._run_daily_excel_sync(silent=True)
        self.refresh()
        self.root.after(100, self._resize_watcher.trigger_now)
        self.root.after(1000, self._tick)

    def _build_ui(self) -> None:
        self.shell = tk.Frame(self.root, bg=THEME.bg)
        self.shell.pack(fill=tk.BOTH, expand=True)
        self.shell.rowconfigure(1, weight=1)
        self.shell.columnconfigure(0, weight=1)

        header_wrap = tk.Frame(self.shell, bg=THEME.bg)
        header_wrap.grid(row=0, column=0, sticky="ew")

        GradientHeader(header_wrap).pack(fill=tk.X)
        header_content = tk.Frame(header_wrap, bg=THEME.bg)
        header_content.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.top_row = tk.Frame(header_content, bg=THEME.bg)
        self.top_row.pack(fill=tk.X, padx=24, pady=(18, 0))

        self.title_label = tk.Label(
            self.top_row,
            text="Hekal Work Tracker",
            bg=THEME.bg,
            fg=THEME.text,
            font=(pick_font(THEME.font_ui), 24, "bold"),
        )
        self.title_label.pack(side=tk.RIGHT)

        self.date_chip = tk.Label(
            self.top_row,
            text="",
            bg=THEME.bg_soft,
            fg=THEME.accent,
            font=(pick_font(THEME.font_ui), 10, "bold"),
            padx=12,
            pady=6,
        )
        self.date_chip.pack(side=tk.LEFT)

        self.subtitle_label = tk.Label(
            header_content,
            text="تتبع الجلسات · احسب الساعات · راقب أرباحك الشهرية",
            bg=THEME.bg,
            fg=THEME.text_muted,
            font=(pick_font(THEME.font_ui), 11),
            wraplength=800,
            justify=tk.RIGHT,
        )
        self.subtitle_label.pack(anchor="e", padx=24, pady=(4, 16))

        viewport = tk.Frame(self.shell, bg=THEME.bg)
        viewport.grid(row=1, column=0, sticky="nsew")
        viewport.rowconfigure(0, weight=1)
        viewport.columnconfigure(1, weight=1)

        self.scroll_y = ttk.Scrollbar(viewport, orient=tk.VERTICAL)
        self.scroll_canvas = tk.Canvas(viewport, bg=THEME.bg, highlightthickness=0, bd=0)
        self.scroll_canvas.configure(yscrollcommand=self.scroll_y.set)
        self.scroll_y.configure(command=self.scroll_canvas.yview)

        self.main = tk.Frame(self.scroll_canvas, bg=THEME.bg, padx=24, pady=8)
        self._main_window_id = self.scroll_canvas.create_window((0, 0), window=self.main, anchor="nw")
        self.main.bind("<Configure>", self._on_main_configure)
        self.scroll_canvas.bind("<Configure>", self._on_canvas_configure)
        self.scroll_canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

        self.scroll_canvas.grid(row=0, column=1, sticky="nsew")

        hero = Card(self.main, padding=24, glow=False)
        hero.pack(fill=tk.X, pady=(0, 16))

        status_row = tk.Frame(hero.body, bg=THEME.card)
        status_row.pack(fill=tk.X)

        self.pulse = PulseDot(status_row)
        self.pulse.pack(side=tk.RIGHT, padx=(8, 0))

        self.status_var = tk.StringVar(value="لا توجد جلسة نشطة")
        tk.Label(
            status_row,
            textvariable=self.status_var,
            bg=THEME.card,
            fg=THEME.text_muted,
            font=(pick_font(THEME.font_ui), 12),
            wraplength=520,
            justify=tk.RIGHT,
        ).pack(side=tk.RIGHT, fill=tk.X, expand=True)

        self.elapsed_var = tk.StringVar(value="00:00:00")
        self.elapsed_label = tk.Label(
            hero.body,
            textvariable=self.elapsed_var,
            bg=THEME.card,
            fg=THEME.text,
            font=(pick_font(THEME.font_mono), 54, "bold"),
        )
        self.elapsed_label.pack(anchor="center", pady=(10, 18))

        self.buttons = tk.Frame(hero.body, bg=THEME.card)
        self.buttons.pack(fill=tk.X)

        self.start_btn = ActionButton(
            self.buttons,
            "▶  بدء الجلسة",
            self.start_session,
            color=THEME.success,
            hover=THEME.success_hover,
        )
        self.end_btn = ActionButton(
            self.buttons,
            "■  إنهاء الجلسة",
            self.end_session,
            color=THEME.danger,
            hover=THEME.danger_hover,
        )

        tk.Label(
            self.main,
            text="ملخص اليوم",
            bg=THEME.bg,
            fg=THEME.text,
            font=(pick_font(THEME.font_ui), 13, "bold"),
        ).pack(anchor="e", pady=(0, 8))

        self.stats_row = tk.Frame(self.main, bg=THEME.bg)
        self.stats_row.pack(fill=tk.X, pady=(0, 16))

        self.stat_sessions = StatTile(self.stats_row, "عدد الجلسات", THEME.text)
        self.stat_money = StatTile(self.stats_row, "أرباح اليوم", THEME.violet)
        self.stat_overtime = StatTile(self.stats_row, "ساعات إضافية", THEME.warning)
        self.stat_standard = StatTile(self.stats_row, "ساعات عادية", THEME.success)
        self.stat_total = StatTile(self.stats_row, "إجمالي الساعات", THEME.accent)
        self.stat_tiles = [
            self.stat_sessions,
            self.stat_money,
            self.stat_overtime,
            self.stat_standard,
            self.stat_total,
        ]

        month_card = Card(self.main, padding=16)
        month_card.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        self.month_top = tk.Frame(month_card.body, bg=THEME.card)
        self.month_top.pack(fill=tk.X, pady=(0, 10))

        self.month_title = tk.Label(
            self.month_top,
            text="ملخص الشهر الحالي",
            bg=THEME.card,
            fg=THEME.text,
            font=(pick_font(THEME.font_ui), 13, "bold"),
        )

        self.month_header_var = tk.StringVar()
        self.month_range = tk.Label(
            self.month_top,
            textvariable=self.month_header_var,
            bg=THEME.card,
            fg=THEME.text_muted,
            font=(pick_font(THEME.font_ui), 10),
            wraplength=420,
            justify=tk.LEFT,
        )

        table_wrap = tk.Frame(month_card.body, bg=THEME.card)
        table_wrap.pack(fill=tk.BOTH, expand=True)
        table_wrap.rowconfigure(0, weight=1)
        table_wrap.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(table_wrap, columns=self._all_tree_columns, show="headings")
        for col, text in TREE_HEADINGS.items():
            self.tree.heading(col, text=text, anchor=tk.CENTER)
            self.tree.column(col, anchor=tk.CENTER, stretch=True, minwidth=60)
        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)

        tree_scroll = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll.grid(row=0, column=1, sticky="ns")

        self.month_total_var = tk.StringVar()
        self.month_total_label = tk.Label(
            month_card.body,
            textvariable=self.month_total_var,
            bg=THEME.card,
            fg=THEME.accent,
            font=(pick_font(THEME.font_ui), 12, "bold"),
            wraplength=760,
            justify=tk.RIGHT,
        )
        self.month_total_label.pack(anchor="e", pady=(10, 0))

        self.footer = tk.Frame(self.shell, bg=THEME.bg_soft, padx=24, pady=14)
        self.footer.grid(row=2, column=0, sticky="ew")

        self.actions = tk.Frame(self.footer, bg=THEME.bg_soft)
        self.info = tk.Frame(self.footer, bg=THEME.bg_soft)

        self.footer_buttons = [
            ActionButton(
                self.actions,
                "استعادة Excel",
                self.restore_from_excel,
                color=THEME.card,
                hover=THEME.card_hover,
                text_color=THEME.text,
            ),
            ActionButton(
                self.actions,
                "مزامنة Excel",
                self.sync_excel_now,
                color="#1d4ed8",
                hover="#2563eb",
            ),
            ActionButton(
                self.actions,
                "تصدير كامل",
                self.export_all_data,
                color=THEME.violet,
                hover="#8b5cf6",
                text_color="#04111f",
            ),
            ActionButton(
                self.actions,
                "إضافة / خصم ساعات",
                self.open_hours_adjustment,
                color=THEME.warning,
                hover="#f59e0b",
                text_color="#04111f",
            ),
            ActionButton(
                self.actions,
                "الإعدادات",
                self.open_settings,
                color=THEME.bg_soft,
                hover=THEME.card,
                text_color=THEME.text,
            ),
        ]

        self.sync_status_var = tk.StringVar()
        self.sync_status_label = tk.Label(
            self.info,
            textvariable=self.sync_status_var,
            bg=THEME.bg_soft,
            fg=THEME.text_muted,
            font=(pick_font(THEME.font_ui), 10),
            wraplength=420,
            justify=tk.LEFT,
        )
        self.sync_status_label.pack(anchor="w")

        self.files_label = tk.Label(
            self.info,
            text=f"JSON · {DATA_FILE.name}    Excel · {EXCEL_FILE.name}",
            bg=THEME.bg_soft,
            fg=THEME.text_muted,
            font=(pick_font(THEME.font_ui), 9),
            wraplength=420,
            justify=tk.LEFT,
        )
        self.files_label.pack(anchor="w", pady=(2, 0))

    def _on_main_configure(self, _event: tk.Event | None = None) -> None:
        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.scroll_canvas.itemconfigure(self._main_window_id, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        if not self._scroll_enabled:
            return
        self.scroll_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _apply_responsive_layout(self, width: int, height: int, mode: LayoutMode) -> None:
        self._layout_mode = mode
        pad = content_padding(mode)

        self.main.configure(padx=pad)
        self.top_row.configure(padx=pad)
        self.subtitle_label.configure(padx=pad, wraplength=max(width - pad * 2, 200))
        self.footer.configure(padx=pad)

        self.title_label.configure(font=(pick_font(THEME.font_ui), TITLE_FONT[mode], "bold"))
        self.elapsed_label.configure(font=(pick_font(THEME.font_mono), TIMER_FONT[mode], "bold"))
        self.month_total_label.configure(wraplength=max(width - pad * 2 - 32, 180))
        self.sync_status_label.configure(wraplength=max(width - pad * 2, 180))
        self.files_label.configure(wraplength=max(width - pad * 2, 180))

        title_size = 9 if mode == "compact" else 10
        stat_pad = 10 if mode == "compact" else 14
        for tile in self.stat_tiles:
            tile.set_responsive(title_size=title_size, value_size=STAT_VALUE_FONT[mode], pad_x=stat_pad)

        btn_font = BUTTON_FONT[mode]
        btn_pady = BUTTON_PADY[mode]
        for btn in [self.start_btn, self.end_btn, *self.footer_buttons]:
            btn.set_responsive(font_size=btn_font, pady=btn_pady)

        self._layout_header(mode)
        self._layout_stats(mode)
        self._layout_buttons(mode)
        self._layout_month_header(mode)
        self._layout_footer(width, mode)
        self._layout_tree(width, mode)
        self._layout_scroll(height)

    def _layout_header(self, mode: LayoutMode) -> None:
        self.title_label.pack_forget()
        self.date_chip.pack_forget()
        if mode == "compact":
            self.date_chip.pack(anchor="e", fill=tk.X, pady=(0, 6))
            self.title_label.pack(anchor="e", fill=tk.X)
        else:
            self.title_label.pack(side=tk.RIGHT)
            self.date_chip.pack(side=tk.LEFT)

    def _layout_stats(self, mode: LayoutMode) -> None:
        for tile in self.stat_tiles:
            tile.grid_forget()

        for col in range(8):
            self.stats_row.columnconfigure(col, weight=0, uniform="")
        for row in range(4):
            self.stats_row.rowconfigure(row, weight=0)

        layout = STAT_LAYOUTS[mode]
        max_col = max(column + span - 1 for _, column, span in layout)
        for col in range(max_col + 1):
            self.stats_row.columnconfigure(col, weight=1, uniform="stat")

        max_row = max(row for row, _, _ in layout)
        for row in range(max_row + 1):
            self.stats_row.rowconfigure(row, weight=1)

        gap = 4 if mode == "compact" else 6
        for tile, (row, column, span) in zip(self.stat_tiles, layout):
            tile.grid(
                row=row,
                column=column,
                columnspan=span,
                sticky="nsew",
                padx=(0 if column == 0 else gap, 0 if column + span - 1 == max_col else gap),
                pady=(0, gap if row < max_row else 0),
            )

    def _layout_buttons(self, mode: LayoutMode) -> None:
        self.start_btn.pack_forget()
        self.end_btn.pack_forget()
        if mode == "compact":
            self.end_btn.pack(fill=tk.X, pady=(0, 8))
            self.start_btn.pack(fill=tk.X)
        else:
            self.start_btn.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(8, 0))
            self.end_btn.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(0, 8))

    def _layout_month_header(self, mode: LayoutMode) -> None:
        self.month_title.pack_forget()
        self.month_range.pack_forget()
        if mode == "compact":
            self.month_title.pack(anchor="e", fill=tk.X)
            self.month_range.pack(anchor="e", fill=tk.X, pady=(4, 0))
        else:
            self.month_title.pack(side=tk.RIGHT)
            self.month_range.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))

    def _layout_footer(self, width: int, mode: LayoutMode) -> None:
        narrow = width < NARROW_FOOTER_WIDTH or mode == "compact"
        self.info.pack_forget()
        self.actions.pack_forget()
        for btn in self.footer_buttons:
            btn.pack_forget()

        if narrow:
            self.info.pack(fill=tk.X, anchor="w")
            self.actions.pack(fill=tk.X, pady=(10, 0))
            for btn in self.footer_buttons:
                btn.pack(fill=tk.X, pady=(0, 6))
        else:
            self.info.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.actions.pack(side=tk.RIGHT)
            for index, btn in enumerate(reversed(self.footer_buttons)):
                btn.pack(side=tk.RIGHT, padx=(8 if index else 0, 0))

    def _layout_tree(self, width: int, mode: LayoutMode) -> None:
        visible = VISIBLE_TREE_COLUMNS[mode]
        self.tree.configure(displaycolumns=visible)
        available = max(width - content_padding(mode) * 2 - 48, 240)
        day_width = 108 if mode != "compact" else 96
        details_width = 72 if mode != "compact" else 64
        other_cols = [c for c in visible if c not in {"day", "details"}]
        remaining = max(available - day_width - details_width, 120)
        other_width = max(int(remaining / max(len(other_cols), 1)), 56)

        for col in self._all_tree_columns:
            if col not in visible:
                self.tree.column(col, width=0, minwidth=0, stretch=False)
                self.tree.heading(col, text="")
            else:
                if col == "day":
                    col_width = day_width
                elif col == "details":
                    col_width = details_width
                else:
                    col_width = other_width
                self.tree.column(col, width=col_width, minwidth=56, stretch=col != "details")
                self.tree.heading(col, text=TREE_HEADINGS[col])

    def _layout_scroll(self, height: int) -> None:
        need_scroll = height < COMPACT_HEIGHT
        if need_scroll == self._scroll_enabled:
            self._on_main_configure()
            return

        self._scroll_enabled = need_scroll
        if need_scroll:
            self.scroll_y.grid(row=0, column=0, sticky="ns")
        else:
            self.scroll_y.grid_remove()
            self.scroll_canvas.yview_moveto(0)
        self._on_main_configure()

    def _active_session(self) -> Session | None:
        if not self.active_session_id:
            return None
        for session in self.sessions:
            if session.id == self.active_session_id and session.end is None:
                return session
        return None

    def start_session(self) -> None:
        if self._active_session():
            messagebox.showwarning("تنبيه", "يوجد جلسة نشطة بالفعل. أنهِها أولاً.")
            return

        session = Session(id=new_session_id(), start=datetime.now())
        self.sessions.append(session)
        self.active_session_id = session.id
        self._persist()
        self.refresh()

    def end_session(self) -> None:
        active = self._active_session()
        if not active:
            messagebox.showwarning("تنبيه", "لا توجد جلسة نشطة لإنهائها.")
            return

        updated = Session(id=active.id, start=active.start, end=datetime.now())
        self.sessions = [updated if s.id == active.id else s for s in self.sessions]
        self.active_session_id = None
        self._persist()
        self.refresh()

    def open_settings(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("الإعدادات")
        dialog.geometry("460x420")
        dialog.minsize(320, 380)
        dialog.transient(self.root)
        dialog.grab_set()
        style_toplevel(dialog)

        tk.Label(
            dialog,
            text="إعدادات الحساب",
            bg=THEME.bg,
            fg=THEME.text,
            font=(pick_font(THEME.font_ui), 18, "bold"),
        ).pack(anchor="e", padx=20, pady=(20, 6))

        tk.Label(
            dialog,
            text="عدّل قواعد الشهر والأسعار",
            bg=THEME.bg,
            fg=THEME.text_muted,
            font=(pick_font(THEME.font_ui), 10),
        ).pack(anchor="e", padx=20, pady=(0, 16))

        card = Card(dialog, padding=18)
        card.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 12))

        fields: dict[str, tk.StringVar] = {
            "month_start_day": tk.StringVar(value=str(self.settings.month_start_day)),
            "standard_daily_hours": tk.StringVar(value=str(self.settings.standard_daily_hours)),
            "standard_hourly_rate": tk.StringVar(value=str(self.settings.standard_hourly_rate)),
            "overtime_hourly_rate": tk.StringVar(value=str(self.settings.overtime_hourly_rate)),
        }

        labels = {
            "month_start_day": "بداية الشهر (يوم)",
            "standard_daily_hours": "الساعات اليومية العادية",
            "standard_hourly_rate": "سعر الساعة العادية ($)",
            "overtime_hourly_rate": "سعر الساعة الإضافية ($)",
        }

        for key, label in labels.items():
            row = tk.Frame(card.body, bg=THEME.card)
            row.pack(fill=tk.X, pady=8)
            tk.Label(row, text=label, bg=THEME.card, fg=THEME.text_muted, anchor="e").pack(
                side=tk.RIGHT, fill=tk.X, expand=True
            )
            tk.Entry(
                row,
                textvariable=fields[key],
                width=12,
                justify="center",
                bg=THEME.bg_soft,
                fg=THEME.text,
                insertbackground=THEME.accent,
                relief="flat",
                highlightthickness=1,
                highlightbackground=THEME.border,
                highlightcolor=THEME.accent,
            ).pack(side=tk.LEFT, ipady=6, padx=(0, 8))

        tk.Label(
            card.body,
            text="مثال: بداية من يوم 17 تعني الفترة من 17 إلى 16 من الشهر التالي.",
            bg=THEME.card,
            fg=THEME.text_muted,
            wraplength=380,
            justify=tk.RIGHT,
        ).pack(anchor="e", pady=(8, 0))

        def save_settings() -> None:
            try:
                new_settings = Settings(
                    month_start_day=int(fields["month_start_day"].get()),
                    standard_daily_hours=float(fields["standard_daily_hours"].get()),
                    standard_hourly_rate=float(fields["standard_hourly_rate"].get()),
                    overtime_hourly_rate=float(fields["overtime_hourly_rate"].get()),
                )
                new_settings.validate()
            except ValueError as exc:
                messagebox.showerror("خطأ", str(exc), parent=dialog)
                return

            self.settings = new_settings
            self._persist()
            self.refresh()
            dialog.destroy()

        ActionButton(
            dialog,
            "حفظ الإعدادات",
            save_settings,
            color=THEME.accent,
            hover=THEME.success,
            width=18,
        ).pack(fill=tk.X, padx=20, pady=(0, 20))

    def _persist(self) -> None:
        save_data(
            dump_state(
                self.settings,
                self.sessions,
                self.active_session_id,
                adjustments=self.adjustments,
            )
        )
        self._run_daily_excel_sync(silent=True)

    def _run_daily_excel_sync(self, *, silent: bool, force: bool = False) -> None:
        try:
            sync_to_excel_if_needed(
                self.settings,
                self.sessions,
                self.active_session_id,
                adjustments=self.adjustments,
                force=force,
            )
        except ExcelSyncError as exc:
            if not silent:
                messagebox.showerror("خطأ في Excel", str(exc))
        except OSError as exc:
            if not silent:
                messagebox.showerror("خطأ في Excel", f"تعذر حفظ ملف Excel:\n{exc}")

    def sync_excel_now(self) -> None:
        try:
            path = sync_to_excel_if_needed(
                self.settings,
                self.sessions,
                self.active_session_id,
                adjustments=self.adjustments,
                force=True,
            )
            self.refresh()
            messagebox.showinfo("تمت المزامنة", f"تم تحديث ملف Excel:\n{path or EXCEL_FILE}")
        except (ExcelSyncError, OSError) as exc:
            messagebox.showerror("خطأ في Excel", str(exc))

    def export_all_data(self) -> None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = filedialog.asksaveasfilename(
            title="تصدير كل البيانات",
            defaultextension=".xlsx",
            initialfile=f"hekal_work_full_export_{stamp}.xlsx",
            filetypes=[("Excel", "*.xlsx"), ("All files", "*.*")],
        )
        if not destination:
            return

        try:
            excel_path, json_path = export_full_backup(
                self.settings,
                self.sessions,
                self.active_session_id,
                Path(destination),
                adjustments=self.adjustments,
                json_source=DATA_FILE,
            )
            extra = f"\nونسخة JSON:\n{json_path}" if json_path else ""
            messagebox.showinfo(
                "تم التصدير",
                f"تم تصدير كل البيانات إلى:\n{excel_path}{extra}",
            )
        except (ExcelSyncError, OSError) as exc:
            messagebox.showerror("خطأ في التصدير", str(exc))

    def restore_from_excel(self) -> None:
        if not EXCEL_FILE.exists():
            messagebox.showerror("استعادة", f"ملف Excel غير موجود:\n{EXCEL_FILE}")
            return

        confirmed = messagebox.askyesno(
            "استعادة من Excel",
            "سيتم استبدال بيانات JSON الحالية بما في ملف Excel.\nهل تريد المتابعة؟",
        )
        if not confirmed:
            return

        try:
            (
                self.settings,
                self.sessions,
                self.adjustments,
                self.active_session_id,
            ) = restore_json_from_excel()
            self.refresh()
            messagebox.showinfo("تمت الاستعادة", "تم استرجاع البيانات من Excel بنجاح.")
        except (ExcelSyncError, OSError, ValueError) as exc:
            messagebox.showerror("خطأ في الاستعادة", str(exc))

    def _on_tree_click(self, event: tk.Event) -> None:
        if self.tree.identify_region(event.x, event.y) != "cell":
            return
        column = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)
        if not row_id or not column:
            return
        col_index = int(column.replace("#", "")) - 1
        display = self.tree["displaycolumns"]
        if display in ("#all", ("#all",), []):
            visible = list(self.tree["columns"])
        else:
            visible = list(display)
        if col_index < 0 or col_index >= len(visible):
            return
        if visible[col_index] != "details":
            return
        day_value = self.tree.set(row_id, "day")
        if not day_value:
            return
        self.open_day_details(date.fromisoformat(day_value))

    def open_day_details(self, day: date) -> None:
        now = datetime.now()
        day_sessions = sessions_for_day(self.sessions, day, now=now)
        day_adjustments = adjustments_for_day(self.adjustments, day)
        breakdown = allocate_session_breakdown(day_sessions, self.settings, now=now)
        day_summary = calculate_day_summary(
            day, self.sessions, self.settings, now=now, adjustments=self.adjustments
        )

        dialog = tk.Toplevel(self.root)
        dialog.title(f"تفاصيل يوم {day.isoformat()}")
        dialog.geometry("720x520")
        dialog.minsize(420, 360)
        dialog.transient(self.root)
        dialog.grab_set()
        style_toplevel(dialog)

        tk.Label(
            dialog,
            text=f"تفاصيل الجلسات · {day.isoformat()}",
            bg=THEME.bg,
            fg=THEME.text,
            font=(pick_font(THEME.font_ui), 18, "bold"),
        ).pack(anchor="e", padx=20, pady=(20, 4))

        tk.Label(
            dialog,
            text=(
                f"إجمالي {format_hours(day_summary.total_hours)}"
                f"  ·  عادية {format_hours(day_summary.standard_hours)}"
                f"  ·  إضافية {format_hours(day_summary.overtime_hours)}"
                f"  ·  ${day_summary.earnings:.2f}"
            ),
            bg=THEME.bg,
            fg=THEME.accent,
            font=(pick_font(THEME.font_ui), 11, "bold"),
        ).pack(anchor="e", padx=20, pady=(0, 12))

        card = Card(dialog, padding=12)
        card.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 12))

        columns = ("start", "end", "hours", "standard", "overtime")
        tree = ttk.Treeview(card.body, columns=columns, show="headings", height=10)
        headings = {
            "start": "بدأت الساعة",
            "end": "خلصت الساعة",
            "hours": "المدة",
            "standard": "عادية",
            "overtime": "إضافية",
        }
        for col, text in headings.items():
            tree.heading(col, text=text, anchor=tk.CENTER)
            tree.column(col, anchor=tk.CENTER, width=120, stretch=True)

        scroll = ttk.Scrollbar(card.body, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        if breakdown:
            for index, row in enumerate(breakdown):
                end_text = (
                    row.session.end.strftime("%H:%M:%S")
                    if row.session.end
                    else "جارٍ الآن"
                )
                tag = "even" if index % 2 == 0 else "odd"
                tree.insert(
                    "",
                    tk.END,
                    tags=(tag,),
                    values=(
                        row.session.start.strftime("%H:%M:%S"),
                        end_text,
                        format_hours(row.total_hours),
                        format_hours(row.standard_hours),
                        format_hours(row.overtime_hours),
                    ),
                )
        else:
            tree.insert("", tk.END, values=("—", "—", "0:00", "0:00", "0:00"))

        tree.tag_configure("even", background=THEME.table_row)
        tree.tag_configure("odd", background=THEME.table_alt)

        note = (
            "توزيع الساعات العادية/الإضافية يتم حسب ترتيب الجلسات خلال اليوم "
            f"(أول {format_hours(self.settings.standard_daily_hours)} عادية)."
        )
        tk.Label(
            dialog,
            text=note,
            bg=THEME.bg,
            fg=THEME.text_muted,
            wraplength=660,
            justify=tk.RIGHT,
            font=(pick_font(THEME.font_ui), 9),
        ).pack(anchor="e", padx=20, pady=(0, 8))

        if day_adjustments:
            adj_lines = []
            for adj in sorted(day_adjustments, key=lambda a: a.at):
                kind = "إضافة" if adj.hours_delta > 0 else "خصم"
                time_part = (
                    f" الساعة {adj.at.strftime('%H:%M')}"
                    if (adj.at.hour or adj.at.minute)
                    else ""
                )
                adj_lines.append(
                    f"• {kind} {format_hours(abs(adj.hours_delta))} "
                    f"({adj.hour_type_label}){time_part} — {adj.reason}"
                )
            tk.Label(
                dialog,
                text="تعديلات يدوية:\n" + "\n".join(adj_lines),
                bg=THEME.bg,
                fg=THEME.warning,
                justify=tk.RIGHT,
                wraplength=660,
                font=(pick_font(THEME.font_ui), 10),
            ).pack(anchor="e", padx=20, pady=(0, 12))

        ActionButton(
            dialog,
            "إغلاق",
            dialog.destroy,
            color=THEME.bg_soft,
            hover=THEME.card,
            text_color=THEME.text,
            width=12,
        ).pack(fill=tk.X, padx=20, pady=(0, 20))

    def open_hours_adjustment(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("إضافة / خصم ساعات")
        dialog.geometry("500x580")
        dialog.minsize(360, 500)
        dialog.transient(self.root)
        dialog.grab_set()
        style_toplevel(dialog)

        now = datetime.now()

        tk.Label(
            dialog,
            text="تعديل الساعات يدوياً",
            bg=THEME.bg,
            fg=THEME.text,
            font=(pick_font(THEME.font_ui), 18, "bold"),
        ).pack(anchor="e", padx=20, pady=(20, 6))

        tk.Label(
            dialog,
            text="أضف أو اخصم ساعات عادية أو إضافية مع السبب والتاريخ",
            bg=THEME.bg,
            fg=THEME.text_muted,
            font=(pick_font(THEME.font_ui), 10),
        ).pack(anchor="e", padx=20, pady=(0, 16))

        card = Card(dialog, padding=18)
        card.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 12))

        kind_var = tk.StringVar(value="add")
        hour_type_var = tk.StringVar(value="standard")
        date_var = tk.StringVar(value=now.strftime("%Y-%m-%d"))
        time_var = tk.StringVar(value="")
        hours_var = tk.StringVar(value="1")
        reason_var = tk.StringVar()

        def _radio_row(parent: tk.Misc, variable: tk.StringVar, options: list[tuple[str, str]]) -> None:
            row = tk.Frame(parent, bg=THEME.card)
            row.pack(fill=tk.X, pady=(0, 12))
            for text, value in options:
                tk.Radiobutton(
                    row,
                    text=text,
                    variable=variable,
                    value=value,
                    bg=THEME.card,
                    fg=THEME.text,
                    selectcolor=THEME.bg_soft,
                    activebackground=THEME.card,
                    activeforeground=THEME.text,
                    font=(pick_font(THEME.font_ui), 11),
                ).pack(side=tk.LEFT, padx=(0, 16))

        tk.Label(
            card.body,
            text="نوع العملية",
            bg=THEME.card,
            fg=THEME.text_muted,
            anchor="e",
            font=(pick_font(THEME.font_ui), 10),
        ).pack(anchor="e")
        _radio_row(
            card.body,
            kind_var,
            [("خصم ساعات", "deduct"), ("إضافة ساعات", "add")],
        )

        tk.Label(
            card.body,
            text="نوع الساعات",
            bg=THEME.card,
            fg=THEME.text_muted,
            anchor="e",
            font=(pick_font(THEME.font_ui), 10),
        ).pack(anchor="e")
        _radio_row(
            card.body,
            hour_type_var,
            [("ساعات إضافية", "overtime"), ("ساعات عادية", "standard")],
        )

        fields = [
            ("التاريخ (YYYY-MM-DD)", date_var),
            ("الوقت اختياري (HH:MM)", time_var),
            ("عدد الساعات", hours_var),
            ("السبب", reason_var),
        ]
        for label, var in fields:
            row = tk.Frame(card.body, bg=THEME.card)
            row.pack(fill=tk.X, pady=8)
            tk.Label(row, text=label, bg=THEME.card, fg=THEME.text_muted, anchor="e").pack(
                side=tk.RIGHT, fill=tk.X, expand=True
            )
            tk.Entry(
                row,
                textvariable=var,
                width=18,
                justify="center",
                bg=THEME.bg_soft,
                fg=THEME.text,
                insertbackground=THEME.accent,
                relief="flat",
                highlightthickness=1,
                highlightbackground=THEME.border,
                highlightcolor=THEME.accent,
            ).pack(side=tk.LEFT, ipady=6, padx=(0, 8))

        def save_adjustment() -> None:
            try:
                day = date.fromisoformat(date_var.get().strip())
                time_text = time_var.get().strip()
                if time_text:
                    time_parts = time_text.split(":")
                    if len(time_parts) != 2:
                        raise ValueError("صيغة الوقت يجب أن تكون HH:MM أو اتركه فارغاً")
                    hour, minute = int(time_parts[0]), int(time_parts[1])
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError("الوقت غير صالح")
                else:
                    hour, minute = 0, 0
                hours = float(hours_var.get().strip())
                if hours <= 0:
                    raise ValueError("عدد الساعات يجب أن يكون أكبر من صفر")
                reason = reason_var.get().strip()
                if not reason:
                    raise ValueError("السبب مطلوب")
                hour_type = hour_type_var.get()
                if hour_type not in {"standard", "overtime"}:
                    raise ValueError("اختر نوع الساعات")
                delta = hours if kind_var.get() == "add" else -hours
                at = datetime(day.year, day.month, day.day, hour, minute)
                adjustment = HourAdjustment(
                    id=new_adjustment_id(),
                    at=at,
                    hours_delta=delta,
                    reason=reason,
                    created_at=datetime.now(),
                    hour_type=hour_type,
                )
                adjustment.validate()
            except ValueError as exc:
                messagebox.showerror("خطأ", str(exc), parent=dialog)
                return

            self.adjustments.append(adjustment)
            self._persist()
            self.refresh()
            dialog.destroy()
            kind_label = "إضافة" if adjustment.hours_delta > 0 else "خصم"
            messagebox.showinfo(
                "تم الحفظ",
                f"تم تسجيل {kind_label} {format_hours(abs(adjustment.hours_delta))} "
                f"({adjustment.hour_type_label}) ليوم {adjustment.at.date().isoformat()}.",
            )

        ActionButton(
            dialog,
            "حفظ التعديل",
            save_adjustment,
            color=THEME.accent,
            hover=THEME.success,
            width=18,
        ).pack(fill=tk.X, padx=20, pady=(0, 20))

    def refresh(self) -> None:
        now = datetime.now()
        today = date.today()
        active = self._active_session()

        self.date_chip.configure(text=today.strftime("%A · %d %b %Y"))

        if active:
            self.status_var.set(f"جلسة نشطة منذ {active.start.strftime('%H:%M:%S')}")
            self.pulse.set_active(True)
            self.start_btn.set_enabled(False)
            self.end_btn.set_enabled(True)
        else:
            self.status_var.set("جاهز لبدء جلسة جديدة")
            self.pulse.set_active(False)
            self.start_btn.set_enabled(True)
            self.end_btn.set_enabled(False)

        day_summary = calculate_day_summary(
            today, self.sessions, self.settings, now=now, adjustments=self.adjustments
        )
        self.stat_total.value_var.set(format_hours(day_summary.total_hours))
        self.stat_standard.value_var.set(format_hours(day_summary.standard_hours))
        self.stat_overtime.value_var.set(format_hours(day_summary.overtime_hours))
        self.stat_money.value_var.set(f"${day_summary.earnings:.0f}")
        self.stat_sessions.value_var.set(str(day_summary.session_count))

        period = calculate_period_summary(
            self.sessions, self.settings, today, now=now, adjustments=self.adjustments
        )
        period_start, period_end, _ = period_bounds_for_date(today, self.settings.month_start_day)
        self.month_header_var.set(f"{period_start} → {period_end}")

        for item in self.tree.get_children():
            self.tree.delete(item)

        for index, day_row in enumerate(period.days):
            tag = "even" if index % 2 == 0 else "odd"
            self.tree.insert(
                "",
                tk.END,
                iid=day_row.day.isoformat(),
                tags=(tag,),
                values=(
                    day_row.day.isoformat(),
                    format_hours(day_row.total_hours),
                    format_hours(day_row.standard_hours),
                    format_hours(day_row.overtime_hours),
                    f"${day_row.earnings:.2f}",
                    day_row.session_count,
                    "عرض",
                ),
            )

        self.tree.tag_configure("even", background=THEME.table_row)
        self.tree.tag_configure("odd", background=THEME.table_alt)

        self.month_total_var.set(
            f"إجمالي الشهر  {format_hours(period.total_hours)} ساعة"
            f"   ·   عادية {format_hours(period.standard_hours)}"
            f"   ·   إضافية {format_hours(period.overtime_hours)}"
            f"   ·   ${period.earnings:,.2f}"
        )

        if active:
            elapsed = int(active.duration_seconds(now=now))
            h, rem = divmod(elapsed, 3600)
            m, s = divmod(rem, 60)
            self.elapsed_var.set(f"{h:02d}:{m:02d}:{s:02d}")
        else:
            self.elapsed_var.set("00:00:00")

        payload = load_payload()
        self.sync_status_var.set(sync_status_text(payload.get("last_excel_sync_date")))

    def _tick(self) -> None:
        if self._active_session():
            self.refresh()
        self.root.after(1000, self._tick)


def main() -> None:
    root = tk.Tk()
    SalaryTrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
