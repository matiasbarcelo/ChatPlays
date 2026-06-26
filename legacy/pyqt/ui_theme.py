"""Shared PyQt5 styling for consistent appearance across macOS/Windows/Linux."""

from PyQt5 import QtGui, QtWidgets

from repo_paths import FONTS_DIR

# Spin boxes (QSpinBox / QDoubleSpinBox) are intentionally excluded so Qt draws
# the default Fusion step buttons and arrows.
APP_STYLESHEET = """
    QMainWindow {
        background-color: #f0f0f0;
        color: #1a1a1a;
    }
    QLineEdit, QListWidget, QComboBox {
        background-color: #ffffff;
        color: #1a1a1a;
        border: 1px solid #c0c0c0;
        border-radius: 4px;
        padding: 2px 6px;
        min-height: 22px;
    }
    QPushButton {
        background-color: #e8e8e8;
        color: #1a1a1a;
        border: 1px solid #b0b0b0;
        border-radius: 4px;
        padding: 4px 12px;
        min-height: 28px;
    }
    QPushButton:hover {
        background-color: #dcdcdc;
    }
    QPushButton:pressed {
        background-color: #c8c8c8;
    }
    QCheckBox, QLabel {
        background-color: transparent;
        color: #1a1a1a;
    }
    QStatusBar {
        background-color: #f0f0f0;
    }
"""


def load_bundled_fonts():
    """Register project fonts so Qt can resolve families like 'Alte Haas Grotesk'."""
    if not FONTS_DIR.is_dir():
        return
    for font_path in sorted(FONTS_DIR.glob("*.ttf")):
        QtGui.QFontDatabase.addApplicationFont(str(font_path))


def apply_app_theme(app):
    """Use Fusion style so macOS dark mode does not clip native-styled widgets."""
    load_bundled_fonts()
    app.setStyle("Fusion")

    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor("#f0f0f0"))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor("#1a1a1a"))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor("#ffffff"))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor("#1a1a1a"))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor("#e0e0e0"))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor("#333333"))
    app.setPalette(palette)

    app.setStyleSheet(APP_STYLESHEET)


def fit_push_button(button):
    """Resize a button to fit its label; macOS metrics are wider than Designer defaults."""
    button.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
    hint = button.sizeHint()
    button.setMinimumSize(hint)
    button.resize(
        max(button.width(), hint.width()),
        max(button.height(), hint.height()),
    )


def fit_layout_container(container):
    """Grow a fixed-size layout host so themed widgets are not clipped."""
    layout = container.layout()
    if layout is None:
        return
    hint = layout.sizeHint()
    margins = layout.contentsMargins()
    needed_height = hint.height() + margins.top() + margins.bottom()
    needed_width = hint.width() + margins.left() + margins.right()
    container.setMinimumHeight(needed_height)
    container.resize(
        max(container.width(), needed_width),
        max(container.height(), needed_height),
    )


def fit_spin_box(spin_box):
    """Ensure spin boxes keep room for value text and step buttons."""
    hint = spin_box.sizeHint()
    spin_box.setMinimumSize(hint)
    spin_box.resize(
        max(spin_box.width(), hint.width()),
        max(spin_box.height(), hint.height()),
    )
