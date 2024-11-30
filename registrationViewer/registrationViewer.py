import time
import logging
import functools
import importlib

from typing import Optional, List, Any

import ctk
import slicer.util
import vtk
import slicer
import qt
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
        self._parameterNodeGuiTag = None

        from registrationViewerLib import utils, crosshairs, drop_data_loading, view_logic
        utils = importlib.reload(utils)
        crosshairs = importlib.reload(crosshairs)
        drop_data_loading = importlib.reload(drop_data_loading)
        view_logic = importlib.reload(view_logic)

        self.group_first_row = 1
        self.group_second_row = 2
        self.group_third_row = 3

        self.views_first_row = ["Red1", "Green1", "Yellow1"]
        self.views_second_row = ["Red2", "Green2", "Yellow2"]
        self.views_third_row = ["Red3", "Green3", "Yellow3"]
        # self.views_double_red = ["Red4", "Red5"]
        # self.views_double_green = ["Green4", "Green5"]
        # self.views_double_yellow = ["Yellow4", "Yellow5"]

        self.views_all = self.views_first_row + \
            self.views_second_row + self.views_third_row  # + \
        # self.views_double_red + self.views_double_green + self.views_double_yellow

        utils.create_shortcuts(('s', self.on_synchronise_views_wth_trasform),
                               ('l', self.on_synchronise_views_manually),
                               )

        self.use_transform = True
        self.reverse_transformation_direction = True
        self.current_offset = [0.0, 0.0, 0.0]

        self.crosshair = None

        self.logic = registrationViewerLogic()

        self.synchronise_with_displacement_pressed = False
        self.synchronise_manually_pressed = False

        self.cursor_view: str = ""

        self.node_warped = None
        self.node_diff = None

        self.current_layout: 'view_logic.Layout'

        self.node_roi_fixed = None
        self.node_roi_moving = None

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

        self.node_crosshair.RemoveAllObservers()
        self.synchronise_with_displacement_pressed = False
        self.ui.synchronise_views_with_transform.setText(
            "Synchronise views (s)")

        self._remove_custom_nodes()

        view_logic.register_layout_callback(self.update_current_layout)
        view_logic.set_3x3_layout()

        # set groups
        for i in range(3):
            slicer.app.layoutManager().sliceWidget(
                self.views_first_row[i]).mrmlSliceNode().SetViewGroup(1)
            slicer.app.layoutManager().sliceWidget(
                self.views_second_row[i]).mrmlSliceNode().SetViewGroup(2)
            slicer.app.layoutManager().sliceWidget(
                self.views_third_row[i]).mrmlSliceNode().SetViewGroup(3)

        # Buttons
        self.ui.button_2x3.connect("clicked(bool)", view_logic.set_2x3_layout)
        self.ui.button_3x3.connect("clicked(bool)", view_logic.set_3x3_layout)
        self.ui.synchronise_views_with_transform.connect(
            "clicked(bool)", self.on_synchronise_views_wth_trasform)
        self.ui.synchronise_views_manually.connect(
            "clicked(bool)", self.on_synchronise_views_manually)
        self.ui.addRoiFixed.connect("clicked(bool)", self.on_add_roi_fixed)
        self.ui.addRoiMoving.connect("clicked(bool)", self.on_add_roi_moving)

        # loading code
        drop_data_loading.create_loading_ui(self)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

        # self.dropWidget.load_data_from_dropped_folder("/home/fryderyk/Documents/code/registrationViewer/registrationViewer/Resources/Data/BSplineNiftyReg_6cc04c82-245e-4326-b117-fee51c3b6a50",
        #                                               "/data/LungCT_preprocessed_new",
        #                                               '0')
        utils.collapse_all_segmentations()

        view_logic.link_views(self.views_first_row)
        view_logic.link_views(self.views_second_row)
        view_logic.link_views(self.views_third_row)

        view_logic.set_2x3_layout()

        slicer.util.resetSliceViews()

        # utils.temp_load_data(self)

    def update_current_layout(self, layout: view_logic.Layout) -> None:
        self.current_layout = layout

    def update_views_third_row_with_volume_diff(self) -> None:

        if self.node_fixed is not None and self.node_moving is not None and self.node_transformation is not None:
            if self.node_diff is None:
                self.node_diff = slicer.modules.volumes.logic(
                ).CloneVolume(self.node_fixed, "Difference")
                self.node_diff.SetName("Difference")

            if self.node_warped is not None:
                slicer.mrmlScene.RemoveNode(self.node_warped)

            self.node_warped = slicer.modules.volumes.logic(
            ).CloneVolume(self.node_moving, "Warped")
            self.node_warped.SetName("Warped")
            utils.warp_moving_with_transform(self.node_moving,
                                             self.node_transformation,
                                             self.node_warped)

            array_fixed = slicer.util.arrayFromVolume(self.node_fixed)
            array_warped = slicer.util.arrayFromVolume(self.node_warped)

            array_diff = array_fixed - array_warped

            slicer.util.updateVolumeFromArray(self.node_diff, array_diff)

            self.node_diff.GetDisplayNode().SetAutoWindowLevel(False)
            self.node_diff.GetDisplayNode().SetWindow(2)
            self.node_diff.GetDisplayNode().SetThreshold(-1.0, 1.0)

            view_logic.update_views_with_volume(
                self.views_third_row, self.node_diff)

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

        self.node_crosshair.RemoveAllObservers()
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

        if self.current_layout == view_logic.Layout.L_3X3:
            self.update_views_third_row_with_volume_diff()

        view_logic.update_views_with_volume(
            self.views_first_row, self.node_fixed)
        view_logic.update_views_with_volume(
            self.views_second_row, self.node_moving)
        self._update_crosshair_transformation()

        # set window, level and threshold for fixed and moving
        for node in [self.node_fixed, self.node_moving]:
            if node is None:
                continue

            utils.set_window_level_and_threshold(node,
                                                 window=1036,
                                                 level=329,
                                                 threshold=(-1024, 3071))

    def _synchronisation_checks(self) -> bool:
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

        if self.node_transformation is None:
            slicer.util.errorDisplay("No transformation found")
            return False

        return True

    def on_synchronise_views_wth_trasform(self) -> None:

        if not self._synchronisation_checks():
            return

        self.synchronise_with_displacement_pressed = not self.synchronise_with_displacement_pressed

        self._set_up_crosshair(self.synchronise_with_displacement_pressed)

        if self.synchronise_with_displacement_pressed is True:
            print("pressed to synchronise")
            self.ui.synchronise_views_with_transform.setText(
                "Unsynchronise views (s)")

            self.use_transform = self.crosshair.use_transform = True
            self.crosshair.offset_diffs = self.current_offset = [0, 0, 0]
            self.crosshair.apply_offsets = False
            self.ui.synchronise_views_manually.setText("Link views (l)")
            self.synchronise_manually_pressed = False

        else:
            print("pressed to unsynchronise")
            self.node_crosshair.RemoveAllObservers()
            self.ui.synchronise_views_with_transform.setText(
                "Synchronise views (s)")

    def on_synchronise_views_manually(self, views: List[List[str]] = None) -> None:

        if not self._synchronisation_checks():
            return

        self.synchronise_manually_pressed = not self.synchronise_manually_pressed

        self._set_up_crosshair(self.synchronise_manually_pressed)

        if self.synchronise_manually_pressed is True:
            print("pressed to synchronise manually")
            self.ui.synchronise_views_manually.setText(
                "Unink views (l)")

            self.use_transform = self.crosshair.use_transform = False
            self.ui.synchronise_views_with_transform.setText(
                "Synchronise views (s)")
            self.synchronise_with_displacement_pressed = False

        else:
            print("pressed to unsynchronise manually")
            self.node_crosshair.RemoveAllObservers()
            self.ui.synchronise_views_manually.setText("Link views (l)")

        # get view offset differences between Red1 and Red2, Green1 and Green2, Yellow1 and Yellow2
        offset_diff_red = view_logic.get_view_offset(
            "Red1") - view_logic.get_view_offset("Red2")
        offset_diff_green = view_logic.get_view_offset(
            "Green1") - view_logic.get_view_offset("Green2")
        offset_diff_yellow = view_logic.get_view_offset(
            "Yellow1") - view_logic.get_view_offset("Yellow2")

        self.crosshair.offset_diffs = self.current_offset = [
            offset_diff_red, offset_diff_green, offset_diff_yellow]
        self.crosshair.apply_offsets = self.synchronise_manually_pressed

    def on_add_roi_moving(self) -> None:
        self.node_roi_moving = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLMarkupsROINode")

        self._configure_roi(self.views_second_row, self.node_roi_moving)

    def on_add_roi_fixed(self) -> None:
        self.node_roi_fixed = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLMarkupsROINode")

        self._configure_roi(self.views_first_row, self.node_roi_fixed)

    def _configure_roi(self, views: List[str], node_roi) -> None:

        if not views:
            return
        if not node_roi:
            return

        # geometry
        offsets = [view_logic.get_view_offset(view) for view in views]
        node_roi.SetCenter(-offsets[2],
                           offsets[1],
                           offsets[0])
        node_roi.SetSize(10, 10, 10)

        # display
        node_display = node_roi.GetDisplayNode()
        if not node_display:
            return

        node_display.SetOpacity(0.5)
        node_display.SetFillOpacity(0)

        node_display.SetTextScale(0.0)
        node_display.SetUseGlyphScale(True)
        node_display.SetGlyphScale(1)
        node_display.SetInteractionHandleScale(1.5)

        node_display.RotationHandleVisibilityOn()
        node_display.TranslationHandleVisibilityOn()
        node_display.ScaleHandleVisibilityOn()

        layout_manager = slicer.app.layoutManager()

        if not layout_manager:
            return

        for view in views:
            view_widget = layout_manager.sliceWidget(view)

            if not view_widget:
                continue

            node_display.AddViewNodeID(view_widget.mrmlSliceNode().GetID())

    def update_cursor_view(self) -> None:

        def wrapper(self, callee, event):  # pylint: disable=unused-argument
            position = self.node_crosshair.GetCursorPositionXYZ([0]*3)
            if position is not None:
                self.crosshair.cursor_view = position.GetName()

        self.node_crosshair.AddObserver(slicer.vtkMRMLCrosshairNode.CursorPositionModifiedEvent,
                                        functools.partial(wrapper, self))

    def _remove_custom_nodes(self) -> None:
        if self.node_diff is not None:
            slicer.mrmlScene.RemoveNode(self.node_diff)
            self.node_diff = None
        if self.node_warped is not None:
            slicer.mrmlScene.RemoveNode(self.node_warped)
            self.node_warped = None
        if self.crosshair is not None:
            self.crosshair.delete_crosshairs_and_folder()

    def _are_nodes_selected(self) -> bool:
        return self.ui.inputSelector_fixed.currentNode() is not None and \
            self.ui.inputSelector_moving.currentNode() is not None and \
            self.ui.inputSelector_transformation.currentNode() is not None

    def _set_up_crosshair(self, turn_synchronisation_on: bool) -> None:
        if self.crosshair is None:
            # self.crosshair.delete_crosshairs_and_folder()

            self.crosshair = crosshairs.Crosshairs(node_cursor=self.node_crosshair,
                                                   node_transformation=self.node_transformation,
                                                   use_transform=self.use_transform,
                                                   offset_diffs=self.current_offset,
                                                   apply_offsets=self.synchronise_manually_pressed,)

        if turn_synchronisation_on:
            self.node_crosshair.AddObserver(slicer.vtkMRMLCrosshairNode.CursorPositionModifiedEvent,
                                            self.crosshair.on_mouse_moved_place_crosshair)
            self.update_cursor_view()

    def _update_crosshair_transformation(self) -> None:
        if self.crosshair:
            self.crosshair.node_transformation = self.node_transformation

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
    def node_transformation(self) -> Any:
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
