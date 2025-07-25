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
from registrationViewerLib import utils, sectra, crosshairs, view_logic, drop_data_loading, study, tasks, texts


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
            "utils", "sectra", "crosshairs",
            "view_logic", "drop_data_loading",
            "study", "tasks", "texts"
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

        utils.create_shortcuts(
            ('s', self.on_synchronise_views),
        )

        self.study_current_transform_type: 'utils.TransformType' = utils.TransformType.NONE

        self.use_transform = True
        self.use_only_linear_transform = False
        self.reverse_transformation_direction = True
        self.current_offset = [0.0, 0.0, 0.0]
        self.offset_set = False

        self.crosshair = None

        self.logic = registrationViewerLogic()

        self.synchronise_with_displacement_pressed = False
        self.synchronise_manually_pressed = False

        self.node_moving_warped = None
        self.node_diff = None

        self.current_layout: 'view_logic.Layout'

        self.ui_is_simple = False

        self.node_transform_fixed = None
        self.node_transform_moving = None

        self.node_seg_fixed = None
        self.node_seg_moving = None

        self.crosshair_custom_observer_tags = []

        self.current_loaded_case_path = ""

        # STUDY
        self.study_data: 'study.StudyData' = None

        self.full_screen_block: utils.FullScreenBlock = utils.FullScreenBlock()

        self.current_radiologist_id: str = ""
        self.chunk_idx = 0
        self.current_combination_idx: int = 0
        self.combination_starting_offset: int = 0
        self.current_training_combination_idx: int = 0
        self.applied_starting_offset: bool = False

        self.study_loaded_data: dict[str,
                                     dict[str, vtkMRMLScalarVolumeNode]] = {}

        self.study_node_annotation = None

        self.study_node_groundtruth_points = {}

        self.arrow_key_filter = utils.ArrowKeyFilter()

        self.slider_observers: Dict[str, Callable[[float], None]] = {}

        self.first_time_description_show: bool = True
        self.first_time_training_description_show: bool = True
        self.first_time_info_show: bool = True

        self.checkbox_training_cases: bool = True

        # task specific
        self.study_gt_lymphnode_description: dict[str, str] = {}
        self.study_gt_recurrence_description: dict[str, str] = {}
        self.study_lymphnode_size: Literal["Size same",
                                           "Size increased",
                                           "Size decreased"] = "Size same"

        self.study_recurrence_present: bool = False

        self.study_progress_bar_patients: utils.ProgressBar
        self.study_progress_bar_tasks: utils.ProgressBar

        self.temp_enabled = False

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

        # # If sub-widgets contain MRML-aware widgets, set the scene for them
        # for widget in [self.sub_widget_3, self.sub_widget_4]:
        #     for child in widget.findChildren(slicer.qMRMLWidget):
        #         child.setMRMLScene(slicer.mrmlScene)

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

        # Buttons
        self.ui.synchronise_views_with_transform.connect(
            "clicked(bool)", self.on_synchronise_views)

        # loading code
        drop_data_loading.create_loading_ui(self)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

        view_logic.link_views(self.views_first_row)
        view_logic.link_views(self.views_second_row)

        view_logic.set_2x3_layout()

        slicer.util.resetSliceViews()

        # self.dropWidget.load_data_from_dropped_folder(
        #     "/home/koeglf/data/debugging/SerielleCTs_nii_forHumans/LB9oATPd0mE")
        # # utils.temp_load_data(self)

        # slicer.util.setDataProbeVisible(False)

        a = r"/home/koeglf/data/registrationStudy/SerielleCTs_nii_forHumans/training/training_4_yIt7Z7VHXU0"
        # self.dropWidget.load_data_from_dropped_folder(a)

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

        # reset field of view for view 0, 3 and 6
        for view in [self.views_first_row[0], self.views_second_row[0]]:
            slicer.app.layoutManager().sliceWidget(
                view).sliceController().fitSliceToBackground()

        view_logic.link_views(self.views_first_row)
        view_logic.link_views(self.views_second_row)

    def update_current_layout(self, layout: view_logic.Layout) -> None:
        self.current_layout = layout

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
                "Unsynchronise views with transform (t)")

            self.use_transform = self.crosshair.use_transform = True
            self.crosshair.use_only_linear_transform = self.use_only_linear_transform
            print(f"{self.use_only_linear_transform=}")

            self.crosshair.offset_diffs = self.current_offset = [0, 0, 0]
            self.crosshair.apply_offsets = False
            self.synchronise_manually_pressed = False
        else:
            print("pressed to unsynchronise")
            self.remove_custom_observers_from_crosshair()
            self.ui.synchronise_views_with_transform.setText(
                "Synchronise views with transform (t)")

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
                                               node_transform_fixed=self.node_transform_fixed,
                                               node_transform_moving=self.node_transform_moving,
                                               use_transform=self.use_transform,
                                               use_only_linear_transform=self.use_only_linear_transform,
                                               offset_diffs=self.current_offset,
                                               apply_offsets=self.synchronise_manually_pressed)

        if turn_synchronisation_on:
            observer_tag = self.node_crosshair.AddObserver(slicer.vtkMRMLCrosshairNode.CursorPositionModifiedEvent,
                                                           self.crosshair.on_mouse_moved_place_crosshair)
            self.crosshair_custom_observer_tags.append(observer_tag)

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

    def get_combination(self, idx: int) -> Tuple[str, str, str]:
        """
        Get the combination of patient name, task and transformation type
        """

        return self.study_data.case_task_transformation_map[self.current_radiologist_id][idx]

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

    @property
    def current_task(self) -> tasks.Task:
        if self.current_patient_task_transform_comb == ("", "", ""):
            return tasks.Task.NONE

        return tasks.Task(self.current_patient_task_transform_comb[1])

    @property
    def number_of_all_tasks(self) -> int:
        """
        Get the number of all tasks for the current radiologist.
        This includes training tasks.
        """
        return self.study_data.number_of_tasks()

    @property
    def number_of_study_tasks(self) -> int:

        return self.study_data.number_of_tasks() - self.study_data.number_of_training_tasks

    @property
    def number_of_training_tasks(self) -> int:

        return self.study_data.number_of_training_tasks

    @property
    def number_of_simple_training_tasks(self) -> int:
        return self.study_data.number_of_simple_training_tasks

    @property
    def number_of_full_training_tasks(self) -> int:
        return self.study_data.number_of_full_training_tasks

    def number_of_study_patients(self, with_calibration: bool = False) -> int:

        return self.study_data.number_of_patients(with_calibration)

    @property
    def number_of_training_patients(self) -> int:

        return self.study_data.number_of_training_patients

    @property
    def number_of_simple_training_patients(self) -> int:
        return self.study_data.number_of_simple_training_patients

    @property
    def number_of_full_training_patients(self) -> int:
        return self.study_data.number_of_full_training_patients

    @property
    def current_patient_idx(self) -> int:

        return self.study_data.current_patient_idx(self.current_patient_name)

    @property
    def show_training_cases(self) -> bool:
        """
        Check if the training cases should be shown.
        """
        return self.checkbox_training_cases

    @property
    def current_patient_name(self) -> str:
        if self.current_patient_task_transform_comb == ("", "", ""):
            return "no_patient"

        return self.current_patient_task_transform_comb[0]

    @property
    def previous_patient_name(self) -> str:
        if self.current_patient_task_transform_comb == ("", "", ""):
            return "no_patient"

        if self.current_combination_idx == 0:
            return "no_patient"

        return self.study_data.case_task_transformation_map[self.current_radiologist_id][self.current_combination_idx - 1][0]

    @property
    def current_patient_transform_type(self) -> utils.TransformType:
        if self.current_patient_task_transform_comb == ("", "", ""):
            return utils.TransformType.NONE

        return utils.TransformType(self.current_patient_task_transform_comb[2])

    @property
    def current_patient_task_transform_comb(self) -> Tuple[str, str, str]:

        return self.study_data.case_task_transformation_map[self.current_radiologist_id][self.current_combination_idx]

    def patient_task_transform_comb(self, idx: int) -> Tuple[str, str, str]:

        return self.study_data.case_task_transformation_map[self.current_radiologist_id][idx]

    @property
    def is_current_task_training(self) -> bool:
        """
        Check if the current combination is a training task.
        """

        return self.current_patient_name in self.study_data.training_case_names

    @property
    def is_current_task_full_training_example(self) -> bool:
        """
        Check if the current combination is a full training task.
        """

        return self.current_patient_name in self.study_data.full_training_case_names

    @property
    def is_current_task_simple_training_example(self) -> bool:
        """
        Check if the current combination is a full training task.
        """

        return self.current_patient_name in self.study_data.simple_training_case_names

    def is_patient_task_transform_comb_training(self, idx: int) -> bool:
        """
        Check if the current combination is a training task.
        """
        if self.current_patient_task_transform_comb == ("", "", ""):
            return False

        return "training" in self.patient_task_transform_comb(idx)[0]

    @property
    def current_radiologist_name(self) -> str:

        return self.study_data.participants[self.current_radiologist_id]['name']

    @property
    def next_task_log_text(self) -> str:
        # if self.is_current_task_training:
        #     return "Next training task"

        return "Next task"

    @property
    def start_task_log_text(self) -> str:
        # if self.is_current_task_training:
        #     return "Start training task"

        return "Start task"

    @property
    def start_task_log_text_user(self) -> str:
        if self.is_current_task_training:
            return "User started training task"

        return "User started task"

    def transform_crosshair_nodes(self,
                                  node: slicer.vtkMRMLMarkupsFiducialNode,
                                  invert: bool) -> None:
        """
        Transform every crosshair from the list of nodes with the current transformation.
        """
        # first move to fixed space, then deform then move back to moving space

        if self.node_transform_nonlinear:
            if invert:
                if self.node_transform_fixed:
                    node.ApplyTransform(
                        self.node_transform_fixed.GetTransformToParent())
                if not self.use_only_linear_transform:
                    node.ApplyTransform(
                        self.node_transform_nonlinear.GetTransformFromParent())
                if self.node_transform_moving:
                    node.ApplyTransform(
                        self.node_transform_moving.GetTransformFromParent())
            else:
                if self.node_transform_moving:
                    node.ApplyTransform(
                        self.node_transform_moving.GetTransformToParent())
                if not self.use_only_linear_transform:
                    node.ApplyTransform(
                        self.node_transform_nonlinear.GetTransformToParent())
                if self.node_transform_fixed:
                    node.ApplyTransform(
                        self.node_transform_fixed.GetTransformFromParent())

        else:
            print("No transformation available")

    def evaluate_lymph_node(
        self,
        logger: logging.Logger,
        study_a: str,
        study_b: str,
        patient_name: str,
        count: int,
        numbr_of_patients: int
    ) -> None:

        path_lymph_a = glob.glob(study_a + "/roi_lymphnode*.mrk.json")[0]
        path_lymph_b = glob.glob(study_b + "/roi_lymphnode*.mrk.json")[0]

        dist_dict = {}

        for linear_only in [True, False]:

            self.use_only_linear_transform = linear_only

            lymph_a = slicer.util.loadMarkups(path_lymph_a)
            lymph_b = slicer.util.loadMarkups(path_lymph_b)

            self.transform_crosshair_nodes(lymph_b, invert=True)

            center_a = np.array(lymph_a.GetNthControlPointPosition(0))
            center_b = np.array(lymph_b.GetNthControlPointPosition(0))

            distance = np.linalg.norm(center_a - center_b)

            dist_dict[linear_only] = distance

            slicer.mrmlScene.RemoveNode(lymph_a)
            slicer.mrmlScene.RemoveNode(lymph_b)

        logger.log(
            logging.DEBUG, f"({count}/{numbr_of_patients}) {patient_name} ~ lymph node distance: {dist_dict[True]}, {dist_dict[False]}")

    def evaluate_bifurcation(
        self,
        logger: logging.Logger,
        study_a: str,
        study_b: str,
        patient_name: str,
        count: int,
        numbr_of_patients: int
    ) -> None:
        path_points_a = glob.glob(study_a + "/points_*.mrk.json")[0]
        path_points_b = glob.glob(study_b + "/points_*.mrk.json")[0]

        points_a = slicer.util.loadMarkups(path_points_a)
        points_b = slicer.util.loadMarkups(path_points_b)
        self.transform_crosshair_nodes(points_b, invert=True)

        dict_points_a = {}
        dict_points_b = {}

        for i in range(points_a.GetNumberOfControlPoints()):
            pos_a = np.array(points_a.GetNthControlPointPosition(i))
            pos_b = np.array(points_b.GetNthControlPointPosition(i))

            name_a = points_a.GetNthControlPointLabel(i)
            name_b = points_b.GetNthControlPointLabel(i)

            name_a = '_'.join(name_a.split('_')[1:4])
            name_b = '_'.join(name_b.split('_')[1:4])

            dict_points_a[name_a] = pos_a
            dict_points_b[name_b] = pos_b

        if set(dict_points_a.keys()) != set(dict_points_b.keys()):
            # print(f"{dict_points_a=}")
            # print(f"{dict_points_b=}")
            logger.log(logging.ERROR,
                       f"Points do not match for {patient_name}")
            return

        for name, pos_a in dict_points_a.items():

            pos_b = dict_points_b[name]

            distance = np.linalg.norm(pos_a - pos_b)

            self.distances[patient_name][name] = distance
            logger.log(
                logging.DEBUG, f"({count}/{numbr_of_patients}) {patient_name} ~ {name.ljust(18)} ~ {distance:05.2f}")

        slicer.mrmlScene.RemoveNode(points_a)
        slicer.mrmlScene.RemoveNode(points_b)

    def evaluate(self, obj: Literal['bifurcation', 'lymph_node']) -> None:

        logger = logging.getLogger(f"Evaluation_{obj.capitalize()}")
        logger.setLevel(logging.DEBUG)

        if logger.hasHandlers():
            logger.handlers.clear()

        fh = logging.FileHandler(
            "/home/koeglf/Documents/code/registrationViewer/registrationViewer/evaluate.log")
        fh.setLevel(logging.DEBUG)

        logger.addHandler(fh)

        all_patients_neg = glob.glob(
            "/home/koeglf/data/registrationStudy/SerielleCTs_nii_forHumans/negative/*")
        all_patients_pos = glob.glob(
            "/home/koeglf/data/registrationStudy/SerielleCTs_nii_forHumans/positive/*")
        all_patients_cal = glob.glob(
            "/home/koeglf/data/registrationStudy/SerielleCTs_nii_forHumans/calibration/*")
        all_patients_train = glob.glob(
            "/home/koeglf/data/registrationStudy/SerielleCTs_nii_forHumans/training/*")

        all_patients = all_patients_neg + all_patients_pos + \
            all_patients_cal + all_patients_train
        self.distances = {}

        count = 0

        for patient in all_patients:
            try:
                count += 1
                patient_name = patient.split('/')[-1]

                self.distances[patient_name] = {}

                self.dropWidget.load_data_from_dropped_folder(patient)

                paths_studies = glob.glob(patient + "/preprocessed/*")
                paths_studies.sort()

                study_a = paths_studies[0] + "/annotations"
                study_b = paths_studies[1] + "/annotations"

                if obj == 'bifurcation':
                    self.evaluate_bifurcation(
                        logger, study_a, study_b, patient_name, count, len(
                            all_patients))
                elif obj == 'lymph_node':
                    self.evaluate_lymph_node(
                        logger, study_a, study_b, patient_name, count, len(
                            all_patients))
                else:
                    raise ValueError(
                        f"Unknown object type: {obj}. Use 'bifurcation' or 'lymph_node'.")
                # delete
                slicer.mrmlScene.RemoveNode(self.node_seg_fixed)
                slicer.mrmlScene.RemoveNode(self.node_seg_moving)
                slicer.mrmlScene.RemoveNode(self.node_transform_fixed)
                slicer.mrmlScene.RemoveNode(self.node_transform_moving)
                slicer.mrmlScene.RemoveNode(
                    self.ui_sub_3.inputSelector_transformation.currentNode())

                slicer.mrmlScene.RemoveNode(self.node_fixed)
                slicer.mrmlScene.RemoveNode(self.node_moving)

                # return

            except:
                logger.log(logging.ERROR, f"couldn't evaluate {patient_name}")

                try:
                    slicer.mrmlScene.RemoveNode(self.node_seg_fixed)
                    slicer.mrmlScene.RemoveNode(self.node_seg_moving)
                    slicer.mrmlScene.RemoveNode(self.node_transform_fixed)
                    slicer.mrmlScene.RemoveNode(self.node_transform_moving)
                    slicer.mrmlScene.RemoveNode(
                        self.ui_sub_3.inputSelector_transformation.currentNode())
                    slicer.mrmlScene.RemoveNode(self.node_fixed)
                    slicer.mrmlScene.RemoveNode(self.node_moving)
                except:
                    pass

            # if count >= 2:
            #     return


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
