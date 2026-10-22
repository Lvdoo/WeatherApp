from __future__ import annotations

import ctypes
import os
import queue
import threading
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

import tkinter as tk
import tkinter.font as tkfont

from PIL import Image, ImageDraw, ImageOps, ImageTk

import utils
import weather_api

# ---------------------------------------------------------------------------
# Design constants.  Every colour used by the app lives here (no colour is
# hard-coded anywhere else).
# ---------------------------------------------------------------------------

ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

WHITE = "#FFFFFF"
INK = "#10203A"                 # dark text used on light cards
TEXT_ON_DARK = "#FFFFFF"        # white text on frosted/dark cards
ERROR_COLOR = "#FF6B7A"         # error message (readable on every theme)
MESSAGE_ON_LIGHT = "#0B1B33"    # status text on a light gradient
PLACEHOLDER = "Search a city..."
PLACEHOLDER_HINT = "#C9D6EA"    # light grey hint inside the search pill
ACCENT = "#FFD60A"              # vivid yellow accent (min/max arrows, sunrise)

# --- search bar / unit toggle geometry (multiplied by the global scale) -----
BAR_HEIGHT = 52                 # px: nominal height of the single search pill
BAR_MAX_WIDTH = 560             # px: widest the pill ever gets (toggle incl.)
BAR_PAD_X = 20                  # horizontal padding inside the pill
BAR_WIDTH_RATIO = 0.38          # share of the window width (wide screens)
BAR_TOP_MARGIN = 20             # px: high margin of the bar (results state)

# --- frosted "pill" look of the single search bar ---------------------------
# The pill is one *opaque* bar: the slice of gradient sitting behind it mixed
# with 20 % white.  Opaque (and not translucent) on purpose: the Entry placed
# inside the pill can then use exactly the same colour, so no widget box of a
# different tone is ever visible.  The toggle draws a *darker* rounded case
# behind the active unit instead of a colour accent.
PILL_FILL_ALPHA = 0.20          # white mixed into the gradient (pill fill)
PILL_BORDER_ALPHA = 78          # 1 px light border, ~30 % white
PILL_BORDER_ALPHA_FOCUS = 153   # brighter border while the field has focus
SEGMENT_ACTIVE_ALPHA = 0.30     # dark rounded case drawn behind the active unit
SEGMENT_HOVER_ALPHA = 0.10      # white wash on the inactive unit under the mouse
SEGMENT_TEXT_ALPHA = 0.70       # inactive label: 70 % towards the text colour
SEPARATOR_ALPHA = 0.25          # thin vertical rule between field and toggle
MAGNIFIER_ALPHA = 0.70          # magnifier stroke

# Messages shown under the search bar (states 1 / 2 / 3).
MESSAGE_LOADING = "Searching..."
MESSAGE_EMPTY = "Please enter a city name."

# Gradient + frosted-glass parameters per weather theme.
#   top / bottom : vertical (diagonal) gradient colours, from the icon code
#   overlay      : colour mixed over the cards so white text stays readable
#   alpha        : opacity of that overlay (0 = pure gradient, 1 = opaque)
# Light gradients use a dark overlay ("assombrir les cartes si besoin").
THEMES: dict[str, dict[str, object]] = {
    "clear_day": {"top": "#1E6FFF", "bottom": "#00C6FF", "overlay": INK, "alpha": 0.38},
    "cloudy":    {"top": "#4F6BED", "bottom": "#9FB4FF", "overlay": INK, "alpha": 0.42},
    "rain":      {"top": "#1E2A78", "bottom": "#6A3FD6", "overlay": WHITE, "alpha": 0.16},
    "snow":      {"top": "#4FACFE", "bottom": "#B8E6FF", "overlay": INK, "alpha": 0.54},
    "night":     {"top": "#0B1026", "bottom": "#4B22A0", "overlay": WHITE, "alpha": 0.15},
}
DEFAULT_THEME = "clear_day"     # gradient used by the home / error states

FADE_MS = 400                   # nominal gradient cross-fade duration
FADE_FRAME_MS = 40              # one fade step
CARD_FADE_MS = 300              # card fade-in duration (results state)
CARD_FADE_FRAME_MS = 40         # one card fade step
SHADOW_ALPHA = 70               # card drop-shadow opacity (0-255)
BORDER_ALPHA = 78               # thin light border opacity (0-255)
HOVER_BOOST = 0.06              # extra card opacity on hover
LAYOUT_WIDE = 800               # width breakpoint (px): wide vs narrow
LAYOUT_NARROW = 600             # below this the search pill fills the width

# The three interface states of the single-screen dashboard.
HOME, RESULTS, ERROR = "home", "results", "error"

# Vertical allocation of the window, per state (grid row -> weight).
#   row 0 = top bar (always fixed), then the content rows.
ROW_WEIGHTS: dict[str, dict[int, int]] = {
    HOME:    {0: 1},                    # the whole window centers the bar
    RESULTS: {1: 3, 2: 1},              # central area weight=3, forecast weight=1
    ERROR:   {0: 1},                    # bar + message centered together
}

# Font sizes are expressed in **pixels** (negative Tk sizes), so the global
# scale factor alone decides how big the interface is: (base, minimum).
FONT_SPEC: dict[str, tuple[int, int]] = {
    "temp": (96, 40),
    "city": (28, 14),
    "clock": (16, 10),
    "desc": (17, 11),
    "value": (18, 11),
    "label": (13, 9),
    "day": (17, 10),
    "fc_temp": (15, 10),
    "entry": (15, 11),
    "pill": (14, 11),
    "error": (13, 10),
}

# The vertical list of details inside the "info" card.
#   (key, label, kind, value-key)
INFO_ROWS: list[tuple[str, str, str, Optional[str]]] = [
    ("feels", "Feels like", "value", "feels"),
    ("minmax", "Min / Max", "minmax", None),
    ("humidity", "Humidity", "value", "humidity"),
    ("clouds", "Clouds", "value", "clouds"),
    ("wind_dir", "Wind direction", "value", "wind_dir"),
    ("wind_speed", "Wind speed", "value", "wind_speed"),
    ("sunrise", "Sunrise", "value", "sunrise"),
    ("sunset", "Sunset", "value", "sunset"),
]


# ---------------------------------------------------------------------------
# Small colour helpers
# ---------------------------------------------------------------------------
def _clamp(value: float, low: float, high: float) -> float:
    """Clamp *value* between *low* and *high*."""
    return max(low, min(high, value))


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    """``"#RRGGBB"`` -> ``(r, g, b)``."""
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    """``(r, g, b)`` -> ``"#RRGGBB"``."""
    return "#{:02X}{:02X}{:02X}".format(*(int(_clamp(c, 0, 255)) for c in rgb))


def blend(color_a: str, color_b: str, ratio: float) -> str:
    """Linear interpolation: ``ratio=0`` -> *color_a*, ``ratio=1`` -> *color_b*."""
    ratio = _clamp(ratio, 0.0, 1.0)
    a, b = _hex_to_rgb(color_a), _hex_to_rgb(color_b)
    return _rgb_to_hex(tuple(a[i] + (b[i] - a[i]) * ratio for i in range(3)))


def _rgba_over(base: str, overlay: str, alpha: float) -> str:
    """Flatten *overlay* at *alpha* on top of *base* (both ``"#RRGGBB"``).

    Used to draw translucent cases (active segment, hover wash) directly on a
    Canvas, which has no alpha channel of its own.
    """
    return blend(base, overlay, alpha)


def luminance(color: str) -> float:
    """Rough perceived luminance (0 = black, 1 = white)."""
    r, g, b = _hex_to_rgb(color)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def _message_color(top: str, bottom: str) -> str:
    """Readable white for the status line on a light or a dark gradient."""
    average = blend(top, bottom, 0.5)
    return TEXT_ON_DARK if luminance(average) < 0.62 else MESSAGE_ON_LIGHT


def theme_for_icon(icon_code: Optional[str]) -> str:
    """Map an OpenWeatherMap icon code (01d, 10n, ...) to a theme key."""
    if not icon_code:
        return DEFAULT_THEME
    if icon_code.endswith("n"):            # "n" suffix -> night
        return "night"
    prefix = icon_code[:2]
    if prefix in ("01", "02"):
        return "clear_day"
    if prefix in ("03", "04"):
        return "cloudy"
    if prefix in ("09", "10", "11"):
        return "rain"
    if prefix in ("13", "50"):
        return "snow"
    return DEFAULT_THEME


def _error_message(exc: Exception) -> str:
    """Turn an exception into a short, user friendly message."""
    text = str(exc).lower()
    if "not found" in text:
        return "City not found. Please check the spelling."
    if "api key" in text or ("invalid" in text and "key" in text):
        return "Invalid API key."
    for word in ("connection", "timed out", "timeout", "max retries",
                 "getaddrinfo", "ssl", "network", "unreachable", "proxy"):
        if word in text:
            return "No internet connection. Please try again."
    return "Something went wrong. Please try again."


