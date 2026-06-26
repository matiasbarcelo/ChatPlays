"""Responsive layout for the setup/test window (kept out of generated UI code)."""

from PyQt5 import QtCore, QtWidgets

MAX_CONTENT_WIDTH = 1000

# Fixed canvas sizes (trimmed below the original Designer heights so there is no
# dead space under the controller art or below the input boxes).
FIXED_PAGE_SIZES = {
    "anarchyPage": (371, 481),
    "democracyPage": (371, 481),
    "page_1": (411, 295),
    "page_2": (411, 295),
    "page_3": (421, 261),
}
CONTROLLER_STACK_SIZE = (421, 295)


def _child_widgets(page):
    return [
        child
        for child in page.children()
        if isinstance(child, QtWidgets.QWidget) and child.parent() is page
    ]


def _is_pixmap_label(widget):
    pixmap = widget.pixmap() if isinstance(widget, QtWidgets.QLabel) else None
    return pixmap is not None and not pixmap.isNull()


def _lock_pixmap_label(label, width, height):
    """Match original Designer behavior: scaled image in a fixed rect."""
    label.setScaledContents(True)
    label.setFixedSize(width, height)
    label.setSizePolicy(
        QtWidgets.QSizePolicy.Fixed,
        QtWidgets.QSizePolicy.Fixed,
    )


def is_on_fixed_canvas(widget):
    parent = widget.parent()
    while parent is not None:
        try:
            if getattr(parent, "_is_fixed_canvas", False):
                return True
            parent = parent.parent()
        except RuntimeError:
            return False
    return False


def attach_fixed_canvas(page, canvas_width, canvas_height):
    """Preserve exact Designer geometry; center the canvas when the page grows."""
    children = _child_widgets(page)
    if not children:
        return None

    design_geometries = {child: child.geometry() for child in children}

    canvas = QtWidgets.QWidget()
    canvas.setObjectName(f"{page.objectName()}_canvas")
    canvas.setFixedSize(canvas_width, canvas_height)
    canvas._is_fixed_canvas = True

    for child, geometry in design_geometries.items():
        child.setParent(canvas)
        child.setGeometry(geometry)
        if _is_pixmap_label(child):
            _lock_pixmap_label(child, geometry.width(), geometry.height())
        elif isinstance(child, QtWidgets.QPushButton):
            # Grow buttons so themed padding/metrics don't clip the label, while
            # keeping them anchored on their original center (over the artwork).
            hint = child.sizeHint()
            new_width = max(geometry.width(), hint.width())
            new_height = max(geometry.height(), hint.height())
            new_geometry = QtCore.QRect(0, 0, new_width, new_height)
            new_geometry.moveCenter(geometry.center())
            child.setGeometry(new_geometry)
            child.setFixedSize(new_width, new_height)
            child.setSizePolicy(
                QtWidgets.QSizePolicy.Fixed,
                QtWidgets.QSizePolicy.Fixed,
            )

    page_layout = QtWidgets.QVBoxLayout(page)
    page_layout.setContentsMargins(0, 0, 0, 0)
    page_layout.setSpacing(0)

    center_row = QtWidgets.QHBoxLayout()
    center_row.addStretch(1)
    center_row.addWidget(canvas, 0, QtCore.Qt.AlignCenter)
    center_row.addStretch(1)

    page_layout.addLayout(center_row)
    page_layout.addStretch(1)

    page._fixed_canvas = canvas  # noqa: SLF001
    return canvas


def _make_gov_header_row(icon, label, point_size=22, icon_size=44):
    """Build a centered 'icon + title' row from an existing page icon and label."""
    icon.setParent(None)
    label.setParent(None)

    icon.setScaledContents(True)
    icon.setFixedSize(icon_size, icon_size)

    font = label.font()
    font.setPointSize(point_size)
    label.setFont(font)
    label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
    label.setSizePolicy(
        QtWidgets.QSizePolicy.Minimum,
        QtWidgets.QSizePolicy.Preferred,
    )

    row = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)
    layout.addStretch(1)
    layout.addWidget(icon, 0, QtCore.Qt.AlignVCenter)
    layout.addWidget(label, 0, QtCore.Qt.AlignVCenter)
    layout.addStretch(1)
    return row


def build_gov_header(ui):
    """Pull each government's icon + title out of the right-column pages into one
    centered header (icon left of a larger title) that follows the active gov."""
    header = QtWidgets.QStackedWidget()
    header.setObjectName("govHeaderStack")
    header.addWidget(_make_gov_header_row(ui.anarchyIcon, ui.anarchyLabel))
    header.addWidget(_make_gov_header_row(ui.democracyIcon, ui.democracyLabel))
    header.setSizePolicy(
        QtWidgets.QSizePolicy.Preferred,
        QtWidgets.QSizePolicy.Fixed,
    )
    header.setCurrentIndex(ui.stackedWidget.currentIndex())
    ui.stackedWidget.currentChanged.connect(header.setCurrentIndex)
    ui._gov_header = header  # noqa: SLF001
    return header


def _center_widget_in_parent(parent, widget, below=None):
    """Center a fixed-size widget inside a growing parent, optionally stacking
    another widget directly beneath it."""
    layout = parent.layout()
    if layout is not None:
        old_parent = QtWidgets.QWidget()
        old_parent.setLayout(layout)

    column = QtWidgets.QVBoxLayout()
    column.setContentsMargins(0, 0, 0, 0)
    column.setSpacing(4)
    column.addWidget(widget, 0, QtCore.Qt.AlignHCenter)
    if below is not None:
        column.addWidget(below)

    row = QtWidgets.QHBoxLayout()
    row.addStretch(1)
    row.addLayout(column)
    row.addStretch(1)

    outer = QtWidgets.QVBoxLayout(parent)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    outer.addLayout(row)
    outer.addStretch(1)


