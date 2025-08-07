from __future__ import annotations
import functools
import importlib
import logging
import os
import time

from typing import Optional, Any, Literal, Tuple, Dict, Callable

import numpy as np
import glob

import ctk
import vtk
import qt
import slicer
import slicer.util
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import (
    ScriptedLoadableModule,
    ScriptedLoadableModuleWidget,
    ScriptedLoadableModuleLogic)
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
)
from slicer import vtkMRMLScalarVolumeNode, vtkMRMLTransformNode  # pylint: disable=no-name-in-module

import registrationViewerLib
from registrationViewerLib import utils, crosshairs, view_logic, drop_data_loading


class registrationViewer(ScriptedLoadableModule):
    """_summary_

    Args:
        ScriptedLoadableModule (_type_): _description_
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("registrationViewer")
        # folders where the module shows up in the module selector
        self.parent.categories = [
            translate("qSlicerAbstractCoreModule", "Examples")]
        self.parent.dependencies = []  # list of module names that this module requires
        self.parent.contributors = ["Fryderyk Kögl (TUM)"]
        # _() function marks text as translatable to other languages
        self.parent.helpText = _("""Basic module. See more information in <a href="https://github.com/koegl-PhD/registrationViewer">module documentation</a>.
""")
        self.parent.acknowledgementText = _("""
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""")

#
# registrationViewerParameterNode
#


@parameterNodeWrapper
class registrationViewerParameterNode:
    """
    The parameters needed by module.

    inputVolume - Input volume to print the name
    """

    volume_fixed: vtkMRMLScalarVolumeNode
    volume_moving: vtkMRMLScalarVolumeNode
    transformation: vtkMRMLTransformNode


#
# registrationViewerWidget
#


class registrationViewerWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        # needed for parameter node observation
        VTKObservationMixin.__init__(self)
        self._parameterNode: Optional[registrationViewerParameterNode] = None
        self._parameterNodeGuiTags = []

        modules = [
            "utils", "crosshairs",
            "view_logic", "drop_data_loading"
        ]

        for name in modules:
            m = importlib.reload(getattr(registrationViewerLib, name))
            setattr(registrationViewerLib, name, m)  # type: ignore
            globals()[name] = m  # type: ignore

        self.logger = None

        self.group_first_row = 1
        self.group_second_row = 2

        self.views_first_row = ["Red", "Green", "Yellow"]
        self.views_second_row = ["Red+", "Green+", "Yellow+"]

        self.views_all = self.views_first_row + self.views_second_row

        utils.create_shortcuts(
            ('s', self.on_synchronise_views),
        )

        self.use_transform = True
        self.reverse_transformation_direction = True
        self.current_offset = [0.0, 0.0, 0.0]
        self.offset_set = False

        self.crosshair = None

        self.logic = registrationViewerLogic()

        self.synchronise_with_displacement_pressed = False

        self.crosshair_custom_observer_tags = []

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        mainWidget = slicer.util.loadUI(
            self.resourcePath("UI/registrationViewer.ui"))
        self.layout.addWidget(mainWidget)
        self.ui = slicer.util.childWidgetVariables(mainWidget)

        self.all_uis = [self.ui]

        slicer.app.processEvents()  # Ensures all widgets are fully rendered

        # Set MRML scene for main UI (but not generic QWidgets)
        mainWidget.setMRMLScene(slicer.mrmlScene)

        for selector in [self.ui.inputSelector_fixed,
                         self.ui.inputSelector_moving,
                         self.ui.inputSelector_transformation]:
            selector.setMRMLScene(slicer.mrmlScene)

        mainWidget.connect("mrmlSceneChanged(vtkMRMLScene*)",
                           self.ui.inputSelector_fixed.setMRMLScene)
        mainWidget.connect("mrmlSceneChanged(vtkMRMLScene*)",
                           self.ui.inputSelector_moving.setMRMLScene)
        mainWidget.connect("mrmlSceneChanged(vtkMRMLScene*)",
                           self.ui.inputSelector_transformation.setMRMLScene)

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(
            slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene,
                         slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        self.remove_custom_observers_from_crosshair()
        self.synchronise_with_displacement_pressed = False
        self.ui.synchronise_views_with_transform.setText(
            "Synchronise views (s)")

        self._remove_custom_nodes()

        view_logic.set_three_over_three_layout()

        # set groups
        for i in range(3):
            slicer.app.layoutManager().sliceWidget(
                self.views_first_row[i]).mrmlSliceNode().SetViewGroup(1)
            slicer.app.layoutManager().sliceWidget(
                self.views_second_row[i]).mrmlSliceNode().SetViewGroup(2)

        # Buttons
        self.ui.synchronise_views_with_transform.connect(
            "clicked(bool)", self.on_synchronise_views)

        # loading code
        # drop_data_loading.create_loading_ui(self)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

        view_logic.link_views(self.views_first_row)
        view_logic.link_views(self.views_second_row)

        # view_logic.set_three_over_three_layout()

        slicer.util.resetSliceViews()

        # self.dropWidget.load_data_from_dropped_folder(
        #     "/home/fryderyk/Documents/code/data/example_ct")

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        self.removeObservers()

    def enter(self) -> None:
        """Called each time the user opens this module."""
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self) -> None:
        """Called each time the user opens a different module."""
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self._disconnect_gui()
            self._clear_parameter_node_gui_tags()

            self.removeObserver(
                self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._update_from_gui)

    def onSceneStartClose(self, caller, event) -> None:  # pylint: disable=unused-argument
        """Called just before the scene is closed."""

        self.remove_custom_observers_from_crosshair()
        self.synchronise_with_displacement_pressed = False
        self.ui.synchronise_views_with_transform.setText(
            "Synchronise views (s)")

        self._remove_custom_nodes()

        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:  # pylint: disable=unused-argument
        """Called just after the scene is closed."""
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists and observed."""
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

    def setParameterNode(self, inputParameterNode: Optional[registrationViewerParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._disconnect_gui()
            self.removeObserver(
                self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._update_from_gui)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._connect_gui()
            self.addObserver(self._parameterNode,
                             vtk.vtkCommand.ModifiedEvent, self._update_from_gui)

    def _connect_gui(self) -> None:
        for ui in self.all_uis:
            self._parameterNodeGuiTags.append(
                self._parameterNode.connectGui(ui))

    def _disconnect_gui(self) -> None:
        for tag in self._parameterNodeGuiTags:
            self._parameterNode.disconnectGui(tag)

    def _clear_parameter_node_gui_tags(self) -> None:
        self._parameterNodeGuiTags = []

    def _update_from_gui(self, caller=None, event=None) -> None:  # pylint: disable=unused-argument

        view_logic.update_views_with_volume(
            self.views_first_row, self.node_fixed)
        view_logic.update_views_with_volume(
            self.views_second_row, self.node_moving)
        self._update_crosshair_transformation()

        # reset field of view for view 0, 3 and 6
        for view in [self.views_first_row[0], self.views_second_row[0]]:
            slicer.app.layoutManager().sliceWidget(
                view).sliceController().fitSliceToBackground()

        view_logic.link_views(self.views_first_row)
        view_logic.link_views(self.views_second_row)

    def synchronisation_checks(self) -> bool:
        """
        Internal helper method to validate synchronization prerequisites.
        Returns True if synchronization can proceed, False otherwise.
        """
        if not self._are_nodes_selected():
            slicer.util.errorDisplay(
                "Please select fixed, moving and transformation nodes")
            return False

        if self.node_crosshair is None:
            slicer.util.errorDisplay("No crosshair found")
            return False

        if self.node_transform_nonlinear is None:
            slicer.util.errorDisplay("No nonlinear transform found")
            return False

        return True

    def on_synchronise_views(self) -> None:

        if not self.synchronisation_checks():
            return

        self.synchronise_with_displacement_pressed = not self.synchronise_with_displacement_pressed

        if self.synchronise_with_displacement_pressed is True:
            self._set_up_crosshair(self.synchronise_with_displacement_pressed)
            print("pressed to synchronise")
            self.ui.synchronise_views_with_transform.setText(
                "Unsynchronise views (s)")

            self.use_transform = self.crosshair.use_transform = True

            self.crosshair.offset_diffs = self.current_offset = [0, 0, 0]
            self.crosshair.apply_offsets = False
            self.synchronise_manually_pressed = False
        else:
            print("pressed to unsynchronise")
            self.remove_custom_observers_from_crosshair()
            self.ui.synchronise_views_with_transform.setText(
                "Synchronise views (s)")

    def _remove_custom_nodes(self) -> None:
        if self.crosshair is not None:
            self.crosshair.delete_crosshairs_and_folder()
            self.crosshair = None

    def _are_nodes_selected(self) -> bool:
        return self.ui.inputSelector_fixed.currentNode() is not None and \
            self.ui.inputSelector_moving.currentNode() is not None and \
            self.ui.inputSelector_transformation.currentNode() is not None

    def _set_up_crosshair(self, turn_synchronisation_on: bool) -> None:
        if self.crosshair:
            self.crosshair.delete_crosshairs_and_folder()

        self.crosshair = crosshairs.Crosshairs(node_cursor=self.node_crosshair,
                                               node_transform_nonlinear=self.node_transform_nonlinear,
                                               use_transform=self.use_transform)

        if turn_synchronisation_on:
            observer_tag = self.node_crosshair.AddObserver(slicer.vtkMRMLCrosshairNode.CursorPositionModifiedEvent,
                                                           self.crosshair.on_mouse_moved_place_crosshair)
            self.crosshair_custom_observer_tags.append(observer_tag)

    def _update_crosshair_transformation(self) -> None:
        if self.crosshair:
            self.crosshair.node_transform_nonlinear = self.node_transform_nonlinear

    def remove_custom_observers_from_crosshair(self) -> None:
        for observer_tag in self.crosshair_custom_observer_tags:
            if self.node_crosshair:
                self.node_crosshair.RemoveObserver(observer_tag)

        self.crosshair_custom_observer_tags.clear()

    @property
    def node_fixed(self) -> Any:
        return self.ui.inputSelector_fixed.currentNode()

    @property
    def node_moving(self) -> Any:
        return self.ui.inputSelector_moving.currentNode()

    @property
    def node_crosshair(self) -> Any:
        return slicer.util.getNode("Crosshair")

    @property
    def node_transform_nonlinear(self) -> Any:
        return self.ui.inputSelector_transformation.currentNode()


class registrationViewerLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)

    def getParameterNode(self):
        return registrationViewerParameterNode(super().getParameterNode())

    def process(self, inputVolume: vtkMRMLScalarVolumeNode) -> None:
        """
        Run the processing algorithm.
        Can be used without GUI widget.
        :param inputVolume: volume to be thresholded
        """

        if not inputVolume:
            raise ValueError("Input volume is invalid")

        start_time = time.time()
        logging.info("Processing started")

        # print(f"Volume name: {inputVolume.GetName()}")

        stop_time = time.time()
        logging.info(
            "Processing completed in %.2f seconds", stop_time-start_time)
