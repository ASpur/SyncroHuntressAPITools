"""Tests for the comparison view: proxy filters, stat cards, settings dialog."""

import pytest

from const import STATUS_MISSING_HUNTRESS, STATUS_MISSING_SYNCRO, STATUS_OK
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

    def test_not_ok_hides_ok_rows(self, qapp, rows):
        _, proxy = self._model(rows)
        proxy.set_status_filter("Not OK")
        assert proxy.rowCount() == 2

    def test_exact_status_filter(self, qapp, rows):
        _, proxy = self._model(rows)
        proxy.set_status_filter(STATUS_MISSING_SYNCRO)
        assert proxy.rowCount() == 1

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
        assert widget._active_filter == "issues"
        # Two non-OK rows visible by default.
        assert widget.proxy_model.rowCount() == 2
        # No stat card is highlighted for the composite "issues" default.
        assert not any(c.property("active") for c in widget._cards.values())

    def test_card_click_filters_and_highlights(self, qapp, isolated_settings, rows):
        widget = self._widget(isolated_settings)
        widget._on_result(rows)
        widget._cards["ok"].clicked.emit("ok")
        assert widget._active_filter == "ok"
        assert widget.proxy_model.rowCount() == 2
        assert widget._cards["ok"].property("active") is True

    def test_stat_card_counts(self, qapp, isolated_settings, rows):
        widget = self._widget(isolated_settings)
        widget._on_result(rows)
        assert widget._cards["all"]._value.text() == "4"
        assert widget._cards["missing_huntress"]._value.text() == "1"


class TestSettingsDialog:
    def test_save_blocked_when_fields_missing(self, qapp, isolated_settings):
        from gui.widgets.settings_dialog import SettingsDialog

        dialog = SettingsDialog(isolated_settings)
        result = {"accepted": False}
        dialog.accepted.connect(lambda: result.update(accepted=True))
        dialog._on_save()
        # isVisibleTo reflects the visibility flag even though the dialog is
        # never shown in a headless test.
        assert dialog.error_label.isVisibleTo(dialog)
        assert dialog.error_label.text()
        assert result["accepted"] is False

    def test_valid_save_persists_and_accepts(self, qapp, isolated_settings):
        from gui.widgets.settings_dialog import SettingsDialog

        dialog = SettingsDialog(isolated_settings)
        dialog.syncro_subdomain.setText("acme")
        dialog.syncro_api_key.setText("k1")
        dialog.huntress_api_key.setText("k2")
        dialog.huntress_secret.setText("s1")
        accepted = {"value": False}
        dialog.accepted.connect(lambda: accepted.update(value=True))
        dialog._on_save()
        assert accepted["value"] is True
        assert isolated_settings.get("SyncroSubDomain") == "acme"
        assert isolated_settings.validate()[0] is True
