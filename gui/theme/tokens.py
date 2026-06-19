"""Design tokens for the neutral dev-tool theme.

A palette is a flat ``{token: "#hex"}`` map. Two palettes exist (``LIGHT`` and
``DARK``); the active one is chosen from the OS color scheme in ``theme.py``.
Both expose the same keys so ``qss()`` and the table model can read either one
without branching. Status meaning is carried by a small colored dot, never a
full-row fill: OK = green, missing-in-Huntress = red, missing-in-Syncro = amber.
"""

from typing import Dict

Palette = Dict[str, str]

# Linear / Primer flavour: flat, near-monochrome neutrals, one calm accent, and
# three reserved status hues. Primary buttons are high-contrast monochrome, so
# their fill/text are derived from text/bg tokens rather than the accent.
LIGHT: Palette = {
    "bg_primary": "#ffffff",
    "bg_secondary": "#f7f7f4",
    "bg_tertiary": "#efeee9",
    "text_primary": "#1b1b19",
    "text_secondary": "#56564f",
    "text_tertiary": "#8a8a82",
    "border": "#e4e3dc",
    "border_strong": "#cfcdc4",
    "accent": "#2f6db3",
    "hover": "#f0efea",
    "selection_bg": "#e7eef7",
    "status_ok": "#1d9e75",
    "status_missing_huntress": "#d8453f",
    "status_missing_syncro": "#e0901a",
    "ignored_fg": "#9b9b93",
    # Primary (high-contrast) button.
    "primary_bg": "#1b1b19",
    "primary_fg": "#ffffff",
    "primary_bg_hover": "#141412",
}

DARK: Palette = {
    "bg_primary": "#1c1c1b",
    "bg_secondary": "#222221",
    "bg_tertiary": "#2a2a28",
    "text_primary": "#ececea",
    "text_secondary": "#a9a9a2",
    "text_tertiary": "#76766f",
    "border": "#33332f",
    "border_strong": "#45453f",
    "accent": "#5a9be0",
    "hover": "#2c2c2a",
    "selection_bg": "#2d3a4a",
    "status_ok": "#3ec298",
    "status_missing_huntress": "#ef625d",
    "status_missing_syncro": "#f0ab3c",
    "ignored_fg": "#6f6f68",
    "primary_bg": "#ececea",
    "primary_fg": "#1c1c1b",
    "primary_bg_hover": "#d8d8d6",
}


def palette_for_scheme(is_dark: bool) -> Palette:
    """Return the palette matching the OS color scheme."""
    return DARK if is_dark else LIGHT
