import functools
import importlib
import logging
import os
import time

from typing import Optional, Any, Literal, Tuple, Dict, Callable

import numpy as np

import ctk
import vtk
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
from registrationViewerLib import annotations_connections, custom_logging, utils, sectra, crosshairs, view_logic, drop_data_loading, study_connections, study, tasks, texts


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
            "annotations_connections", "utils", "sectra", "crosshairs",
            "view_logic", "drop_data_loading", "study_connections",
            "study", "tasks", "texts", "custom_logging"
        ]

        for name in modules:
            m = importlib.reload(getattr(registrationViewerLib, name))
            setattr(registrationViewerLib, name, m)  # type: ignore
            globals()[name] = m  # type: ignore

        self.logger = None

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

        def toggle_simple_ui_button_visibility(self):
            self.ui_sub_1.simple_ui_button.setVisible(
                not self.ui_sub_1.simple_ui_button.isVisible())

            if self.ui_sub_1.simple_ui_button.isVisible():
                text = "Organiser showed advanced button"
            else:
                text = "Organiser hid advanced button"
            custom_logging.log(
                logging.INFO, custom_logging.LogType.INTERNAL, text)

        self.console_visible = True

        def toggle_console_visibility(self):

            if self.console_visible:
                text = "Organiser opened console"
            else:
                text = "Organiser closed console"
            custom_logging.log(
                logging.INFO, custom_logging.LogType.INTERNAL, text)

            slicer.util.setPythonConsoleVisible(self.console_visible)
            self.console_visible = not self.console_visible

        utils.create_shortcuts(
            ('s', self.on_synchronise_views_wth_trasform),
            # ('m', self.on_synchronise_views_manually),
            ('t', lambda: study_connections.key_call_on_synchronise_views_general(self)),
            ('Ctrl+k', lambda: toggle_simple_ui_button_visibility(self)),
            ('Ctrl+p', lambda: toggle_console_visibility(self)),
        )

        self.study_current_transform_type: 'utils.TransformType' = utils.TransformType.NONE

        self.use_transform = True
        self.use_only_linear_transform = False
        self.reverse_transformation_direction = True
        self.current_offset = [0.0, 0.0, 0.0]

        self.crosshair = None

        self.logic = registrationViewerLogic()

        self.synchronise_with_displacement_pressed = False
        self.synchronise_manually_pressed = False

        self.cursor_view: str = ""

        self.node_moving_warped = None
        self.node_diff = None

        self.current_layout: 'view_logic.Layout'

        self.ui_is_simple = False

        self.node_transform_fixed = None
        self.node_transform_moving = None

        self.node_seg_fixed = None
        self.node_seg_moving = None

        # we need to store our tags so we can specifically remove only them
        self.crosshair_custom_observer_tags = []

        self.current_loaded_case_path = ""

        # ANNOTATIONS
        self.annotations_already_saved = False
        self.annotation_fixed_roi_lymphnode = None
        self.annotation_moving_roi_lymphnode = None
        self.annotation_lymphnode_size: Literal["Size same",
                                                "Size increased",
                                                "Size decreased"] = "Size same"

        self.annotation_fixed_points = None
        self.annotation_moving_points = None

        self.annotation_fixed_roi_recurrence = None

        # STUDY
        self.study_data: 'study.StudyData' = None

        self.current_radiologist_id: str = ""
        self.chunk_idx = 0
        self.current_combination_idx: int = 0
        self.combination_starting_offset: int = 0
        self.current_test_combination_idx: int = 0
        self.applied_starting_offset: bool = False

        self.current_patient_list = []

        self.study_loaded_data: dict[str,
                                     dict[str, vtkMRMLScalarVolumeNode]] = {}

        self.study_node_annotation = None

        self.study_node_groundtruth_points = {}

        self.arrow_key_filter = utils.ArrowKeyFilter()

        self.slider_observers: Dict[str, Callable[[float], None]] = {}

        self.first_time_description_show: bool = True
        self.first_time_test_description_show: bool = True

        self.checkbox_test_cases: bool = False

        self.dummy_patient_step: Literal["start", "end"] = "start"

        # task specific
        self.study_gt_lymphnode_description: dict[str, str] = {}
        self.study_gt_recurrence_description: dict[str, str] = {}
        self.study_lymphnode_size: Literal["Size same",
                                           "Size increased",
                                           "Size decreased"] = "Size same"

        self.study_recurrence_present: bool = False

        self.study_progress_bar_patients = None
        self.study_progress_bar_tasks = None

        self.current_view: str = ""
        self.current_view_observer_tag = []

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        mainWidget = slicer.util.loadUI(
            self.resourcePath("UI/registrationViewer.ui"))
        self.layout.addWidget(mainWidget)
        self.ui = slicer.util.childWidgetVariables(mainWidget)

        self.all_uis = [self.ui]

        num_sub_components = len([f for f in os.listdir(self.resourcePath(
            "UI")) if "subComponent" in f and not 'TEMPLATE' in f])

        for i in range(1, num_sub_components + 1):  # 1-based index
            setattr(self,
                    f"sub_widget_{i}",
                    slicer.util.loadUI(self.resourcePath(f"UI/subComponent{i}.ui")))

            placeholder = getattr(self.ui, f"subWidgetPlaceholder_{i}")
            sub_widget = getattr(self, f"sub_widget_{i}")
            placeholder.layout().addWidget(sub_widget)

            setattr(self,
                    f"ui_sub_{i}",
                    slicer.util.childWidgetVariables(sub_widget))

            self.all_uis.append(getattr(self, f"ui_sub_{i}"))

        self.ui_sub_2.data_master_path_edit.filters = ctk.ctkPathLineEdit.Files
        self.ui_sub_2.data_master_path_edit.nameFilters = [
            "JSON files (*.json)"]

        default_path = "/home/koeglf/Documents/code/registrationViewer/registrationViewer/Resources/example_study/data_master_random.json"
        if os.path.exists(default_path):
            self.ui_sub_2.data_master_path_edit.currentPath = default_path

        slicer.app.processEvents()  # Ensures all widgets are fully rendered

        # Set MRML scene for main UI (but not generic QWidgets)
        mainWidget.setMRMLScene(slicer.mrmlScene)

        # If sub-widgets contain MRML-aware widgets, set the scene for them
        for widget in [self.sub_widget_1, self.sub_widget_2, self.sub_widget_3, self.sub_widget_4]:
            for child in widget.findChildren(slicer.qMRMLWidget):
                child.setMRMLScene(slicer.mrmlScene)

        for selector in [self.ui_sub_3.inputSelector_fixed,
                         self.ui_sub_3.inputSelector_moving,
                         self.ui_sub_3.inputSelector_transformation]:
            selector.setMRMLScene(slicer.mrmlScene)

        mainWidget.connect("mrmlSceneChanged(vtkMRMLScene*)",
                           self.ui_sub_3.inputSelector_fixed.setMRMLScene)
        mainWidget.connect("mrmlSceneChanged(vtkMRMLScene*)",
                           self.ui_sub_3.inputSelector_moving.setMRMLScene)
        mainWidget.connect("mrmlSceneChanged(vtkMRMLScene*)",
                           self.ui_sub_3.inputSelector_transformation.setMRMLScene)

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(
            slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene,
                         slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        self.remove_custom_observers_from_crosshair()
        self._remove_view_observers_from_crosshair()
        self.synchronise_with_displacement_pressed = False
        self.ui_sub_4.synchronise_views_with_transform.setText(
            "Synchronise views with transform (t)")

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

        # CONNECTIONS
        # Study
        study_connections.set_connections(self)

        # Buttons
        self.ui_sub_1.simple_ui_button.connect(
            "clicked(bool)", lambda: study_connections.btn_call_on_simple_ui(self))
        self.ui_sub_4.button_2x3.connect(
            "clicked(bool)", view_logic.set_2x3_layout)
        self.ui_sub_4.button_3x3.connect("clicked(bool)", lambda: view_logic.set_3x3_layout(
            self.update_views_third_row_with_volume_diff))
        self.ui_sub_4.synchronise_views_with_transform.connect(
            "clicked(bool)", self.on_synchronise_views_wth_trasform)
        self.ui_sub_4.synchronise_views_manually.connect(
            "clicked(bool)", self.on_synchronise_views_manually)
        self.ui_sub_4.linearTransformationCheckBox.toggled.connect(
            self.on_linear_only)
        self.ui_sub_4.remove_all_data.connect(
            "clicked(bool)", self.on_remove_all_data)

        # ANOOTATIONS
        annotations_connections.set_connections(self)

        # loading code
        drop_data_loading.create_loading_ui(self)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

        utils.collapse_all_segmentations()

        view_logic.link_views(self.views_first_row)
        view_logic.link_views(self.views_second_row)
        view_logic.link_views(self.views_third_row)

        view_logic.set_2x3_layout()

        slicer.util.resetSliceViews()

        # self.dropWidget.load_data_from_dropped_folder(
        #     "/home/koeglf/data/debugging/SerielleCTs_nii_forHumans/LB9oATPd0mE")
        # # utils.temp_load_data(self)

        # slicer.util.setDataProbeVisible(False)

        self.update_current_view()

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        sectra.disable_sectra_movements()

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
        self._remove_view_observers_from_crosshair()
        self.synchronise_with_displacement_pressed = False
        self.ui_sub_4.synchronise_views_with_transform.setText(
            "Synchronise views with transform (t)")

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

            range_of_volume = utils.get_range_of_values(node)

            if not (range_of_volume[0] >= -1 and range_of_volume[1] <= 2):
                utils.set_window_level_and_threshold(node,
                                                     window=1036,
                                                     level=329,
                                                     threshold=(-1024, 3071))

        # reset field of view for view 0, 3 and 6
        for view in [self.views_first_row[0], self.views_second_row[0], self.views_third_row[0]]:
            slicer.app.layoutManager().sliceWidget(
                view).sliceController().fitSliceToBackground()

        utils.collapse_all_segmentations()
        utils.set_all_segmentation_visibility(True)

        view_logic.link_views(self.views_first_row)
        view_logic.link_views(self.views_second_row)
        view_logic.link_views(self.views_third_row)

    def _enable_sectr_movements(self) -> None:

        custom_logging.configure_logger(self,
                     "/home/koeglf/Documents/code/registrationViewer/registrationViewer/default.log",
                     "RegistrationEvaluation")  # nopep8

        sectra.setup_sectra_movements(self)
        sectra.enable_sectra_movements()

    def update_current_layout(self, layout: view_logic.Layout) -> None:
        self.current_layout = layout

    def update_views_third_row_with_volume_diff(self) -> None:

        try:

            if self.node_fixed is not None and \
                    self.node_moving is not None and \
                    self.node_transform_nonlinear is not None:

                title = "Creating difference view..."
                slicer.progressWindow = slicer.util.createProgressDialog()
                slicer.progressWindow.show()
                slicer.progressWindow.activateWindow()
                slicer.progressWindow.setValue(0)
                slicer.progressWindow.setLabelText(title)
                slicer.app.processEvents()

                offset_red1 = view_logic.get_view_offset("Red1")
                offset_green1 = view_logic.get_view_offset("Green1")
                offset_yellow1 = view_logic.get_view_offset("Yellow1")

                node_fixed_transformed_with_affine = slicer.modules.volumes.logic().CloneVolume(self.node_fixed,
                                                                                                "Fixed with affine")
                utils.apply_and_harden_transform_to_node(node_fixed_transformed_with_affine,
                                                         self.node_transform_fixed)

                node_moving_transformed_with_affine = slicer.modules.volumes.logic().CloneVolume(self.node_moving,
                                                                                                 "Moving with affine")
                utils.apply_and_harden_transform_to_node(node_moving_transformed_with_affine,
                                                         self.node_transform_moving)

                if not utils.update_progress_window(20, title):
                    return

                if self.node_diff is None:
                    self.node_diff = slicer.modules.volumes.logic().CloneVolume(node_fixed_transformed_with_affine,
                                                                                "Difference")

                if self.node_moving_warped is not None:
                    slicer.mrmlScene.RemoveNode(self.node_moving_warped)

                self.node_moving_warped = slicer.modules.volumes.logic().CloneVolume(node_moving_transformed_with_affine,
                                                                                     "Warped")
                if not utils.update_progress_window(40, title):
                    return

                utils.apply_and_harden_transform_to_node(
                    self.node_moving_warped, self.node_transform_nonlinear)
                self.node_moving_warped = utils.normalize_node(
                    self.node_moving_warped)
                node_fixed_transformed_with_affine = utils.normalize_node(
                    node_fixed_transformed_with_affine)
                utils.resample_node_to_reference_node(
                    self.node_moving_warped, node_fixed_transformed_with_affine)

                if not utils.update_progress_window(60, title):
                    return

                array_fixed = slicer.util.arrayFromVolume(
                    node_fixed_transformed_with_affine)
                array_warped = slicer.util.arrayFromVolume(
                    self.node_moving_warped)

                array_diff = np.abs(array_fixed - array_warped)

                slicer.util.updateVolumeFromArray(self.node_diff, array_diff)

                if not utils.update_progress_window(80, title):
                    return

                utils.apply_and_harden_transform_to_node(self.node_diff,
                                                         self.node_transform_fixed,
                                                         invert=True)

                view_logic.update_views_with_volume(
                    self.views_third_row, self.node_diff)

                slicer.mrmlScene.RemoveNode(
                    node_fixed_transformed_with_affine)
                slicer.mrmlScene.RemoveNode(
                    node_moving_transformed_with_affine)

                slicer.util.resetSliceViews()

                view_logic.set_view_offset("Red3", offset_red1)
                view_logic.set_view_offset("Green3", offset_green1)
                view_logic.set_view_offset("Yellow3", offset_yellow1)

                utils.set_window_level_and_threshold(self.node_diff,
                                                     window=0.43,
                                                     level=0.16,
                                                     threshold=(0, 1))

                slicer.progressWindow.close()

        except Exception as e:
            slicer.progressWindow.close()
            logging.error(f"Error loading data: {str(e)}")
            slicer.util.errorDisplay(f"Error loading data: {str(e)}")

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

    def on_synchronise_views_wth_trasform(self) -> None:
        if not self.synchronisation_checks():
            return

        if self.current_patient_list != [] and self.current_patient_transform_type == utils.TransformType.NONE:
            print('not synchronising because we have None transform')
            return

        self.synchronise_with_displacement_pressed = not self.synchronise_with_displacement_pressed

        if self.synchronise_with_displacement_pressed is True:
            self._set_up_crosshair(self.synchronise_with_displacement_pressed)
            print("pressed to synchronise")
            self.ui_sub_4.synchronise_views_with_transform.setText(
                "Unsynchronise views with transform (t)")
            self.ui_sub_6.synchronise_views_general.setText(
                texts.Buttons.TURN_TRANSFORMATION_OFF)

            self.use_transform = self.crosshair.use_transform = True
            self.crosshair.use_only_linear_transform = self.use_only_linear_transform
            print(f"{self.use_only_linear_transform=}")

            self.crosshair.offset_diffs = self.current_offset = [0, 0, 0]
            self.crosshair.apply_offsets = False
            self.ui_sub_4.synchronise_views_manually.setText(
                "Synchronise views manually (m)")
            self.synchronise_manually_pressed = False
        else:
            print("pressed to unsynchronise")
            self.remove_custom_observers_from_crosshair()
            self.ui_sub_4.synchronise_views_with_transform.setText(
                "Synchronise views with transform (t)")
            self.ui_sub_6.synchronise_views_general.setText(
                texts.Buttons.TURN_TRANSFORMATION_ON)

    def on_synchronise_views_manually(self) -> None:

        if not self.synchronisation_checks():
            return

        self.synchronise_manually_pressed = not self.synchronise_manually_pressed

        if self.synchronise_manually_pressed is True:
            self._set_up_crosshair(self.synchronise_manually_pressed)
            print("pressed to synchronise manually")
            self.ui_sub_4.synchronise_views_manually.setTfnext(
                "Unsynchronise views manually (m)")

            self.use_transform = self.crosshair.use_transform = False
            self.ui_sub_4.synchronise_views_with_transform.setText(
                "Synchronise views with transform (t)")
            self.synchronise_with_displacement_pressed = False
            self.ui_sub_4.linearTransformationCheckBox.setEnabled(False)

        else:
            print("pressed to unsynchronise manually")
            self.remove_custom_observers_from_crosshair()
            self.ui_sub_4.synchronise_views_manually.setText(
                "Synchronise views manually (m)")

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

    def unsynchronise_views(self) -> None:
        print('unsynchronised')
        self.remove_custom_observers_from_crosshair()
        self.ui_sub_4.synchronise_views_with_transform.setText(
            "Synchronise views with transform (t)")
        self.ui_sub_6.synchronise_views_general.setText(
            texts.Buttons.TURN_TRANSFORMATION_ON)

    def on_linear_only(self) -> None:
        print("on linear only")
        self.use_only_linear_transform = self.crosshair.use_only_linear_transform = not self.use_only_linear_transform

    def on_remove_all_data(self) -> None:
        if self.node_fixed is not None:
            slicer.mrmlScene.RemoveNode(self.node_fixed)

        if self.node_moving is not None:
            slicer.mrmlScene.RemoveNode(self.node_moving)

        if self.node_transform_nonlinear is not None:
            slicer.mrmlScene.RemoveNode(self.node_transform_nonlinear)

        if self.node_diff is not None:
            slicer.mrmlScene.RemoveNode(self.node_diff)
            self.node_diff = None

        if self.node_moving_warped is not None:
            slicer.mrmlScene.RemoveNode(self.node_moving_warped)
            self.node_moving_warped = None

        if self.node_transform_fixed is not None:
            slicer.mrmlScene.RemoveNode(self.node_transform_fixed)
            self.node_transform_fixed = None

        if self.node_transform_moving is not None:
            slicer.mrmlScene.RemoveNode(self.node_transform_moving)
            self.node_transform_moving = None

        if self.node_seg_fixed is not None:
            slicer.mrmlScene.RemoveNode(self.node_seg_fixed)
            self.node_seg_fixed = None

        if self.node_seg_moving is not None:
            slicer.mrmlScene.RemoveNode(self.node_seg_moving)
            self.node_seg_moving = None

    def update_cursor_view(self) -> None:

        def wrapper(self: "registrationViewerWidget", callee, event):  # pylint: disable=unused-argument
            position = self.node_crosshair.GetCursorPositionXYZ([0]*3)
            if position is not None:
                self.crosshair.cursor_view = position.GetName()

        observer_tag = self.node_crosshair.AddObserver(slicer.vtkMRMLCrosshairNode.CursorPositionModifiedEvent,
                                                       functools.partial(wrapper, self))
        self.crosshair_custom_observer_tags.append(observer_tag)

    def update_current_view(self) -> None:

        def wrapper(self: "registrationViewerWidget", callee, event):  # pylint: disable=unused-argument
            position = self.node_crosshair.GetCursorPositionXYZ([0]*3)
            if position is not None:
                self.current_view = position.GetName()

        observer_tag = self.node_crosshair.AddObserver(slicer.vtkMRMLCrosshairNode.CursorPositionModifiedEvent,
                                                       functools.partial(wrapper, self))
        self.current_view_observer_tag.append(observer_tag)

    def _remove_custom_nodes(self) -> None:
        if self.node_diff is not None:
            slicer.mrmlScene.RemoveNode(self.node_diff)
            self.node_diff = None
        if self.node_moving_warped is not None:
            slicer.mrmlScene.RemoveNode(self.node_moving_warped)
            self.node_moving_warped = None
        if self.crosshair is not None:
            self.crosshair.delete_crosshairs_and_folder()
            self.crosshair = None

    def _are_nodes_selected(self) -> bool:
        return self.ui_sub_3.inputSelector_fixed.currentNode() is not None and \
            self.ui_sub_3.inputSelector_moving.currentNode() is not None and \
            self.ui_sub_3.inputSelector_transformation.currentNode() is not None

    def _set_up_crosshair(self, turn_synchronisation_on: bool) -> None:
        if self.crosshair:
            self.crosshair.delete_crosshairs_and_folder()

        self.crosshair = crosshairs.Crosshairs(node_cursor=self.node_crosshair,
                                               node_transform_nonlinear=self.node_transform_nonlinear,
                                               node_transform_fixed=self.node_transform_fixed,
                                               node_transform_moving=self.node_transform_moving,
                                               use_transform=self.use_transform,
                                               use_only_linear_transform=self.use_only_linear_transform,
                                               offset_diffs=self.current_offset,
                                               apply_offsets=self.synchronise_manually_pressed)

        self.ui_sub_4.linearTransformationCheckBox.setEnabled(True)

        if turn_synchronisation_on:
            observer_tag = self.node_crosshair.AddObserver(slicer.vtkMRMLCrosshairNode.CursorPositionModifiedEvent,
                                                           self.crosshair.on_mouse_moved_place_crosshair)
            self.crosshair_custom_observer_tags.append(observer_tag)
            self.update_cursor_view()

    def _update_crosshair_transformation(self) -> None:
        if self.crosshair:
            self.crosshair.node_transform_nonlinear = self.node_transform_nonlinear
            self.crosshair.node_transform_fixed = self.node_transform_fixed
            self.crosshair.node_transform_moving = self.node_transform_moving
            self.crosshair.use_only_linear_transform = self.use_only_linear_transform

    def remove_custom_observers_from_crosshair(self) -> None:
        for observer_tag in self.crosshair_custom_observer_tags:
            if self.node_crosshair:
                self.node_crosshair.RemoveObserver(observer_tag)

        self.crosshair_custom_observer_tags.clear()

    def _remove_view_observers_from_crosshair(self) -> None:
        for observer_tag in self.current_view_observer_tag:
            self.node_crosshair.RemoveObserver(observer_tag)

        self.current_view_observer_tag.clear()

    def get_combination(self, idx: int) -> Tuple[str, str, str]:
        """
        Get the combination of patient name, task and transformation type
        """
        if self.current_patient_list == []:
            return ("", "", "")

        return self.study_data.case_task_transformation_map[self.current_radiologist_id][idx]

    @property
    def node_fixed(self) -> Any:
        return self.ui_sub_3.inputSelector_fixed.currentNode()

    @property
    def node_moving(self) -> Any:
        return self.ui_sub_3.inputSelector_moving.currentNode()

    @property
    def node_crosshair(self) -> Any:
        return slicer.util.getNode("Crosshair")

    @property
    def node_transform_nonlinear(self) -> Any:
        return self.ui_sub_3.inputSelector_transformation.currentNode()

    @property
    def current_task(self) -> tasks.Task:
        if self.current_patient_task_transform_comb == ("", "", ""):
            return tasks.Task.NONE

        return tasks.Task(self.current_patient_task_transform_comb[1])

    @property
    def number_of_tasks(self) -> int:

        if self.current_patient_list == []:
            return 0

        return self.study_data.number_of_tasks(self.current_radiologist_id) - self.number_of_test_tasks

    @property
    def number_of_test_tasks(self) -> int:
        if self.current_patient_list == []:
            return 0

        if self.show_test_cases:
            return 3
        else:
            return 0

    @property
    def show_test_cases(self) -> bool:
        """
        Check if the training cases should be shown.
        """
        if self.current_patient_list == []:
            return False

        return self.checkbox_test_cases

    @property
    def current_patient_name(self) -> str:
        if self.current_patient_task_transform_comb == ("", "", ""):
            return "no_patient"

        return self.current_patient_task_transform_comb[0][1]

    @property
    def previous_patient_name(self) -> str:
        if self.current_patient_task_transform_comb == ("", "", ""):
            return "no_patient"

        if self.current_combination_idx == 0:
            return "no_patient"

        return self.study_data.case_task_transformation_map[self.current_radiologist_id][self.current_combination_idx - 1][0][1]

    @property
    def current_patient_transform_type(self) -> utils.TransformType:
        if self.current_patient_task_transform_comb == ("", "", ""):
            return utils.TransformType.NONE

        return utils.TransformType(self.current_patient_task_transform_comb[2])

    @property
    def current_patient_task_transform_comb(self) -> Tuple[str, str, str]:
        if self.current_patient_list == []:
            return ("", "", "")

        return self.study_data.case_task_transformation_map[self.current_radiologist_id][self.current_combination_idx]

    def patient_task_transform_comb(self, idx: int) -> Tuple[str, str, str]:
        if self.current_patient_list == []:
            return ("", "", "")

        return self.study_data.case_task_transformation_map[self.current_radiologist_id][idx]

    @property
    def is_current_patient_task_transform_comb_test(self) -> bool:
        """
        Check if the current combination is a test task.
        """
        if self.current_patient_task_transform_comb == ("", "", ""):
            return False

        return tasks.Task(self.current_patient_task_transform_comb[1]) in [tasks.Task.TEST_NONE, tasks.Task.TEST_ROTATION, tasks.Task.TEST_NONLINEAR]

    def is_patient_task_transform_comb_test(self, idx: int) -> bool:
        """
        Check if the current combination is a test task.
        """
        if self.current_patient_task_transform_comb == ("", "", ""):
            return False

        return tasks.Task(self.patient_task_transform_comb(idx)[1]) in [tasks.Task.TEST_NONE, tasks.Task.TEST_ROTATION, tasks.Task.TEST_NONLINEAR]

    @property
    def current_radiologist_name(self) -> str:

        return self.study_data.participants[self.current_radiologist_id]['name']

    @property
    def next_task_log_text(self) -> str:
        if self.is_current_patient_task_transform_comb_test:
            return "Next test task"

        return "Next task"

    @property
    def start_task_log_text(self) -> str:
        if self.is_current_patient_task_transform_comb_test:
            return "Start test task"

        return "Start task"

    @property
    def start_task_log_text_user(self) -> str:
        if self.is_current_patient_task_transform_comb_test:
            return "User started test task"

        return "User started task"


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
