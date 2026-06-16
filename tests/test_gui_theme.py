"""Tests for the theme tokens and QSS rendering."""

from gui.theme import theme
from gui.theme.tokens import DARK, LIGHT, palette_for_scheme


def test_light_and_dark_palettes_are_distinct():
    assert LIGHT != DARK
    # Both palettes expose exactly the same token set.
    assert set(LIGHT) == set(DARK)


def test_palette_for_scheme_selects_by_mode():
    assert palette_for_scheme(False) is LIGHT
    assert palette_for_scheme(True) is DARK


def test_qss_substitutes_every_token():
    for palette in (LIGHT, DARK):
        rendered = theme.qss(palette)
        # No leftover `$token` placeholders survived substitution.
        assert "$" not in rendered
        assert "QTableView" in rendered