def _fit_window_to_content(window, content):
    """Shrink the window to the laid-out content instead of keeping Designer defaults."""
    content.adjustSize()
    central_layout = window.centralWidget().layout()
    margins = central_layout.contentsMargins()
    frame = window.frameGeometry().size() - window.geometry().size()

    width = content.sizeHint().width() + margins.left() + margins.right() + frame.width()
    height = content.sizeHint().height() + margins.top() + margins.bottom() + frame.height()
    if window.statusBar() is not None:
        height += window.statusBar().sizeHint().height()

    window.setMinimumSize(width, height)
    window.resize(width, height)


def configure_setup_window(ui, main_window=None):
    """Resize panels around fixed-size assets instead of stretching the assets."""
    if getattr(ui, "_responsive_configured", False):
        return

    window = main_window or ui.centralwidget.window()

    expanding = QtWidgets.QSizePolicy(
        QtWidgets.QSizePolicy.Expanding,
        QtWidgets.QSizePolicy.Expanding,
    )
    preferred = QtWidgets.QSizePolicy(
        QtWidgets.QSizePolicy.Preferred,
        QtWidgets.QSizePolicy.Preferred,
    )

    central = ui.centralwidget

    content = QtWidgets.QWidget()
    content.setMaximumWidth(MAX_CONTENT_WIDTH)
    content.setSizePolicy(
        QtWidgets.QSizePolicy.Preferred,
        QtWidgets.QSizePolicy.Maximum,
    )
    content_layout = QtWidgets.QHBoxLayout(content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(16)

    left_panel = QtWidgets.QWidget()
    left_layout = QtWidgets.QVBoxLayout(left_panel)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(8)

    settings_row = QtWidgets.QWidget()
    settings_row.setMaximumWidth(460)
    settings_layout = QtWidgets.QHBoxLayout(settings_row)
    settings_layout.setContentsMargins(0, 0, 0, 0)
    settings_layout.setSpacing(12)
    settings_layout.addWidget(ui.verticalLayoutWidget_2)
    settings_layout.addWidget(ui.verticalLayoutWidget_3, 1)

    settings_container = QtWidgets.QWidget()
    settings_container_layout = QtWidgets.QHBoxLayout(settings_container)
    settings_container_layout.setContentsMargins(0, 0, 0, 0)
    settings_container_layout.addStretch(1)
    settings_container_layout.addWidget(settings_row)
    settings_container_layout.addStretch(1)

    timing_container = QtWidgets.QWidget()
    timing_container_layout = QtWidgets.QHBoxLayout(timing_container)
    timing_container_layout.setContentsMargins(0, 0, 0, 0)
    timing_container_layout.addStretch(1)
    timing_container_layout.addWidget(ui.horizontalLayoutWidget)
    timing_container_layout.addStretch(1)

    left_layout.addWidget(settings_container)
    left_layout.addWidget(timing_container)
    left_layout.addWidget(ui.gridLayoutWidget, 0)

    content_layout.addWidget(left_panel, 3)
    content_layout.addWidget(ui.verticalLayoutWidget, 2)

    outer_layout = QtWidgets.QHBoxLayout(central)
    outer_layout.setContentsMargins(12, 12, 12, 12)
    outer_layout.setSpacing(0)
    outer_layout.addStretch(1)
    outer_layout.addWidget(content, 0, QtCore.Qt.AlignCenter)
    outer_layout.addStretch(1)

    ui.verticalLayoutWidget_2.setSizePolicy(preferred)
    ui.verticalLayoutWidget_3.setSizePolicy(expanding)
    ui.horizontalLayoutWidget.setSizePolicy(
        QtWidgets.QSizePolicy.Preferred,
        QtWidgets.QSizePolicy.Preferred,
    )
    ui.gridLayoutWidget.setSizePolicy(expanding)
    ui.verticalLayoutWidget.setSizePolicy(expanding)
    ui.stackedWidget.setSizePolicy(
        QtWidgets.QSizePolicy.Preferred,
        QtWidgets.QSizePolicy.Fixed,
    )
    ui.stackedWidget.setFixedHeight(FIXED_PAGE_SIZES["anarchyPage"][1])
    ui.stackedWidget_2.setFixedSize(*CONTROLLER_STACK_SIZE)
    ui.stackedWidget_2.setSizePolicy(
        QtWidgets.QSizePolicy.Fixed,
        QtWidgets.QSizePolicy.Fixed,
    )

    # Move the government title/icon out of the pages before the canvases capture
    # their children, so they can live under the controller in the left panel.
    gov_header = build_gov_header(ui)

    attach_fixed_canvas(ui.anarchyPage, *FIXED_PAGE_SIZES["anarchyPage"])
    attach_fixed_canvas(ui.democracyPage, *FIXED_PAGE_SIZES["democracyPage"])
    attach_fixed_canvas(ui.page_1, *FIXED_PAGE_SIZES["page_1"])
    attach_fixed_canvas(ui.page_2, *FIXED_PAGE_SIZES["page_2"])
    attach_fixed_canvas(ui.page_3, *FIXED_PAGE_SIZES["page_3"])
    _center_widget_in_parent(ui.gridLayoutWidget, ui.stackedWidget_2, below=gov_header)

    ui._responsive_configured = True
    _fit_window_to_content(window, content)