def _summarise_forecast(hourly: dict) -> list[dict]:
    """
    Group the raw 3-hour forecast by real calendar day.

    ``utils.daily_summary`` does the same maths but hides the dates, so the
    day names would drift from the API data.  Reading the dates here keeps the
    forecast honest without modifying ``utils.py``.
    """
    groups: dict[str, list] = {}
    for stamp, info in hourly.items():
        groups.setdefault(stamp.split(" ")[0], []).append(info)

    summary: list[dict] = []
    for date, hours in groups.items():
        descriptions = [hour["weather"] for hour in hours]
        summary.append({
            "date": date,
            "min_temp": round(min(hour["temp_min"] for hour in hours)),
            "max_temp": round(max(hour["temp_max"] for hour in hours)),
            "description": max(set(descriptions), key=descriptions.count),
            "icon": hours[len(hours) // 2]["icon"],
        })
    return summary


# ---------------------------------------------------------------------------
# Card: a rounded "frosted glass" panel.
#
# The card is a Canvas that paints, as its background image, the slice of the
# window gradient sitting behind it + a translucent rounded rectangle + a soft
# shadow.  Everything else (text, icons) is drawn as canvas items, so no child
# widget ever breaks the transparency illusion.
# ---------------------------------------------------------------------------
class Card(tk.Canvas):
    """Rounded, optionally hoverable, glass card drawn on a Canvas."""

    def __init__(self, master: tk.Misc, app: "WeatherApp", radius: int = 24,
                 shadow: int = 6, pad: int = 20, hover: bool = False, **kwargs) -> None:
        super().__init__(master, bd=0, highlightthickness=0, relief="flat", **kwargs)
        self.app = app
        self.radius = radius
        self.shadow = shadow
        self.pad = pad
        self.hover_enabled = hover
        self._hover = False
        # Optional explicit glass fill (RGBA tuple) + border alpha.  When None
        # the card uses the app's darkened "result card" overlay.
        self.glass: Optional[tuple[int, int, int, int]] = None
        self.border_alpha: int = BORDER_ALPHA
        self.alpha_boost: float = 0.0
        self._bg_item: Optional[int] = None
        self._photo: Optional[ImageTk.PhotoImage] = None
        # The app installs a callable that draws the card content.
        self.draw_content: Optional[Callable[["Card", int, int], None]] = None
        self.configure(width=1, height=40)      # tiny request: grid decides

        if hover:
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)

    # ------------------------------------------------------------- geometry
    def set_metrics(self, radius: int, shadow: int, pad: int) -> None:
        """Update radius / shadow / padding (they follow the global scale)."""
        self.radius, self.shadow, self.pad = radius, shadow, pad

    def repaint(self, opacity: float = 1.0) -> None:
        """Recompose the background slice + redraw the content."""
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 1 or height <= 1:
            return
        image = self._compose_background(width, height, opacity)
        photo = ImageTk.PhotoImage(image)
        self._photo = photo                        # keep a reference alive
        if self._bg_item is None:
            self._bg_item = self.create_image(0, 0, anchor="nw", image=photo)
        else:
            self.itemconfigure(self._bg_item, image=photo)
        self.tag_lower(self._bg_item)              # put it behind the content
        self.delete("content")
        if self.draw_content is not None:
            self.draw_content(self, width, height)

    def _gradient_backdrop(self, width: int, height: int) -> Image.Image:
        """RGBA slice of the window gradient sitting behind this card."""
        return self.app._gradient_slice(self, width, height)

    def _compose_background(self, width: int, height: int,
                            opacity: float = 1.0) -> Image.Image:
        """
        Gradient slice behind the card + the glass overlay.

        When *opacity* is below 1 the whole card fades towards the bare
        gradient behind it, which is what the results state animates.
        """
        base = self._gradient_backdrop(width, height)
        overlay = self._overlay(width, height)
        composed = Image.alpha_composite(base, overlay)
        if opacity < 1.0:                       # one cheap C-level pass
            composed = Image.blend(base, composed, _clamp(opacity, 0.0, 1.0))
        return composed.convert("RGB")

    def _bounds(self, width: int, height: int) -> tuple[int, int]:
        """Bottom-right corner of the glass rectangle (shadow included)."""
        return width - 1 - self.shadow, height - 1 - self.shadow

    def _overlay(self, width: int, height: int) -> Image.Image:
        """Translucent rounded rectangle + drop shadow, as an RGBA layer."""
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        x1, y1 = self._bounds(width, height)
        radius = min(self.radius, max(0, x1 // 2), max(0, y1 // 2))
        if self.glass is not None:
            # Explicit fill (search pill / toggle): white translucent glass.
            r, gg, b, a = self.glass
            glass = (r, gg, b, max(0, min(255, int(a))))
            border = max(0, min(255, int(self.border_alpha)))
        else:
            glass = self.app._glass_rgba(self._hover and self.hover_enabled,
                                         self.alpha_boost)
            border = self.border_alpha
        if self.shadow > 0:
            # Soft drop shadow: same rounded rectangle, translucent black,
            # shifted by the shadow offset, clipped by the card bounds.
            shadow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            ImageDraw.Draw(shadow_layer).rounded_rectangle(
                [self.shadow, self.shadow, x1 + self.shadow, y1 + self.shadow],
                radius=radius, fill=(0, 0, 0, SHADOW_ALPHA))
            overlay = Image.alpha_composite(overlay, shadow_layer)
        draw = ImageDraw.Draw(overlay)
        if radius < 2:
            draw.rectangle([0, 0, x1, y1], fill=glass)
        else:
            draw.rounded_rectangle([0, 0, x1, y1], radius=radius, fill=glass,
                                   outline=(255, 255, 255, border), width=1)
        return overlay

    # --------------------------------------------------------------- hover
    def _on_enter(self, _event: tk.Event) -> None:
        if not self._hover:
            self._hover = True
            self.repaint()

    def _on_leave(self, event: tk.Event) -> None:
        # Ignore the "entered a child widget" leave events (avoids flicker).
        if getattr(event, "detail", "") == "NotifyInferior":
            return
        if self._hover:
            self._hover = False
            self.repaint()


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------
class WeatherApp(tk.Tk):
    """Single-screen, responsive weather dashboard."""

    def __init__(self) -> None:
        super().__init__()
        self._setup_scaling()
        self.title("WeatherApp")
        default_theme = THEMES[DEFAULT_THEME]
        # Average of the gradient: no grey flash before the first paint.
        self.configure(bg=blend(str(default_theme["top"]),
                                str(default_theme["bottom"]), 0.5))
        self._center_window()
        self.minsize(360, 600)

        # ---------------------------------------------------- runtime state
        self._state = HOME                     # HOME | RESULTS | ERROR
        self._scale = 1.0
        self._layout_mode = ""                 # "wide" | "narrow"
        self._unit = "metric"                  # °C selected by default
        self._city = ""
        self._tz_offset = 0
        self._has_data = False
        self._loading = False
        self._closing = False
        self._message = ""                     # one-line status under the bar
        self._error_text = ""                  # ERROR-state message (vivid)
        self._opacity = 1.0                    # current opacity of the cards
        self._placeholder_shown = False        # is the search hint displayed?
        self._search_focused = False           # does the search field have focus?
        self._request_seq = 0
        self._results: "queue.Queue[tuple]" = queue.Queue()

        # pending after() ids (always cancelled before being replaced)
        self._resize_after: Optional[str] = None
        self._fade_after: Optional[str] = None
        self._card_fade_after: Optional[str] = None
        self._clock_after: Optional[str] = None
        self._poll_after: Optional[str] = None
        self._in_relayout = False

        # gradient / theme state (interpolated during the fade)
        self._theme = DEFAULT_THEME
        theme = THEMES[DEFAULT_THEME]
        self._grad_top = str(theme["top"])
        self._grad_bottom = str(theme["bottom"])
        self._overlay = str(theme["overlay"])
        self._alpha = float(theme["alpha"])
        self._grad_image: Optional[Image.Image] = None
        self._bg_photo: Optional[ImageTk.PhotoImage] = None
        self._bg_item: Optional[int] = None
        # small diagonal mask reused for every gradient (built once)
        base = Image.linear_gradient("L")
        self._mask_base = Image.blend(base, base.transpose(Image.Transpose.ROTATE_90), 0.5)
        self._mask_small: Optional[Image.Image] = None
        self._mask_key: tuple[int, int] = (0, 0)
        # metrics (recomputed from the scale on every relayout)
        self._margin = 16
        self._gutter = 14
        self._search_height = 52
        self._bar_width = 420
        self._search_pad_x = 20
        self._bar_top = 20             # high margin of the bar (results state)
        self._bar_pinned_top = False   # True once the bar moved to the top

        # search pill drawing state (one full-window canvas, see _paint_bar)
        self._bar_item: Optional[int] = None
        self._bar_photo: Optional[ImageTk.PhotoImage] = None
        self._unit_hit_item: Optional[int] = None
        self._unit_zone: tuple[int, int] = (0, 1)   # (x of the toggle, seg width)
        self._message_item: Optional[int] = None
        self._bar_fill = blend(str(default_theme["top"]),
                               str(default_theme["bottom"]), 0.5)
        self._bar_main = TEXT_ON_DARK
        self._hover_segment: Optional[int] = None   # °C/°F segment under mouse
        self._unit_enabled = True

        # content shown by the cards
        self._icon_name = ""
        self._temp_value = "—"
        self._clock_text = ""
        self._description = ""
        self._description = ""
        self._forecast: list[dict] = []
        self._info_values: dict[str, str] = {
            "feels": "—", "max": "—", "min": "—", "humidity": "—", "clouds": "—",
            "wind_dir": "—", "wind_speed": "—", "sunrise": "—", "sunset": "—",
        }
        self._fc_hover: Optional[int] = None

        # icon cache: (name, size, tint) -> PhotoImage or None
        self._icon_cache: dict[tuple, Optional[ImageTk.PhotoImage]] = {}
        self._icon_sources: dict[str, Optional[Image.Image]] = {}

        self._build_fonts()
        self._build_layout()

        self.bind("<Configure>", self._on_configure)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._show_home(home=True)                     # state 1: home
        self.after(60, self._relayout)                 # first paint
        self.after(200, self._focus_entry)             # focus the search field

    # --------------------------------------------------------------- setup
    def _setup_scaling(self) -> None:
        """Make Tk follow the physical DPI of the screen (HiDPI)."""
        try:
            dpi = float(self.winfo_fpixels("1i"))
            if dpi > 0:
                self.tk.call("tk", "scaling", dpi / 72.0)
        except Exception:
            pass

    def _center_window(self) -> None:
        """Start at ~70% of the screen, centered."""
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        width, height = int(screen_w * 0.70), int(screen_h * 0.70)
        x, y = max(0, (screen_w - width) // 2), max(0, (screen_h - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _pick_font_family(self) -> str:
        """Best available system font (SF Pro on macOS, Segoe UI on Windows)."""
        available = set(tkfont.families(self))
        for family in ("SF Pro Display", "Segoe UI Variable Display", "Segoe UI",
                       "Helvetica Neue", "Helvetica", "Arial"):
            if family in available:
                return family
        return "Helvetica"

    def _build_fonts(self) -> None:
        """Create one Font object per role (sizes are set by _update_fonts)."""
        family = self._pick_font_family()
        self.font_family = family

        def make(weight: str = "normal") -> tkfont.Font:
            return tkfont.Font(family=family, size=-16, weight=weight)

        self.f_temp = make()
        self.f_city = make("bold")
        self.f_clock = make()
        self.f_desc = make()
        self.f_value = make("bold")
        self.f_label = make()
        self.f_day = make("bold")
        self.f_day_temp = make()
        self.f_entry = make()
        self.f_pill = make("bold")
        self.f_pill_idle = make()        # inactive °C/°F segment (not bold)
        self.f_error = make()
        self._update_fonts()

    # ---------------------------------------------------------- top level UI
    def _build_layout(self) -> None:
        """One full-window canvas (gradient + search pill) + the three cards."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Full-window canvas, created first -> lowest stacking order.  It
        # carries the gradient *and* every part of the search bar (pill,
        # magnifier, field, toggle, status line), so no Frame / Label with a
        # default background can ever show a grey band behind the bar.
        average = blend(str(THEMES[DEFAULT_THEME]["top"]),
                        str(THEMES[DEFAULT_THEME]["bottom"]), 0.5)
        self._bg_canvas = tk.Canvas(self, bd=0, highlightthickness=0, bg=average)
        self._bg_canvas.grid(row=0, column=0, rowspan=5, columnspan=2, sticky="nsew")

        # ---- the search field: a real Entry embedded *inside* the pill, as a
        # canvas child window.  _paint_bar() keeps its colours identical to the
        # pill behind it, so the widget itself stays invisible.
        self._entry = tk.Entry(self._bg_canvas, font=self.f_entry, bd=0,
                               relief="flat", highlightthickness=0, insertwidth=1,
                               fg=TEXT_ON_DARK, bg=average, cursor="xterm",
                               disabledbackground=average,
                               disabledforeground=TEXT_ON_DARK,
                               highlightbackground=average,
                               highlightcolor=average,
                               insertbackground=TEXT_ON_DARK)
        self._entry_window = self._bg_canvas.create_window(
            0, 0, window=self._entry, anchor="w")
        self._entry.bind("<Return>", lambda _event: self._search())
        self._entry.bind("<Key>", self._on_entry_key)
        self._entry.bind("<FocusIn>", self._on_entry_focus_in)
        self._entry.bind("<FocusOut>", self._on_entry_focus_out)
        self._entry.insert(0, PLACEHOLDER)

        # ---- tag-based canvas bindings (they survive every bar repaint):
        # the pill itself focuses the field, the toggle zone switches unit.
        canvas = self._bg_canvas
        canvas.tag_bind("bar", "<Button-1>", self._on_bar_click)
        canvas.tag_bind("bar", "<Enter>", self._on_bar_enter)
        canvas.tag_bind("bar", "<Leave>", self._on_bar_leave)
        canvas.tag_bind("unit_hit", "<Button-1>", self._on_unit_click)
        canvas.tag_bind("unit_hit", "<Motion>", self._on_unit_motion)
        canvas.tag_bind("unit_hit", "<Enter>", self._on_unit_enter)
        canvas.tag_bind("unit_hit", "<Leave>", self._on_unit_leave)
        canvas.bind("<Leave>", lambda _e: canvas.configure(cursor=""), add="+")

        # ---- the three cards (created once, shown only in the results state)
        self._info_card = Card(self, self, hover=False)
        self._info_card.draw_content = self._draw_info_card
        self._temp_card = Card(self, self, hover=True)
        self._temp_card.draw_content = self._draw_temp_card
        self._forecast_card = Card(self, self, hover=False)
        self._forecast_card.draw_content = self._draw_forecast_card
        self._forecast_card.bind("<Motion>", self._on_forecast_motion)
        self._forecast_card.bind("<Leave>", self._on_forecast_leave)

        self._result_cards = [self._info_card, self._temp_card, self._forecast_card]

    def _focus_entry(self) -> None:
        """Give the keyboard to the search field (home state auto-focus)."""
        try:
            self._entry.focus_set()
            self.focus_force()
        except tk.TclError:
            pass

    # ---------------------------------------------------------- responsive
    def _on_configure(self, event: Optional[tk.Event]) -> None:
        """Debounced reaction to window resizes (~100 ms)."""
        if event is not None and event.widget is not self:
            return
        self._schedule_relayout()

    def _schedule_relayout(self) -> None:
        if self._in_relayout:
            return
        if self._resize_after is not None:
            self.after_cancel(self._resize_after)
        self._resize_after = self.after(100, self._relayout)

    def _relayout(self) -> None:
        """Recompute scale, fonts, metrics, breakpoint and repaint everything."""
        self._resize_after = None
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 1 or height <= 1:      # window not realised yet
            return
        if self._in_relayout:
            return
        self._in_relayout = True
        try:
            self._scale = _clamp(min(width / 1080.0, height / 720.0), 0.5, 2.0)
            self._update_fonts()
            self._layout_mode = "wide" if width > LAYOUT_WIDE else "narrow"
            self._apply_metrics()
            self._apply_grid()
            self.update_idletasks()
            self._rebuild_gradient()
            self._paint_all()
        finally:
            self._in_relayout = False

    def _update_fonts(self) -> None:
        """Scale every font between its minimum and its 1080x720 size."""
        scale = self._scale

        def px(role: str) -> int:
            base, minimum = FONT_SPEC[role]
            return max(minimum, int(round(base * scale)))

        for font, role in ((self.f_temp, "temp"), (self.f_city, "city"),
                           (self.f_clock, "clock"), (self.f_desc, "desc"),
                           (self.f_value, "value"), (self.f_label, "label"),
                           (self.f_day, "day"), (self.f_day_temp, "fc_temp"),
                           (self.f_entry, "entry"), (self.f_pill, "pill"),
                           (self.f_pill_idle, "pill"), (self.f_error, "error")):
            font.configure(size=-px(role))

    def _apply_metrics(self) -> None:
        """Radius / padding / gutter / icon sizes follow the global scale."""
        scale = self._scale
        self._margin = int(_clamp(round(16 * scale), 8, 34))
        self._gutter = int(_clamp(round(14 * scale), 6, 30))
        radius = int(_clamp(round(24 * scale), 10, 52))
        pad = int(_clamp(round(20 * scale), 8, 44))
        shadow = int(_clamp(round(6 * scale), 0, 16))
        for card in self._result_cards:
            card.set_metrics(radius, shadow, pad)

        # ---- search pill: one full-radius bar, ~52 px high * scale.
        self._search_height = int(round(BAR_HEIGHT * scale))
        self._search_height = max(self._search_height,
                                  self.f_entry.metrics("linespace")
                                  + int(round(8 * scale)))
        self._search_pad_x = int(_clamp(round(BAR_PAD_X * scale), 8,
                                        int(round(BAR_PAD_X * 1.6))))

        # One width for every state (the bar never grows between home and
        # results): a centred bar on wide screens, the whole width minus the
        # margins below LAYOUT_NARROW - the toggle stays inside the pill, only
        # the paddings shrink.
        width = max(1, self.winfo_width())
        if width < LAYOUT_NARROW:
            target = cap = width - 2 * self._margin   # narrow: fill the row
        else:
            target = width * BAR_WIDTH_RATIO
            cap = int(BAR_MAX_WIDTH * scale)
        self._bar_width = int(_clamp(round(target), int(220 * scale),
                                     max(int(220 * scale), cap)))
        self._bar_width = min(self._bar_width,
                              max(int(220 * scale), width - 2 * self._margin))
        # High margin of the bar once it is pinned to the top of the window.
        self._bar_top = max(4, int(round(BAR_TOP_MARGIN * scale)))

    def _apply_grid(self) -> None:
        """Place the cards for the current state (the bar is drawn, not gridded)."""
        state, mode = self._state, self._layout_mode
        margin, gutter, scale = self._margin, self._gutter, self._scale

        # ---- window rows: only the rows used by the state carry a weight
        for row in range(5):
            self.rowconfigure(row, weight=0, minsize=0)
        for row, weight in ROW_WEIGHTS[state].items():
            self.rowconfigure(row, weight=weight)
        self.columnconfigure(0, weight=1, minsize=0)
        self.columnconfigure(1, weight=0, minsize=0)
        self._bg_canvas.grid(row=0, column=0, rowspan=5, columnspan=2, sticky="nsew")

        # ---- the three cards only exist in the results state
        if state != RESULTS:
            for card in self._result_cards:
                card.grid_remove()
            return

        # Row 0 reserves the strip that holds the bar (+ its message line), so
        # the cards never cover the pill drawn on the canvas.
        self.rowconfigure(0, minsize=self._bar_geometry()[3] + gutter)

        if mode == "wide":
            # Info card left, temperature card right, forecast band underneath.
            self.columnconfigure(0, weight=4)
            self.columnconfigure(1, weight=6)
            self._info_card.grid(row=1, column=0, columnspan=1, sticky="nsew",
                                 padx=(margin, gutter // 2), pady=(0, gutter))
            self._temp_card.grid(row=1, column=1, columnspan=1, sticky="nsew",
                                 padx=(gutter // 2, margin), pady=(0, gutter))
            self._forecast_card.grid(row=2, column=0, columnspan=2, sticky="nsew",
                                     padx=margin, pady=(0, margin))
        else:
            # Temperature card on top, info card below, forecast band at the end.
            self._temp_card.grid(row=1, column=0, columnspan=2, sticky="nsew",
                                 padx=margin, pady=(0, gutter))
            self._info_card.grid(row=2, column=0, columnspan=2, sticky="nsew",
                                 padx=margin, pady=(0, gutter))
            self._forecast_card.grid(row=3, column=0, columnspan=2, sticky="nsew",
                                     padx=margin, pady=(0, margin))

    def _bar_geometry(self) -> tuple[int, int, int, int]:
        """Pixel box of the search pill inside the full-window canvas.

        Home / first error: centred horizontally *and* vertically (a visible
        message shares the free space).  Results (and an error shown after a
        result): pinned to the top, ~BAR_TOP_MARGIN * scale under the edge, at
        the very same size - the bar never grows between the two states.
        """
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        bar_w = min(self._bar_width, max(1, width - 2 * self._margin))
        bar_h = max(1, self._search_height)
        x0 = max(0, (width - bar_w) // 2)
        if self._bar_pinned_top:
            y0 = self._bar_top
        else:
            shift = self._message_block() // 2 if (
                self._message or self._error_text) else 0
            y0 = max(0, (height - bar_h) // 2 - shift)
        return x0, y0, x0 + bar_w, y0 + bar_h

    def _message_block(self) -> int:
        """Height reserved for the status / error line under the bar."""
        if not (self._message or self._error_text):
            return 0
        return (max(6, int(round(8 * self._scale)))
                + self.f_error.metrics("linespace")
                + max(4, int(round(6 * self._scale))))

    # ------------------------------------------------------------- gradient
    def _gradient_mask(self, width: int, height: int) -> Image.Image:
        """Small diagonal mask, cached by (halved) size."""
        key = (max(2, width // 2), max(2, height // 2))
        if key != self._mask_key or self._mask_small is None:
            self._mask_small = self._mask_base.resize(key, Image.BILINEAR)
            self._mask_key = key
        return self._mask_small

    def _compose_gradient(self, width: int, height: int,
                          top: str, bottom: str) -> Image.Image:
        """Colourise the mask (cheap) then stretch it to the window size."""
        colored = ImageOps.colorize(self._gradient_mask(width, height), top, bottom)
        return colored.convert("RGB").resize((width, height), Image.BILINEAR)

    def _gradient_window(self) -> Image.Image:
        """The full-window gradient, or a solid stand-in before the first paint."""
        if self._grad_image is None:
            return Image.new("RGB", (max(1, self.winfo_width()),
                                     max(1, self.winfo_height())),
                             _hex_to_rgb(self._grad_top))
        return self._grad_image

    def _gradient_crop(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """RGBA slice of the window gradient behind the given pixel box.

        A stale gradient (window resized a moment ago) is stretched rather
        than cropped short, so a repaint can never produce a smaller image.
        """
        grad = self._gradient_window()
        left = int(_clamp(x, 0, max(0, grad.width - 1)))
        top = int(_clamp(y, 0, max(0, grad.height - 1)))
        right = int(_clamp(x + width, left + 1, grad.width))
        bottom = int(_clamp(y + height, top + 1, grad.height))
        piece = grad.crop((left, top, right, bottom)).convert("RGBA")
        if piece.size != (width, height):
            piece = piece.resize((width, height), Image.BILINEAR)
        return piece

    def _rebuild_gradient(self) -> None:
        width = max(1, self._bg_canvas.winfo_width())
        height = max(1, self._bg_canvas.winfo_height())
        if width <= 1 or height <= 1:
            return
        self._grad_image = self._compose_gradient(
            width, height, self._grad_top, self._grad_bottom)
        photo = ImageTk.PhotoImage(self._grad_image)
        self._bg_photo = photo
        if self._bg_item is None:
            self._bg_item = self._bg_canvas.create_image(0, 0, anchor="nw", image=photo)
        else:
            self._bg_canvas.itemconfigure(self._bg_item, image=photo)
        # Average of the gradient for the window *and* the canvas: the strips
        # not covered by the image yet (startup, resize) never flash grey.
        average = blend(self._grad_top, self._grad_bottom, 0.5)
        self.configure(bg=average)
        self._bg_canvas.configure(bg=average)

    # ------------------------------------------------------------- theming
    def set_theme(self, icon_code: Optional[str], animate: bool = True) -> None:
        """Switch the gradient to the theme matching *icon_code*."""
        key = theme_for_icon(icon_code)
        theme = THEMES[key]
        target = (str(theme["top"]), str(theme["bottom"]),
                  str(theme["overlay"]), float(theme["alpha"]))
        self._theme = key
        current = (self._grad_top, self._grad_bottom, self._overlay, self._alpha)
        if not animate or current == target:
            self._apply_theme(*target)
            return
        self._fade_theme(current, target)

    def _apply_theme(self, top: str, bottom: str, overlay: str, alpha: float) -> None:
        self._grad_top, self._grad_bottom = top, bottom
        self._overlay, self._alpha = overlay, alpha
        self._rebuild_gradient()
        self._paint_all()

    def _fade_theme(self, current: tuple, target: tuple) -> None:
        """Smoothly interpolate colours + opacity over ~FADE_MS."""
        if self._fade_after is not None:
            self.after_cancel(self._fade_after)
            self._fade_after = None
        pixels = max(1, self.winfo_width()) * max(1, self.winfo_height())
        steps = max(4, FADE_MS // FADE_FRAME_MS)
        if pixels > 3_200_000:                  # large screens: fewer redraws
            steps = max(3, steps // 2)
        index = 0

        def step() -> None:
            nonlocal index
            index += 1
            ratio = min(1.0, index / steps)
            self._apply_theme(
                blend(current[0], target[0], ratio),
                blend(current[1], target[1], ratio),
                blend(current[2], target[2], ratio),
                current[3] + (target[3] - current[3]) * ratio)
            if ratio < 1.0:
                self._fade_after = self.after(FADE_FRAME_MS, step)
            else:
                self._fade_after = None

        step()

    # ------------------------------------------------------- colour helpers
    def _gradient_pixel(self, x: float, y: float) -> str:
        """Color of the composed gradient at a window coordinate."""
        image = self._grad_image
        if image is None:
            return self._grad_top
        x = int(_clamp(x, 0, image.width - 1))
        y = int(_clamp(y, 0, image.height - 1))
        try:
            pixel = image.getpixel((x, y))
        except Exception:
            return self._grad_top
        return _rgb_to_hex(pixel[:3])

    def _glass_rgba(self, hover: bool = False,
                    boost: float = 0.0) -> tuple[int, int, int, int]:
        """RGBA fill of a frosted card (overlay colour + opacity)."""
        alpha = self._alpha + boost + (HOVER_BOOST if hover else 0.0)
        alpha = float(_clamp(alpha, 0.0, 0.65))
        r, g, b = _hex_to_rgb(self._overlay)
        return r, g, b, int(round(alpha * 255))

    def _gradient_slice(self, widget: tk.Misc, width: int,
                        height: int) -> Image.Image:
        """RGBA slice of the window gradient sitting behind *widget*."""
        grad = self._gradient_window()
        dx = int(widget.winfo_rootx() - self._bg_canvas.winfo_rootx())
        dy = int(widget.winfo_rooty() - self._bg_canvas.winfo_rooty())
        dx = int(_clamp(dx, 0, max(0, grad.width - width)))
        dy = int(_clamp(dy, 0, max(0, grad.height - height)))
        return grad.crop((dx, dy, dx + width, dy + height)).convert("RGBA")

    def _card_composite(self, card: Card) -> str:
        """Opaque-equivalent colour of a card at its centre."""
        width = max(1, card.winfo_width())
        height = max(1, card.winfo_height())
        x = card.winfo_rootx() - self._bg_canvas.winfo_rootx() + width // 2
        y = card.winfo_rooty() - self._bg_canvas.winfo_rooty() + height // 2
        base = self._gradient_pixel(x, y)
        if card.glass is not None:
            r, g, b, a = card.glass
            return blend(base, _rgb_to_hex((r, g, b)), a / 255.0)
        alpha = _clamp(self._alpha + card.alpha_boost, 0.0, 0.65)
        return blend(base, self._overlay, alpha)

    def _text_colors(self, card: Card) -> tuple[str, str]:
        """(main, secondary) text colours for a card, for good contrast."""
        fill = self._card_composite(card)
        main = INK if luminance(fill) > 0.62 else TEXT_ON_DARK
        secondary = blend(fill, main, 0.72)
        return main, secondary

    # --------------------------------------------------------------- icons
    def _icon_source(self, name: str) -> Optional[Image.Image]:
        if name not in self._icon_sources:
            try:
                with Image.open(os.path.join(ICONS_DIR, f"{name}.png")) as image:
                    self._icon_sources[name] = image.convert("RGBA")
            except Exception:
                self._icon_sources[name] = None      # missing file: non-fatal
        return self._icon_sources[name]

    def _icon(self, name: str, size: int, tint: Optional[str] = None
              ) -> Optional[ImageTk.PhotoImage]:
        """Load + resize an icon, cached per (name, size, tint)."""
        size = max(6, int(size))
        key = (name, size, tint)
        if key in self._icon_cache:
            return self._icon_cache[key]
        source = self._icon_source(name)
        photo: Optional[ImageTk.PhotoImage] = None
        if source is not None:
            image = source
            if tint is not None:
                r, g, b = _hex_to_rgb(tint)
                image = Image.new("RGBA", source.size, (r, g, b, 0))
                image.putalpha(source.getchannel("A"))
            scale = size / max(source.size)
            image = image.resize((max(1, round(source.width * scale)),
                                  max(1, round(source.height * scale))), Image.LANCZOS)
            try:
                photo = ImageTk.PhotoImage(image)
            except Exception:
                photo = None
        self._icon_cache[key] = photo
        return photo

    def _draw_icon(self, canvas: tk.Canvas, name: str, size: int, x: float, y: float,
                   tint: Optional[str] = None) -> None:
        """Draw an icon centred at (x, y); silently skip if it is missing."""
        if not name:
            return
        photo = self._icon(name, size, tint)
        if photo is not None:
            canvas.create_image(x, y, image=photo, anchor="center", tags="content")

    # ------------------------------------------------------- painting entry
    def _paint_all(self) -> None:
        """Repaint the bar, the status message and the cards for this state."""
        self._paint_bar()
        self._paint_message()
        if self._state == RESULTS:
            self._paint_cards()

    def _paint_bar(self) -> None:
        """Draw the whole search pill on the single full-window canvas.

        The pill is one *opaque* Pillow bar (the slice of gradient sitting
        behind it + 20 % white), drawn at x4 and reduced with LANCZOS for
        smooth corners.  The magnifier, the thin separator and the °C/°F case
        are part of that single image; the unit labels are canvas texts; the
        Entry is a canvas window coloured with *exactly* the pill colour, so
        no widget background, border or focus ring can ever be seen.
        """
        canvas = self._bg_canvas
        if self.winfo_width() <= 1 or canvas.winfo_width() <= 1:
            return
        box, layout, fill, main, secondary = self._bar_style()
        self._bar_fill, self._bar_main = fill, main
        photo = ImageTk.PhotoImage(self._compose_bar(box, layout, fill, main))
        self._bar_photo = photo                      # keep a reference alive

        canvas.delete("bar_draw")
        self._bar_item = canvas.create_image(box[0], box[1], anchor="nw",
                                             image=photo, tags=("bar_draw", "bar"))
        # ---- °C / °F labels: canvas text, above the image but *below* the
        # invisible hit area, so every click reaches the tag binding.
        for index, label in enumerate(("°C", "°F")):
            center_x = layout["unit_x0"] + layout["seg_w"] * (index + 0.5)
            if index == self._unit_index():
                color, font = WHITE, self.f_pill
            else:
                color, font = secondary, self.f_pill_idle
            if not self._unit_enabled:
                color = blend(fill, color, 0.5)
            canvas.create_text(center_x, layout["cy"], text=label, fill=color,
                               font=font, tags="bar_draw")
        # ---- invisible (but pickable) hit area covering the two segments
        self._unit_hit_item = canvas.create_rectangle(
            layout["unit_x0"], box[1], layout["unit_x1"], box[3],
            fill="", outline="", tags=("bar_draw", "unit_hit"))
        self._unit_zone = (layout["unit_x0"], layout["seg_w"])
        # ---- the field: exactly the pill colour, all round
        fg = PLACEHOLDER_HINT if self._placeholder_shown else main
        self._entry.configure(
            bg=fill, disabledbackground=fill, disabledforeground=main, fg=fg,
            insertbackground=main, highlightbackground=fill, highlightcolor=fill,
            highlightthickness=0, bd=0, relief="flat")
        canvas.itemconfigure(
            self._entry_window,
            width=max(1, int(layout["field_x1"] - layout["field_x0"])),
            height=max(1, int(layout["entry_h"])))
        canvas.coords(self._entry_window, layout["field_x0"], layout["cy"])
        canvas.tag_raise(self._entry_window)         # the field stays on top

    def _bar_style(self) -> tuple:
        """``(box, layout, fill, main, secondary)`` of the pill, right now."""
        box = self._bar_geometry()
        layout = self._bar_layout(*box)
        # Opaque fill = gradient where the field sits + 20 % white: one flat
        # colour shared by the pill and by the Entry placed inside it.
        fill = blend(self._gradient_pixel(int(layout["field_cx"]),
                                          int(layout["cy"])),
                     WHITE, PILL_FILL_ALPHA)
        main, secondary = self._bar_text_colors(fill)
        return box, layout, fill, main, secondary

    @staticmethod
    def _bar_text_colors(fill: str) -> tuple[str, str]:
        """(main, 70 % label) colours for the text drawn on the search pill."""
        main = INK if luminance(fill) > 0.62 else TEXT_ON_DARK
        return main, blend(fill, main, SEGMENT_TEXT_ALPHA)

    def _paint_message(self) -> None:
        """Status line (loading) or error line, right under the pill."""
        canvas = self._bg_canvas
        if self._message_item is not None:
            canvas.delete(self._message_item)
            self._message_item = None
        text, color = self._message, _message_color(self._grad_top, self._grad_bottom)
        if self._error_text:
            text, color = self._error_text, ERROR_COLOR
        if text and canvas.winfo_width() > 1:
            x0, _y0, x1, y1 = self._bar_geometry()
            gap = max(6, int(round(8 * self._scale)))
            self._message_item = canvas.create_text(
                (x0 + x1) / 2, y1 + gap + self.f_error.metrics("linespace") / 2,
                text=text, fill=color, font=self.f_error, tags="message")

    def _paint_cards(self) -> None:
        """Repaint every visible result card at the current fade opacity."""
        for card in self._result_cards:
            card.repaint(self._opacity)

    # ---------------------------------------------------- content: search
    def _bar_layout(self, x0: int, y0: int, x1: int, y1: int) -> dict:
        """Pixel geometry of everything drawn inside the search pill.

        Left to right: magnifier | field | thin separator | °C / °F.  On a
        narrow window the paddings shrink first: the toggle always stays
        inside the same pill, it is never moved out of the bar.
        """
        scale = self._scale
        width, height = x1 - x0, y1 - y0
        cy = (y0 + y1) / 2
        pad = self._search_pad_x
        icon = max(12, int(round(height * 0.42)))
        gap = max(5, int(round(pad * 0.5)))
        seg_w = (max(int(round(46 * scale)), self.f_pill.measure("°C"),
                     self.f_pill.measure("°F")) + int(round(10 * scale)))
        field_min = max(int(round(60 * scale)), 48)
        inset = max(3, int(round(4 * scale)))

        def room() -> int:
            """Width left for the field with the current paddings."""
            return width - 2 * pad - icon - 3 * gap - 2 * seg_w

        while pad > 4 and room() < field_min:        # narrow window: pad first
            pad -= 2
        while gap > 2 and room() < field_min:        # then the small gaps
            gap -= 1
        if room() < field_min:                       # extreme: magnifier yields
            icon = 0

        unit_x1 = x1 - pad
        unit_x0 = unit_x1 - 2 * seg_w
        field_x0 = x0 + pad + (icon + gap if icon else 0)
        field_x1 = max(field_x0 + 8, unit_x0 - gap)
        return {
            "cy": cy,
            "inset": inset,
            "icon": icon,
            "magnify_cx": x0 + pad + icon / 2,
            "field_x0": field_x0,
            "field_x1": field_x1,
            "field_cx": (field_x0 + field_x1) / 2,
            "entry_h": height - 2 * inset,
            "unit_x0": unit_x0,
            "unit_x1": unit_x1,
            "seg_w": seg_w,
            "sep_x": (field_x1 + unit_x0) / 2,      # rule between field/toggle
        }

    def _compose_bar(self, box: tuple[int, int, int, int], layout: dict,
                     fill: str, main: str) -> Image.Image:
        """Opaque Pillow rendering of the pill (drawn at x4, reduced LANCZOS).

        The layer keeps one *uniform* pill colour as its RGB and only shapes
        its alpha, so the reduction can never fringe it: inside the pill the
        result is exactly *fill*, the very colour given to the Entry.
        """
        x0, y0, x1, y1 = box
        width, height = max(1, x1 - x0), max(1, y1 - y0)
        ss = 4                                        # supersampling factor
        w4, h4 = width * ss, height * ss
        red, green, blue = _hex_to_rgb(fill)
        layer = Image.new("RGBA", (w4, h4), (red, green, blue, 0))
        draw = ImageDraw.Draw(layer)
        edge = ss // 2                                # half a pixel, at x4
        border_alpha = (PILL_BORDER_ALPHA_FOCUS if self._search_focused
                        else PILL_BORDER_ALPHA)
        draw.rounded_rectangle([edge, edge, w4 - edge - 1, h4 - edge - 1],
                               radius=(h4 - ss) / 2,  # full radius -> pill
                               fill=(red, green, blue, 255),
                               outline=(*_hex_to_rgb(
                                   blend(fill, WHITE, border_alpha / 255.0)), 255),
                               width=ss)

        # ---- magnifier (circle + handle, ~70 % white), drawn with Pillow
        if layout["icon"]:
            self._draw_magnifier_glyph(
                draw, (layout["magnify_cx"] - x0) * ss, (layout["cy"] - y0) * ss,
                layout["icon"] * ss,
                (*_hex_to_rgb(blend(fill, main, MAGNIFIER_ALPHA)), 255))

        # ---- thin vertical rule between the field and the toggle
        inset = layout["inset"] * ss
        sep_x = int(round((layout["sep_x"] - x0) * ss))
        draw.rectangle([sep_x, inset * 1.5, sep_x + ss - 1, h4 - inset * 1.5],
                       fill=(*_hex_to_rgb(
                           blend(fill, main, SEPARATOR_ALPHA)), 255))

        # ---- active unit: darker rounded case; hovered inactive unit: wash
        unit_x = (layout["unit_x0"] - x0) * ss
        seg_w = layout["seg_w"] * ss
        for index in range(2):
            if index == self._unit_index():
                case = blend(fill, "#000000", SEGMENT_ACTIVE_ALPHA)
            elif index == self._hover_segment and self._unit_enabled:
                case = blend(fill, WHITE, SEGMENT_HOVER_ALPHA)
            else:
                continue
            draw.rounded_rectangle(
                [unit_x + index * seg_w + inset, inset,
                 unit_x + (index + 1) * seg_w - inset, h4 - inset],
                radius=(h4 - 2 * inset) / 2, fill=(*_hex_to_rgb(case), 255))

        pill = layer.resize((width, height), Image.LANCZOS)
        return Image.alpha_composite(
            self._gradient_crop(x0, y0, width, height), pill).convert("RGB")

    @staticmethod
    def _draw_magnifier_glyph(draw: ImageDraw.ImageDraw, cx: float, cy: float,
                              size: float, colour: tuple) -> None:
        """Circle + handle (~45°), stroked in *colour*: no emoji, no icon file."""
        stroke = max(1, int(round(size * 0.13)))
        radius = size * 0.30
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                     outline=colour, width=stroke)
        diagonal = 0.7071                             # cos(45°) = sin(45°)
        draw.line([(cx + radius * diagonal, cy + radius * diagonal),
                   (cx + (radius + size * 0.18) * diagonal,
                    cy + (radius + size * 0.18) * diagonal)],
                  fill=colour, width=stroke)

    # ------------------------------------------------- search pill: events
    def _unit_index(self) -> int:
        """Index of the selected unit (0 = °C, 1 = °F)."""
        return 0 if self._unit == "metric" else 1

    def _segment_at(self, x: float) -> int:
        """Which half of the toggle the canvas coordinate *x* falls into."""
        unit_x, seg_w = self._unit_zone
        return 0 if x < unit_x + seg_w else 1

    def _on_bar_click(self, _event: tk.Event) -> None:
        """Anywhere on the pill (outside the toggle) gives the field focus."""
        try:
            self._entry.focus_set()
        except tk.TclError:
            pass

    def _on_bar_enter(self, _event: tk.Event) -> None:
        self._bg_canvas.configure(cursor="xterm")

    def _on_bar_leave(self, _event: tk.Event) -> None:
        self._bg_canvas.configure(cursor="")

    def _on_unit_enter(self, _event: tk.Event) -> None:
        self._bg_canvas.configure(cursor="hand2" if self._unit_enabled else "")

    def _on_unit_leave(self, _event: tk.Event) -> None:
        self._bg_canvas.configure(cursor="")
        if self._hover_segment is not None:
            self._hover_segment = None
            self._schedule_bar_repaint()

    def _on_unit_motion(self, event: tk.Event) -> None:
        if not self._unit_enabled:
            return
        index = self._segment_at(event.x)
        if index != self._hover_segment:
            self._hover_segment = index
            self._schedule_bar_repaint()

    def _on_unit_click(self, event: tk.Event) -> None:
        if not self._unit_enabled:
            return
        unit = ("metric", "imperial")[self._segment_at(event.x)]
        # Deferred: canvas items are never deleted from inside a binding.
        self.after_idle(lambda: self._on_unit_change(unit))

    def _schedule_bar_repaint(self) -> None:
        """Redraw the pill once the current canvas binding has returned."""
        if getattr(self, "_bar_repaint_pending", False) or self._closing:
            return
        self._bar_repaint_pending = True

        def run() -> None:
            self._bar_repaint_pending = False
            if not self._closing:
                self._paint_bar()

        self.after_idle(run)

    # ------------------------------------------------- content: temperature
    def _draw_temp_card(self, card: Card, width: int, height: int) -> None:
        main, secondary = self._text_colors(card)
        pad, shadow = card.pad, card.shadow
        inner_w = width - 2 * pad - shadow
        inner_h = height - 2 * pad - shadow
        center_x = pad + inner_w / 2
        top = pad

        # ---- big icon + temperature, one horizontal group (stacked when the
        # card is too narrow); the group is centred as a whole.
        icon_size = int(_clamp(min(inner_w, inner_h) * 0.32, 40, 300))
        temp_font = self.f_temp
        temp_w = temp_font.measure(self._temp_value)
        unit_text = "C" if self._unit == "metric" else "F"
        unit_gap = max(2, int(round(4 * self._scale)))
        unit_w = temp_font.measure(unit_text)
        gap = int(round(10 * self._scale))
        total = icon_size + gap + temp_w + unit_gap + unit_w
        stacked = total > inner_w

        # ---- vertical rhythm: the whole column (city, clock, weather,
        # description) is centred inside the glass rectangle, so the top and
        # bottom margins are always equal.
        v_gap = max(4, int(round(inner_h * 0.055)))
        line_city = self.f_city.metrics("linespace")
        line_clock = self.f_clock.metrics("linespace")
        line_desc = self.f_desc.metrics("linespace")
        line_temp = temp_font.metrics("linespace")
        weather_h = (icon_size + 2 * v_gap + line_temp) if stacked \
            else max(icon_size, line_temp)
        block = (line_city + v_gap + line_clock + 2 * v_gap
                 + weather_h + 2 * v_gap + line_desc)
        y = top + max(0.0, (inner_h - block) / 2)

        # ---- city + live date/time
        card.create_text(center_x, y + line_city / 2, text=self._city.title(),
                         anchor="center", font=self.f_city, fill=main, tags="content")
        y += line_city + v_gap
        card.create_text(center_x, y + line_clock / 2, text=self._clock_text,
                         anchor="center", font=self.f_clock, fill=secondary,
                         tags="content")
        y += line_clock + 2 * v_gap

        middle_y = y + weather_h / 2
        if not stacked:
            start = center_x - total / 2
            self._draw_icon(card, self._icon_name, icon_size,
                            start + icon_size / 2, middle_y)
            card.create_text(start + icon_size + gap, middle_y,
                             text=self._temp_value, anchor="w", font=temp_font,
                             fill=main, tags="content")
            # unit, same size as the digits, on the top-right of the number
            card.create_text(start + icon_size + gap + temp_w + unit_gap,
                             middle_y - line_temp / 2, text=unit_text,
                             anchor="nw", font=temp_font, fill=secondary,
                             tags="content")
        else:                                  # too narrow: icon above
            self._draw_icon(card, self._icon_name, icon_size,
                            center_x, y + icon_size / 2)
            temp_y = y + icon_size + 2 * v_gap + line_temp / 2
            text_x = center_x - (temp_w + unit_gap + unit_w) / 2
            card.create_text(text_x, temp_y, text=self._temp_value,
                             anchor="w", font=temp_font, fill=main, tags="content")
            card.create_text(text_x + temp_w + unit_gap, temp_y - line_temp / 2,
                             text=unit_text, anchor="nw", font=temp_font,
                             fill=secondary, tags="content")
        y += weather_h + 2 * v_gap

        # ---- description (the temperature card only exists with data)
        description = str(self._description).capitalize()
        card.create_text(center_x, y + line_desc / 2, text=description,
                         anchor="center", font=self.f_desc, fill=secondary,
                         tags="content")

    # -------------------------------------------------------- content: info
    def _draw_info_card(self, card: Card, width: int, height: int) -> None:
        main, secondary = self._text_colors(card)
        scale = self._scale
        pad, shadow = card.pad, card.shadow
        inner_w = width - 2 * pad - shadow
        inner_h = height - 2 * pad - shadow
        two_columns = self._layout_mode == "narrow"
        icon_size = int(_clamp(round(24 * scale), 16, 48))
        arrow_size = int(_clamp(round(16 * scale), 11, 34))
        gap = int(round(10 * scale))

        if two_columns:                        # compact 2 x 4 grid
            icon_size = int(_clamp(round(20 * scale), 14, 40))
            arrow_size = int(_clamp(round(14 * scale), 10, 30))
            col_gap = pad
            cell_w = (inner_w - col_gap) / 2
            row_h = inner_h / 4
            for index, (key, label, kind, value_key) in enumerate(INFO_ROWS):
                cell_x = pad + (index % 2) * (cell_w + col_gap)
                row_y = pad + row_h * (index // 2 + 0.5)
                self._draw_info_row(card, cell_x, cell_w, row_y, key, label, kind,
                                    value_key, icon_size, arrow_size, gap, main, secondary)
        else:                                  # full-width single column
            row_h = inner_h / len(INFO_ROWS)
            for index, (key, label, kind, value_key) in enumerate(INFO_ROWS):
                row_y = pad + row_h * (index + 0.5)
                self._draw_info_row(card, pad, inner_w, row_y, key, label, kind,
                                    value_key, icon_size, arrow_size, gap, main, secondary)

    def _draw_info_row(self, card: Card, x: float, width: float, y: float,
                       key: str, label: str, kind: str, value_key: Optional[str],
                       icon_size: int, arrow_size: int, gap: int,
                       main: str, secondary: str) -> None:
        """One detail line: icon, label, value (right aligned)."""
        icon_tint = main
        if key == "feels":
            self._draw_icon(card, self._icon_name, icon_size, x + icon_size / 2, y)
        elif key == "humidity":
            self._draw_icon(card, "humidity_icon", icon_size, x + icon_size / 2, y, icon_tint)
        elif key == "clouds":
            self._draw_icon(card, "clouds_icon", icon_size, x + icon_size / 2, y, icon_tint)
        elif key == "wind_dir":
            self._draw_icon(card, "orientation_icon", icon_size, x + icon_size / 2, y, icon_tint)
        elif key == "wind_speed":
            self._draw_icon(card, "wind_icon", icon_size, x + icon_size / 2, y, icon_tint)
        elif key == "minmax":
            # up + down arrow, side by side, centred inside the icon slot
            small = max(8, int(round(icon_size * 0.55)))
            mini_gap = max(2, int(round(icon_size * 0.12)))
            start = x + (icon_size - (2 * small + mini_gap)) / 2
            self._draw_icon(card, "fleche_haut", small, start + small / 2, y, ACCENT)
            self._draw_icon(card, "fleche_bas", small,
                            start + small + mini_gap + small / 2, y, icon_tint)
        elif key == "sunrise":
            self._draw_icon(card, "sunrise_icon", icon_size, x + icon_size / 2, y, ACCENT)
        elif key == "sunset":
            self._draw_icon(card, "sunset_icon", icon_size, x + icon_size / 2, y, icon_tint)

        card.create_text(x + icon_size + gap, y, text=label, anchor="w",
                         font=self.f_label, fill=secondary, tags="content")

        right = x + width
        if kind == "value":
            card.create_text(right, y, text=self._info_values.get(value_key or "", "—"),
                             anchor="e", font=self.f_value, fill=main, tags="content")
            return
        # Min / Max: two values with their arrows, right aligned as a group.
        max_text = self._info_values["max"]
        min_text = self._info_values["min"]
        font = self.f_value
        w_max, w_min = font.measure(max_text), font.measure(min_text)
        small = int(round(gap * 0.6))
        group = arrow_size + small + w_max + 2 * small + arrow_size + small + w_min
        cursor = right - group
        self._draw_icon(card, "fleche_haut", arrow_size, cursor + arrow_size / 2, y, ACCENT)
        cursor += arrow_size + small
        card.create_text(cursor, y, text=max_text, anchor="w", font=font, fill=main, tags="content")
        cursor += w_max + 2 * small
        self._draw_icon(card, "fleche_bas", arrow_size, cursor + arrow_size / 2, y, main)
        cursor += arrow_size + small
        card.create_text(cursor, y, text=min_text, anchor="w", font=font, fill=main, tags="content")

    # ---------------------------------------------------- content: forecast
    def _draw_forecast_card(self, card: Card, width: int, height: int) -> None:
        main, secondary = self._text_colors(card)
        pad, shadow = card.pad, card.shadow
        inner_w = width - 2 * pad - shadow
        inner_h = height - 2 * pad - shadow
        columns = 5
        col_w = inner_w / columns
        icon_size = int(_clamp(round(40 * self._scale), 20, 96))

        # hovered column highlight (drawn first so it stays behind the text)
        if self._fc_hover is not None:
            x0 = pad + col_w * self._fc_hover
            highlight = blend(self._card_composite(card), main, 0.10)
            card.create_rectangle(x0 + 2, pad, x0 + col_w - 2, pad + inner_h,
                                  fill=highlight, outline="", tags="content")

        # thin separators between the columns
        separator = blend(self._card_composite(card), main, 0.20)
        for index in range(1, columns):
            x = pad + col_w * index
            card.create_line(x, pad + inner_h * 0.14, x, pad + inner_h * 0.86,
                             fill=separator, tags="content")

        for index in range(columns):
            center_x = pad + col_w * (index + 0.5)
            if index < len(self._forecast):
                day = self._forecast[index]
                day_name = str(day["day"])
                icon_name = str(day["icon"])
                temp_text = f'{day["min"]}° / {day["max"]}°'
            else:
                day_name, icon_name, temp_text = "—", "", "—"
            card.create_text(center_x, pad + inner_h * 0.18, text=day_name, anchor="center",
                             font=self.f_day, fill=main, tags="content")
            self._draw_icon(card, icon_name, icon_size, center_x, pad + inner_h * 0.50)
            card.create_text(center_x, pad + inner_h * 0.82, text=temp_text, anchor="center",
                             font=self.f_day_temp, fill=secondary, tags="content")

    def _on_forecast_motion(self, event: tk.Event) -> None:
        card = self._forecast_card
        inner_w = max(1, card.winfo_width() - 2 * card.pad - card.shadow)
        column = int((event.x - card.pad) // (inner_w / 5))
        column = column if 0 <= column < 5 else None
        if column != self._fc_hover:
            self._fc_hover = column
            card.repaint()

    def _on_forecast_leave(self, _event: tk.Event) -> None:
        if self._fc_hover is not None:
            self._fc_hover = None
            self._forecast_card.repaint()

    # ---------------------------------------------------------------- states
    def _show_home(self, home: bool = False) -> None:
        """State 1: only the bar, centered.  No card, no icon, no sentence."""
        self._state = HOME
        self._bar_pinned_top = False        # the pill is centred again
        self._has_data = False
        self._error_text = ""
        self._message = ""
        self._stop_clock()
        self._cancel_card_fade()
        self._apply_metrics()
        self._apply_grid()
        self.update_idletasks()
        self._rebuild_gradient()
        self.set_theme(DEFAULT_THEME, animate=not home)   # home = clear day
        self._paint_all()
        if home:
            self._city = ""
            self._show_placeholder()
        elif not self._entry_value():
            self._show_placeholder()
        self._entry.focus_set()

    def _show_results(self) -> None:
        """State 2: bar at the top, cards fade in over the weather gradient."""
        was_results = self._state == RESULTS
        self._state = RESULTS
        self._bar_pinned_top = True         # pill pinned under the top edge
        self._has_data = True
        self._error_text = ""
        self._message = ""
        self._cancel_card_fade()
        self._apply_metrics()
        self._apply_grid()                 # bar jumps to the top of the window
        self.update_idletasks()
        self._rebuild_gradient()
        if was_results:
            self._opacity = 1.0            # content swap only, no animation
            self._paint_all()
            self.set_theme(self._icon_name, animate=True)
        else:
            self._opacity = 1.0            # grid + paint at full opacity...
            self._paint_all()
            self.set_theme(self._icon_name, animate=True)
            self._fade_cards_in()          # ...then animate 0 -> 1

    def _show_error(self, message: str) -> None:
        """State 3: one message under the bar, every card hidden."""
        self._state = ERROR
        self._error_text = message
        self._message = ""
        self._has_data = False
        self._stop_clock()                 # no timers while nothing is shown
        self._cancel_card_fade()
        self._apply_grid()
        self.update_idletasks()
        self._rebuild_gradient()
        self._paint_all()
        self._entry.focus_set()

    # ------------------------------------------------------------- searching
    def _entry_value(self) -> str:
        """The typed city, ignoring the placeholder shown while the field is idle."""
        text = self._entry.get().strip()
        return "" if text == PLACEHOLDER or self._placeholder_shown else text

    def _show_placeholder(self) -> None:
        """Display the greyed-out hint without ever treating it as input."""
        self._placeholder_shown = True
        self._entry.delete(0, "end")
        self._entry.insert(0, PLACEHOLDER)
        self._entry.configure(fg=PLACEHOLDER_HINT)

    def _hide_placeholder(self) -> None:
        """Remove the hint as soon as the user types or a city is picked."""
        if not self._placeholder_shown:
            return
        self._placeholder_shown = False
        self._entry.delete(0, "end")
        self._entry.configure(fg=self._bar_main)

    def _on_entry_focus_in(self, _event: tk.Event) -> None:
        """Lighten the pill border while the field is active (no accent).

        Clicking the pill also clears the hint and puts the caret at the very
        left, so the field is immediately ready to type a city name.
        """
        self._search_focused = True
        self._hide_placeholder()
        try:
            self._entry.icursor(0)
        except tk.TclError:
            pass
        self._paint_bar()

    def _on_entry_key(self, _event: tk.Event) -> None:
        """First keystroke on the hint clears it (focus alone does not)."""
        if self._placeholder_shown and _event.keysym not in ("Left", "Right", "Home",
                                                            "End", "Tab", "Escape"):
            self._hide_placeholder()

    def _on_entry_focus_out(self, _event: tk.Event) -> None:
        self._search_focused = False
        if not self._entry_value():
            self._show_placeholder()
        self._paint_bar()              # border dims + placeholder colour

    def _on_unit_change(self, unit: str) -> None:
        """Switch unit, then re-search only when a city is known."""
        self._unit = unit
        self._paint_bar()                   # the darker case moves
        city = self._entry_value() or self._city
        if self._loading:
            return
        if city:
            self._search(city)
        else:
            # Empty field: just change the selected unit, no query, no error.
            self._entry.focus_set()

    def _search(self, city: Optional[str] = None) -> None:
        """Validate the field, then run the request on a worker thread."""
        if self._loading:
            return
        city = (city or self._entry_value()).strip()
        if not city:                       # empty / spaces: never send a query
            self._show_error(MESSAGE_EMPTY)
            return
        self._city = city
        self._hide_placeholder()           # the field now holds a real city
        self._entry.delete(0, "end")
        self._entry.insert(0, city)
        self._request_seq += 1
        sequence = self._request_seq
        self._set_loading(True)
        threading.Thread(target=self._worker, args=(sequence, city, self._unit),
                         daemon=True).start()
        self._poll_results()

    def _worker(self, sequence: int, city: str, unit: str) -> None:
        """Network work, off the UI thread (result pushed to a queue)."""
        try:
            infos = weather_api.get_weather(city, unit)
            hourly = weather_api.get_previsional_weather(city, unit)
            current_icon = ""
            for info in hourly.values():
                current_icon = info["icon"]
                break
            self._results.put((sequence, infos, _summarise_forecast(hourly),
                               current_icon, None))
        except Exception as exc:            # noqa: BLE001 - reported to the user
            self._results.put((sequence, None, None, None, exc))

    def _poll_results(self) -> None:
        """Fetch worker results on the UI thread (after() based polling)."""
        if self._poll_after is not None:
            self.after_cancel(self._poll_after)
            self._poll_after = None
        try:
            while True:
                sequence, infos, forecast, current_icon, exc = self._results.get_nowait()
                if sequence != self._request_seq:
                    continue                # stale answer -> ignore
                self._set_loading(False)
                if exc is not None:
                    self._show_error(_error_message(exc))
                else:
                    self._render_weather(infos, forecast, current_icon)
        except queue.Empty:
            pass
        if self._loading:
            self._poll_after = self.after(80, self._poll_results)

    def _set_loading(self, loading: bool) -> None:
        """Disable the controls and show the discreet "Searching..." line."""
        self._loading = loading
        self._entry.configure(state="disabled" if loading else "normal")
        self._unit_enabled = not loading
        if loading:
            self._error_text = ""
            self._message = MESSAGE_LOADING
        elif self._message == MESSAGE_LOADING:
            self._message = ""
        self._hover_segment = None
        self._paint_bar()                   # pill re-centres above the message,
        self._paint_message()               # toggle labels dim while loading

    def show_error(self, message: str) -> None:
        """Public helper: go to the error state (or back to home for "")."""
        if message:
            self._show_error(message)
        else:
            self._show_home()

    # -------------------------------------------------------- state changes
    def _fade_cards_in(self) -> None:
        """Fade the cards in from the bare gradient (~CARD_FADE_MS)."""
        steps = max(3, CARD_FADE_MS // CARD_FADE_FRAME_MS)

        def step(index: int) -> None:
            if self._closing:
                return
            if index >= steps or self._state != RESULTS:
                self._opacity = 1.0
                self._paint_cards()
                self._card_fade_after = None
                return
            self._opacity = index / steps
            self._paint_cards()
            self._card_fade_after = self.after(
                CARD_FADE_FRAME_MS, lambda: step(index + 1))

        self._card_fade_after = self.after(CARD_FADE_FRAME_MS, lambda: step(1))

    def _cancel_card_fade(self) -> None:
        if self._card_fade_after is not None:
            self.after_cancel(self._card_fade_after)
            self._card_fade_after = None

    # ------------------------------------------------------------- rendering
    def _render_weather(self, infos: dict, forecast: list[dict],
                        current_icon: Optional[str]) -> None:
        self._icon_name = current_icon or ""
        self._description = infos["description"]

        symbol = "°C" if self._unit == "metric" else "°F"
        timezone_offset = infos["timezone"]
        direction = utils.wind_deg_to_direction(infos["wind_orientation"])
        if self._unit == "metric":              # convert first, round afterwards
            wind_text = f"{round(utils.wind_speed_to_km_h(infos['wind_speed']))} km/h"
        else:
            wind_text = f"{round(infos['wind_speed'])} mph"

        self._temp_value = f"{round(infos['temperature'])}°"
        self._info_values = {
            "feels": f"{round(infos['felt_temp'])}{symbol}",
            "max": f"{round(infos['max_temp'])}°",
            "min": f"{round(infos['min_temp'])}°",
            "humidity": f"{infos['humidity']} %",
            "clouds": f"{infos['clouds']} %",
            "wind_dir": direction,
            "wind_speed": wind_text,
            "sunrise": utils.to_time(infos["sunrise"], timezone_offset)[11:16],
            "sunset": utils.to_time(infos["sunset"], timezone_offset)[11:16],
        }
        self._render_forecast(forecast)
        self._show_results()                # switch state first...
        self._start_clock(timezone_offset)   # ...then run the live clock

    def _render_forecast(self, forecast: list[dict]) -> None:
        """Keep only the 5 next days and pre-compute their display strings."""
        days: list[dict] = []
        for day in forecast[:5]:
            try:
                day_name = datetime.strptime(day["date"], "%Y-%m-%d").strftime("%a")
            except ValueError:
                day_name = day["date"]
            days.append({"day": day_name, "icon": day["icon"],
                         "min": day["min_temp"], "max": day["max_temp"]})
        self._forecast = days

    # ---------------------------------------------------------------- clock
    def _start_clock(self, timezone_offset: int) -> None:
        """(Re)start the live local clock without stacking timers."""
        self._tz_offset = timezone_offset
        self._stop_clock()
        self._clock_text = self._format_clock()
        self._tick()

    def _format_clock(self) -> str:
        """Current local time of the searched city."""
        now = datetime.now(timezone(timedelta(seconds=self._tz_offset)))
        return now.strftime("%a %d %b · %H:%M:%S")

    def _stop_clock(self) -> None:
        """Cancel the clock timer (called when the cards are hidden)."""
        if self._clock_after is not None:
            self.after_cancel(self._clock_after)
            self._clock_after = None

    def _tick(self) -> None:
        if self._closing or self._state != RESULTS:
            return
        self._clock_text = self._format_clock()
        self._temp_card.repaint(self._opacity)
        self._clock_after = self.after(1000, self._tick)

    # ---------------------------------------------------------------- close
    def _on_close(self) -> None:
        self._closing = True
        for after_id in (self._resize_after, self._fade_after,
                         self._card_fade_after, self._clock_after,
                         self._poll_after):
            if after_id is not None:
                try:
                    self.after_cancel(after_id)
                except tk.TclError:
                    pass
        self.destroy()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def _enable_dpi_awareness() -> None:
    """Windows HiDPI: must run before the Tk window is created."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)   # type: ignore[attr-defined]
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()    # type: ignore[attr-defined]
        except Exception:
            pass


def display_weather() -> None:
    """Create and run the weather dashboard (called by main.py)."""
    _enable_dpi_awareness()
    app = WeatherApp()
    app.mainloop()


if __name__ == "__main__":
    display_weather()
