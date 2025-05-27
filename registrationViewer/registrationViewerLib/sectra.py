from typing import TYPE_CHECKING

import slicer


if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget


def set_sectra_style_sheet() -> None:
    slicer.app.setStyleSheet("""
            QWidget {
                background-color: #060f21;
                color: white;
            }
            QMainWindow {
                background-color: #060f21;
            }
            qSlicerLayoutManager {
                background-color: #060f21;
            }
            """)


def set_normal_style_sheet() -> None:
    slicer.app.setStyleSheet("""
            QWidget {
            color: black;
            }
            """)
