import time
import logging
import functools
import importlib

from enum import Enum
from typing import Optional, List

import slicer.util
import vtk
import slicer
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

from registrationViewerLib import utils, crosshairs

#
# registrationViewer
#


class Layout(Enum):
    L_2X3 = 701
    L_3X3 = 601


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
        self._parameterNodeGuiTag = None

        from registrationViewerLib import utils, crosshairs
        utils = importlib.reload(utils)
        crosshairs = importlib.reload(crosshairs)

        self.group_first_row = 1
        self.group_second_row = 2
        self.group_third_row = 3

        self.views_first_row = ["Red1", "Green1", "Yellow1"]
        self.views_second_row = ["Red2", "Green2", "Yellow2"]
        self.views_third_row = ["Red3", "Green3", "Yellow3"]

        utils.create_shortcuts(('t', self.on_toggle_transform),
                               ('s', self.on_synchronise_views),
                               ('r', self.on_toggle_transform_reversal))

        self.use_transform = True
        self.reverse_transformation_direction = True

        self.crosshair = None

        self.logic = registrationViewerLogic()

        self.synchronize_pressed = False

        self.node_transformation = None

        self.cursor_view: str = ""

        self.node_warped = None
        self.node_diff = None

        self.current_layout: Layout

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

        utils.set_3x3_layout()
        self.current_layout = Layout.L_3X3

        # set groups
        for i in range(3):
            slicer.app.layoutManager().sliceWidget(
                self.views_first_row[i]).mrmlSliceNode().SetViewGroup(1)
            slicer.app.layoutManager().sliceWidget(
                self.views_second_row[i]).mrmlSliceNode().SetViewGroup(2)
            slicer.app.layoutManager().sliceWidget(
                self.views_third_row[i]).mrmlSliceNode().SetViewGroup(3)

        # Buttons
        self.ui.button_2x3.connect("clicked(bool)", self.on_button_2x3_clicked)
        self.ui.button_3x3.connect("clicked(bool)", self.on_button_3x3_clicked)
        self.ui.synchronise_views.connect(
            "clicked(bool)", self.on_synchronise_views)
        self.ui.toggle_transform.connect(
            "clicked(bool)", self.on_toggle_transform)
        self.ui.toggle_transform_reversal.connect(
            "clicked(bool)", self.on_toggle_transform_reversal)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

        utils.link_views(self.views_first_row)
        utils.link_views(self.views_second_row)
        utils.link_views(self.views_third_row)

        slicer.util.resetSliceViews()

        # utils.temp_load_data(self)

    # TODO remove all my observers

    def update_views_with_volume(self, views: List[str], volume: vtkMRMLScalarVolumeNode):
        for view in views:
            slice_logic = slicer.app.layoutManager().sliceWidget(view).sliceLogic()
            composite_node = slice_logic.GetSliceCompositeNode()

            if volume:
                composite_node.SetBackgroundVolumeID(volume.GetID())
            else:
                composite_node.SetBackgroundVolumeID(None)

            composite_node.SetForegroundVolumeID(None)

    def update_views_first_row_with_volume_fixed(self):

        node_fixed = self.ui.inputSelector_fixed.currentNode()

        self.update_views_with_volume(self.views_first_row, node_fixed)

    def update_views_second_row_with_volume_moving(self):

        node_moving = self.ui.inputSelector_moving.currentNode()

        self.update_views_with_volume(self.views_second_row, node_moving)

    def update_views_third_row_with_volume_diff(self):

        node_fixed = self.ui.inputSelector_fixed.currentNode()
        node_transformation = self.ui.inputSelector_transformation.currentNode()
        node_moving = self.ui.inputSelector_moving.currentNode()

        if node_fixed is not None and node_moving is not None and node_transformation is not None:
            if self.node_diff is None:
                self.node_diff = slicer.modules.volumes.logic().CloneVolume(node_fixed, "Difference")
                self.node_diff.SetName("Difference")

            if self.node_warped is not None:
                slicer.mrmlScene.RemoveNode(self.node_warped)

            self.node_warped = slicer.modules.volumes.logic().CloneVolume(node_moving, "Warped")
            self.node_warped.SetName("Warped")
            utils.warp_moving_with_transform(node_moving,
                                             node_transformation,
                                             self.node_warped)

            array_fixed = slicer.util.arrayFromVolume(node_fixed)
            array_warped = slicer.util.arrayFromVolume(self.node_warped)

            array_diff = array_fixed - array_warped

            slicer.util.updateVolumeFromArray(self.node_diff, array_diff)

            self.node_diff.GetDisplayNode().SetAutoWindowLevel(False)
            self.node_diff.GetDisplayNode().SetWindow(2)
            self.node_diff.GetDisplayNode().SetThreshold(-1.0, 1.0)

            self.update_views_with_volume(self.views_third_row, self.node_diff)

    def update_transformation_from_selector(self):
        self.node_transformation = self.ui.inputSelector_transformation.currentNode()

        if self.crosshair is None:
            return
        self.crosshair.node_transformation = self.ui.inputSelector_transformation.currentNode()

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
            self._parameterNode.disconnectGui(  # type: ignore
                self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(
                self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._update_from_gui)

    def onSceneStartClose(self, caller, event) -> None:  # pylint: disable=unused-argument
        """Called just before the scene is closed."""
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

        if self.node_diff is not None:
            slicer.mrmlScene.RemoveNode(self.node_diff)
            self.node_diff = None
        if self.node_warped is not None:
            slicer.mrmlScene.RemoveNode(self.node_warped)
            self.node_warped = None

        self._checkCanApply()

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
            self._parameterNode.disconnectGui(  # type: ignore
                self._parameterNodeGuiTag)
            self.removeObserver(
                self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._update_from_gui)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(  # type: ignore
                self.ui)
            self.addObserver(self._parameterNode,
                             vtk.vtkCommand.ModifiedEvent, self._update_from_gui)

    def _update_from_gui(self, caller=None, event=None) -> None:  # pylint: disable=unused-argument

        if self.current_layout == Layout.L_3X3:
            self.update_views_third_row_with_volume_diff()

        self.update_views_first_row_with_volume_fixed()
        self.update_views_second_row_with_volume_moving()
        self.update_transformation_from_selector()

    def on_button_2x3_clicked(self) -> None:
        utils.set_2x3_layout()
        self.current_layout = Layout.L_2X3

    def on_button_3x3_clicked(self) -> None:
        utils.set_3x3_layout()
        self.current_layout = Layout.L_3X3

    def on_toggle_transform(self) -> None:
        if self.node_transformation is None:
            self.update_transformation_from_selector()
        if self.node_transformation is None:
            slicer.util.errorDisplay("No transformation found")
            return

        self.use_transform = not self.use_transform
        self.crosshair.use_transform = self.use_transform

        if self.use_transform:
            self.ui.toggle_transform.setText("Turn off transform (t)")
        else:
            self.ui.toggle_transform.setText("Turn on transform (t)")

        # disable this transform reversal button if use_transform is False
        self.ui.toggle_transform_reversal.setEnabled(self.use_transform)

    def on_synchronise_views(self) -> None:
        self.cursor_node = slicer.util.getNode("Crosshair")
        if self.cursor_node is None:
            slicer.util.errorDisplay("No crosshair found")
            return

        if self.crosshair is not None:
            self.crosshair.delete_crosshairs_and_folder()

        self.crosshair = crosshairs.Crosshairs(cursor_node=self.cursor_node,
                                               use_transform=self.use_transform)
        self.cursor_node.AddObserver(slicer.vtkMRMLCrosshairNode.CursorPositionModifiedEvent,
                                     self.crosshair.on_mouse_moved_place_crosshair)
        self.update_cursor_view()

        if self.node_transformation is None:
            self.update_transformation_from_selector()
        if self.node_transformation is None:
            slicer.util.errorDisplay("No transformation found")
            return

        self.synchronize_pressed = not self.synchronize_pressed

        if self.synchronize_pressed is False:
            self.ui.synchronise_views.setText("Unsynchronise views (s)")
        else:
            self.cursor_node.RemoveAllObservers()
            self.ui.synchronise_views.setText("Synchronise views (s)")

    def on_toggle_transform_reversal(self) -> None:  # pylint: disable=unused-argument
        if self.use_transform:
            self.reverse_transformation_direction = not self.reverse_transformation_direction
            self.crosshair.reverse_transf_direction = self.reverse_transformation_direction

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

        def wrapper(self, callee, event):  # pylint: disable=unused-argument
            position = c.GetCursorPositionXYZ([0]*3)
            if position is not None:
                self.crosshair.cursor_view = position.GetName()

        c.AddObserver(slicer.vtkMRMLCrosshairNode.CursorPositionModifiedEvent,
                      functools.partial(wrapper, self))

    @property
    def cursor_node(self) -> vtk.vtkMRMLCrosshairNode:
        return slicer.util.getNode("Crosshair")


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
