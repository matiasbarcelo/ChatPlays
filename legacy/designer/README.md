# Qt Designer sources

Qt Designer source files for the old PyQt UI live here.

## Open in Designer

```bash
designer legacy/designer/setup_test_ui.ui
designer legacy/designer/chatplays_ui.ui
```

## Regenerate Python (optional, archived PyQt app)

```bash
pyuic5 -x legacy/designer/setup_test_ui.ui -o legacy/pyqt/setupTestUi.py
pyuic5 -x legacy/designer/chatplays_ui.ui -o legacy/pyqt/chatplaysUi.py
```

## Related paths

- Also copied at: `legacy/pyqt/UI/`
- Mockup PNGs: `legacy/design/`
- Generated PyQt code + driver: `legacy/pyqt/`
