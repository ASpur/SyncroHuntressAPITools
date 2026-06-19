"""Tests for the comparison view: proxy filters, stat cards, settings dialog."""

import pytest

from const import STATUS_MISSING_HUNTRESS, STATUS_MISSING_SYNCRO, STATUS_OK
from gui.widgets.comparison_widget import DEFAULT_SELECTION
from services.comparison import ComparisonRow


@pytest.fixture
def rows():
    return [
        ComparisonRow("A-OK", "A-OK", STATUS_OK, "Acme"),
        ComparisonRow("BW-REC", "", STATUS_MISSING_HUNTRESS, "Brightwell"),
        ComparisonRow("", "WEB-01", STATUS_MISSING_SYNCRO, "Acme"),
        ComparisonRow("C-OK", "C-OK", STATUS_OK, "Cascade"),
    ]


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    """Point SettingsModel at a temp file so tests never touch the real one."""
    from gui.models.settings_model import SettingsModel

    monkeypatch.setattr(SettingsModel, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    return SettingsModel()


class TestProxyFilter:
    def _model(self, rows):
        from gui.models.comparison_model import (
            ComparisonFilterProxyModel,
            ComparisonTableModel,
        )

        model = ComparisonTableModel()
        model.setData(rows)
        proxy = ComparisonFilterProxyModel()
        proxy.setSourceModel(model)
        return model, proxy

    def test_union_status_filter(self, qapp, rows):
        _, proxy = self._model(rows)
        proxy.set_status_filter({STATUS_MISSING_HUNTRESS, STATUS_MISSING_SYNCRO})
        assert proxy.rowCount() == 2

    def test_single_status_filter(self, qapp, rows):
        _, proxy = self._model(rows)
        proxy.set_status_filter({STATUS_MISSING_SYNCRO})
        assert proxy.rowCount() == 1

    def test_empty_status_filter_shows_all(self, qapp, rows):
        _, proxy = self._model(rows)
        proxy.set_status_filter(set())
        assert proxy.rowCount() == 4

    def test_ignored_only_mode(self, qapp, rows):
        model, proxy = self._model(rows)
        model.set_ignored({"bw-rec"})
        proxy.set_only_ignored(True)
        assert proxy.rowCount() == 1


class TestComparisonWidget:
    def _widget(self, isolated_settings):
        from gui.widgets.comparison_widget import ComparisonWidget

        return ComparisonWidget(isolated_settings)

    def test_default_filter_is_problems_first(self, qapp, isolated_settings, rows):
        widget = self._widget(isolated_settings)
        widget._on_result(rows)
        assert widget._selected == set(DEFAULT_SELECTION)
        # Two non-OK rows visible by default.
        assert widget.proxy_model.rowCount() == 2
        # Both "missing" cards are highlighted; OK and Total are not.
        assert widget._cards["missing_huntress"].property("active") is True
        assert widget._cards["missing_syncro"].property("active") is True
        assert widget._cards["ok"].property("active") is False
        assert widget._cards["total"].property("active") is False

    def test_total_card_clears_selection(self, qapp, isolated_settings, rows):
        widget = self._widget(isolated_settings)
        widget._on_result(rows)
        widget._cards["total"].clicked.emit("total")
        assert widget._selected == set()
        assert widget.proxy_model.rowCount() == 4
        assert widget._cards["total"].property("active") is True

    def test_status_cards_multi_select(self, qapp, isolated_settings, rows):
        widget = self._widget(isolated_settings)
        widget._on_result(rows)
        widget._cards["total"].clicked.emit("total")  # clear
        widget._cards["ok"].clicked.emit("ok")
        assert widget.proxy_model.rowCount() == 2
        widget._cards["missing_syncro"].clicked.emit("missing_syncro")
        # OK (2) + Missing in Syncro (1) = 3 rows.
        assert widget.proxy_model.rowCount() == 3
        assert widget._cards["ok"].property("active") is True
        assert widget._cards["missing_syncro"].property("active") is True
        # Clicking an active card toggles it back off.
        widget._cards["ok"].clicked.emit("ok")
        assert widget._cards["ok"].property("active") is False
        assert widget.proxy_model.rowCount() == 1

    def test_ignored_toggle_view(self, qapp, isolated_settings, rows):
        widget = self._widget(isolated_settings)
        isolated_settings.add_ignored("bw-rec")
        widget._on_result(rows)
        assert widget.ignored_btn.isVisibleTo(widget.ignored_btn.parentWidget())
        assert widget.ignored_btn.text() == "1 ignored"
        widget._toggle_ignored_view()
        assert widget._only_ignored is True
        assert widget.proxy_model.rowCount() == 1
        assert widget.ignored_btn.property("active") is True
        # Toggling again returns to the problems-first default.
        widget._toggle_ignored_view()
        assert widget._only_ignored is False
        assert widget._selected == set(DEFAULT_SELECTION)

    def test_stat_card_counts(self, qapp, isolated_settings, rows):
        widget = self._widget(isolated_settings)
        widget._on_result(rows)
        assert widget._cards["total"]._value.text() == "4"
        assert widget._cards["missing_huntress"]._value.text() == "1"


class TestSettingsView:
    def test_save_warns_when_fields_missing(self, qapp, isolated_settings):
        from gui.widgets.settings_view import SettingsView

        view = SettingsView(isolated_settings)
        result = {"saved": False}
        view.saved.connect(lambda: result.update(saved=True))
        view._on_save()
        # Settings are persisted but saved is NOT emitted (user stays on
        # the settings page so they can read the warning).
        assert result["saved"] is False
        assert view.warning_label.isVisibleTo(view)
        assert view.warning_label.text()
        assert isolated_settings.get("UseFakeData") is False

    def test_save_no_warning_when_fake_data_enabled(self, qapp, isolated_settings):
        from gui.widgets.settings_view import SettingsView

        view = SettingsView(isolated_settings)
        view.fake_data_checkbox.setChecked(True)
        result = {"saved": False}
        view.saved.connect(lambda: result.update(saved=True))
        view._on_save()
        assert result["saved"] is True
        assert not view.warning_label.isVisibleTo(view)

    def test_valid_save_persists_and_emits(self, qapp, isolated_settings):
        from gui.widgets.settings_view import SettingsView

        view = SettingsView(isolated_settings)
        view.syncro_subdomain.setText("acme")
        view.syncro_api_key.setText("k1")
        view.huntress_api_key.setText("k2")
        view.huntress_secret.setText("s1")
        saved = {"value": False}
        view.saved.connect(lambda: saved.update(value=True))
        view._on_save()
        assert saved["value"] is True
        assert isolated_settings.get("SyncroSubDomain") == "acme"
        assert isolated_settings.validate()[0] is True
