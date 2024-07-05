import logging
import os
from typing import Annotated, Optional
import functools

import vtk
import vtk
import qt
import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)

from slicer import vtkMRMLScalarVolumeNode, vtkMRMLTransformNode

from registrationViewerLib import utils

#
# registrationViewer
#


class registrationViewer(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("registrationViewer")
        # folders where the module shows up in the module selector
        self.parent.categories = [
            translate("qSlicerAbstractCoreModule", "Examples")]
        self.parent.dependencies = []  # list of module names that this module requires
        self.parent.contributors = ["Fryderyk Kögl (TUM)"]
        # TODO: update with short description of the module and a link to online module documentation
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
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None

        # set the view to 3 over 3
        slicer.app.layoutManager().setLayout(
            slicer.vtkMRMLLayoutNode.SlicerLayoutThreeOverThreeView)

        self.group_normal = 1
        self.group_plus = 2
        self.views_normal = ["Red", "Green", "Yellow"]
        self.views_plus = ["Red+", "Green+", "Yellow+"]
        # set groups
        for i in range(3):
            slicer.app.layoutManager().sliceWidget(
                self.views_normal[i]).mrmlSliceNode().SetViewGroup(self.group_normal)
            slicer.app.layoutManager().sliceWidget(
                self.views_plus[i]).mrmlSliceNode().SetViewGroup(self.group_plus)

        utils.create_shortcuts(('t', self.on_toggle_transform),
                               ('s', self.on_synchronise_views),
                               ('r', self.on_toggle_transform_reversal))

        self.use_transform = True
        self.reverse_transformation_direction = True

        self.my_crosshair_node_normal = None
        self.my_crosshair_node_plus = None
        self.cursor_node = None

        self.logic = registrationViewerLogic()

        self.pressed = False

        # self.transformation_matrix = vtk.vtkMatrix4x4()
        self.node_transformation = None

        self.cursor_view: str = ""

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(
            self.resourcePath("UI/registrationViewer.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(
            slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene,
                         slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Buttons
        self.ui.synchronise_views.connect(
            "clicked(bool)", self.on_synchronise_views)
        self.ui.toggle_transform.connect(
            "clicked(bool)", self.on_toggle_transform)
        self.ui.toggle_transform_reversal.connect(
            "clicked(bool)", self.on_toggle_transform_reversal)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

        utils.temp_load_data(self)

        self.my_crosshair_node_red = utils.create_crosshair(views=["Red"])
        self.my_crosshair_node_green = utils.create_crosshair(views=["Green"])
        self.my_crosshair_node_yellow = utils.create_crosshair(views=[
                                                               "Yellow"])

        self.my_crosshair_node_plus = utils.create_crosshair(
            views=["Red+", "Green+", "Yellow+"])

    # TODO remove all my observers

    def update_views_normal_with_volume_fixed(self):
        # show fixed volume in top row
        for view in self.views_normal:
            slice_logic = slicer.app.layoutManager().sliceWidget(view).sliceLogic()
            composite_node = slice_logic.GetSliceCompositeNode()

            node_fixed = self.ui.inputSelector_fixed.currentNode()

            if node_fixed:
                composite_node.SetBackgroundVolumeID(node_fixed.GetID())
            else:
                composite_node.SetBackgroundVolumeID(None)

            composite_node.SetForegroundVolumeID(None)

    def update_views_plus_with_volume_moving(self):
        # show fixed volume in top row
        for view in self.views_plus:
            slice_logic = slicer.app.layoutManager().sliceWidget(view).sliceLogic()
            composite_node = slice_logic.GetSliceCompositeNode()

            node_moving = self.ui.inputSelector_moving.currentNode()

            if node_moving:
                composite_node.SetBackgroundVolumeID(node_moving.GetID())
            else:
                composite_node.SetBackgroundVolumeID(None)

            composite_node.SetForegroundVolumeID(None)

    def update_transformation_from_selector(self):
        self.node_transformation = self.ui.inputSelector_transformation.currentNode()

        # invert transformation

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
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(
                self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)

    def onSceneStartClose(self, caller, event) -> None:
        """Called just before the scene is closed."""
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """Called just after the scene is closed."""
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists and observed."""
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

        # to do make smart selection
        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        # if not self._parameterNode.inputVolume:
        #     firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass(
        #         "vtkMRMLScalarVolumeNode")
        #     if firstVolumeNode:
        #         self._parameterNode.inputVolume = firstVolumeNode

    def setParameterNode(self, inputParameterNode: Optional[registrationViewerParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(
                self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode,
                             vtk.vtkCommand.ModifiedEvent, self._checkCanApply)

            self._checkCanApply()

    # todo why is this needed
    def _checkCanApply(self, caller=None, event=None) -> None:
        self.update_views_normal_with_volume_fixed()
        self.update_views_plus_with_volume_moving()
        self.update_transformation_from_selector()

    def on_toggle_transform(self) -> None:
        if self.node_transformation is None:
            self.update_transformation_from_selector()
        if self.node_transformation is None:
            slicer.util.errorDisplay("No transformation found")
            return

        self.use_transform = not self.use_transform

        if self.use_transform:
            self.ui.toggle_transform.setText("Turn off transform (t)")
        else:
            self.ui.toggle_transform.setText("Turn on transform (t)")

        # disable this transform reversal button if use_transform is False
        self.ui.toggle_transform_reversal.setEnabled(self.use_transform)

    def on_synchronise_views(self) -> None:
        """Run processing when user clicks "Apply" button."""

        if self.node_transformation is None:
            self.update_transformation_from_selector()
        if self.node_transformation is None:
            slicer.util.errorDisplay("No transformation found")
            return

        if self.pressed is False:
            self.cursor_node = slicer.util.getNode("Crosshair")
            self.cursor_node.AddObserver(slicer.vtkMRMLCrosshairNode.CursorPositionModifiedEvent,
                                         functools.partial(utils.on_mouse_moved_place_corsshair, self))
            self.pressed = True
            self.ui.synchronise_views.setText("Unsynchronise views (s)")

            # has to be done here because here we know that the cursor_node is not None
            self.update_cursor_view()

        else:
            self.cursor_node.RemoveAllObservers()
            self.pressed = False
            self.ui.synchronise_views.setText("Synchronise views (s)")

    def on_toggle_transform_reversal(self) -> None:
        if self.use_transform:
            self.reverse_transformation_direction = not self.reverse_transformation_direction

            if self.reverse_transformation_direction:
                self.ui.toggle_transform_reversal.setText(
                    "Turn off transform reversal (r)")
            else:
                self.ui.toggle_transform_reversal.setText(
                    "Turn on transform reversal (r)")
        else:
            slicer.util.errorDisplay(
                "Cannot reverse transformation direction without using transformation.\n \
                Please turn on transformation first.")

    def update_cursor_view(self):

        c = slicer.util.getNode("*Crosshair*")

        def wrapper(self, callee, event):
            position = c.GetCursorPositionXYZ([0]*3)
            if position is not None:
                self.cursor_view = position.GetName()

                print(self.cursor_view)

        c.AddObserver(slicer.vtkMRMLCrosshairNode.CursorPositionModifiedEvent,
                      functools.partial(wrapper, self))


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

        import time

        startTime = time.time()
        logging.info("Processing started")

        utils.printVolumeName(inputVolume)

        # print(f"Volume name: {inputVolume.GetName()}")

        stopTime = time.time()
        logging.info(
            f"Processing completed in {stopTime-startTime:.2f} seconds")
