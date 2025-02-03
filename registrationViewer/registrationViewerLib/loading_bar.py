import os
import glob
import logging
from typing import List
import ctk
import qt
import slicer
from slicer.ScriptedLoadableModule import *
import registrationViewerLib.utils as utils


def create_loading_bar(
        self,
        max_size: int,
        bar_idx: int,
        text: str = None,
        text_position: str = 'above'):
    # Create a widget for the loading bar
    loadingWidget = qt.QWidget()
    loadingLayout = qt.QVBoxLayout(loadingWidget)

    # Create progress bar and EXPLICITLY set it as an attribute
    progress_bar = qt.QProgressBar()
    setattr(self, f"progress_bar_{bar_idx}", progress_bar)

    progress_bar.setMaximum(max_size)
    progress_bar.setTextVisible(True)
    # This sets the format to show current/maximum
    progress_bar.setFormat("%v/%m")
    progress_bar.setStyleSheet("""
     QProgressBar {
     border: 2px solid #999;
     border-radius: 5px;
     text-align: center;
     }
     QProgressBar::chunk {
     background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
     stop:0 #888,
     stop:1 #0F0);
     }
     """)

    # Add text if provided
    if text:
        text_label = qt.QLabel(text)
        text_label.setAlignment(qt.Qt.AlignCenter)
        # Add text based on specified position
        if text_position == 'above':
            loadingLayout.addWidget(text_label)

    # Add progress bar to layout
    loadingLayout.addWidget(progress_bar)

    # Add the loading widget to the main layout
    self.layout.addWidget(loadingWidget)

    return loadingWidget
