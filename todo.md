# TODO: Fix Codebase Inconsistencies

## Context
This project compares Syncro MSP and Huntress agent data via their APIs. It has both a CLI (`main.py`) and GUI (`gui/`) interface. During a code review, several inconsistencies were identified that make the codebase appear AI-generated or hastily assembled.

## Naming
- [ ] Rename `huntressApiSecretKey` → `HuntressSecretKey` in:
  - `config.py:11`
  - `gui/models/settings_model.py`
  - `gui/widgets/settings_widget.py:143,153`
  - Existing `settings.json` files need manual update

## Type Hints
- [ ] `main.py:6` - add return type to `create_parser()`
- [ ] `main.py:36` - add return type to `main()`
- [ ] `utils/rate_limit.py:15` - change `float | None` to `Optional[float]`

## Code Duplication
- [ ] Extract `build_normalized_maps()` helper in `services/comparison.py`
  - Replace duplicate logic in `gui/workers/comparison_worker.py:73-86`
- [ ] Extract password field helper in `gui/widgets/settings_widget.py`
  - Replace 3 duplicate blocks (lines 41-58, 66-82, 85-103)

## Minor
- [ ] Add trailing newline to `services/comparison.py`
- [ ] Add docstring to `Spinner._spin()` in `utils/output.py`
