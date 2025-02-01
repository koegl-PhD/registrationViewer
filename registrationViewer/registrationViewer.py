import functools
import importlib
import json
import logging
import os
import time

from typing import Optional, List, Any, Literal

import numpy as np

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

from registrationViewerLib import utils, crosshairs, view_logic, drop_data_loading, study_loading, tasks


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

        from registrationViewerLib import utils, tasks, crosshairs, drop_data_loading, view_logic, study_loading
        utils = importlib.reload(utils)
        crosshairs = importlib.reload(crosshairs)
        drop_data_loading = importlib.reload(drop_data_loading)
        view_logic = importlib.reload(view_logic)
        study_loading = importlib.reload(study_loading)
        tasks = importlib.reload(tasks)

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

        utils.create_shortcuts(('t', self.on_synchronise_views_wth_trasform),
                               ('m', self.on_synchronise_views_manually),
                               ('s', self.on_synchronise_views_general))

        self.transformation_mode: 'utils.TransformationMode' = utils.TransformationMode.NON_LINEAR

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

        # ANNOTATIONS
        self.annotations_save_path = "/home/koeglf/data/try_new_preprocessing/annotations/"
        self.annotations_already_saved = False
        self.annotation_fixed_roi_lymphnode = None
        self.annotation_moving_roi_lymphnode = None
        self.annotation_bool_lymphnode_increased = False

        self.annotation_fixed_points = None
        self.annotation_moving_points = None

        self.annotation_fixed_roi_recurrence = None

        # STUDY
        self.path_study_data_master: str = r"/home/koeglf/Documents/code/registrationViewer/registrationViewer/Resources/example_study/data_master.json"
        self.study_data_master: 'study_loading.StudyData' = study_loading.StudyData(
            self.path_study_data_master)
        self.current_radiologist_id: str = ""
        self.current_task: 'tasks.Task' = tasks.Task.NONE

        self.study_points = None

        # UI sub components
        self.ui_sub_1 = None
        self.ui_sub_2 = None

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        mainWidget = slicer.util.loadUI(
            self.resourcePath("UI/registrationViewer.ui"))
        self.layout.addWidget(mainWidget)
        self.ui = slicer.util.childWidgetVariables(mainWidget)

        subWidget1 = slicer.util.loadUI(
            self.resourcePath("UI/subComponent1.ui"))
        subWidget2 = slicer.util.loadUI(
            self.resourcePath("UI/subComponent2.ui"))

        self.ui.subWidget1Placeholder.layout().addWidget(subWidget1)
        self.ui.subWidget2Placeholder.layout().addWidget(subWidget2)

        # Set MRML scene for main UI (but not generic QWidgets)
        mainWidget.setMRMLScene(slicer.mrmlScene)

        # If sub-widgets contain MRML-aware widgets, set the scene for them
        for widget in [subWidget1, subWidget2]:
            for child in widget.findChildren(slicer.qMRMLWidget):
                child.setMRMLScene(slicer.mrmlScene)

        self.ui_sub_1 = slicer.util.childWidgetVariables(subWidget1)
        self.ui_sub_2 = slicer.util.childWidgetVariables(subWidget2)

        """
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
        """
        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(
            slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene,
                         slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        self._remove_custom_observers_from_crosshair()
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

        # CONNECTIONS
        # Study
        self.ui_sub_2.set_radiologist_id_button.connect("clicked(bool)",
                                                        self.on_set_radiologist_id)
        self.ui_sub_2.start_study_button.connect("clicked(bool)",
                                                 self.on_start_study)

        def _on_text_changed():
            self.ui_sub_2.start_study_button.setEnabled(False)
            self.ui_sub_2.radiologistSetCheckBox.setChecked(False)
            self.ui_sub_2.start_study_button.toolTip = "Please set radiologist ID first"
        self.ui_sub_2.radiologistIDTextEdit.textChanged.connect(
            _on_text_changed)

        self.ui.start_study_by_user_button.connect("clicked(bool)",
                                                   self.on_user_start_study)

        self.ui.study_next_task_button.connect("clicked(bool)",
                                               self.on_next_task)

        self.ui.study_add_point_button.connect("clicked(bool)",
                                               self.on_study_add_point)

        # Buttons
        self.ui_sub_1.simple_ui.connect("clicked(bool)", self.on_simple_ui)
        self.ui.button_2x3.connect("clicked(bool)", view_logic.set_2x3_layout)
        self.ui.button_3x3.connect("clicked(bool)", view_logic.set_3x3_layout)
        self.ui.button_3x3.connect("clicked(bool)", lambda: view_logic.set_3x3_layout(
            self.update_views_third_row_with_volume_diff))
        self.ui.synchronise_views_with_transform.connect(
            "clicked(bool)", self.on_synchronise_views_wth_trasform)
        self.ui.synchronise_views_manually.connect(
            "clicked(bool)", self.on_synchronise_views_manually)
        self.ui.synchronise_views_general.connect(
            "clicked(bool)", self.on_synchronise_views_general)
        self.ui.linearTransformationCheckBox.toggled.connect(
            self.on_linear_only)
        self.ui.remove_all_data.connect(
            "clicked(bool)", self.on_remove_all_data)

        # ANOOTATIONS
        self.ui.saveAnnotations.connect("clicked(bool)",
                                        self.on_save_annotations)
        self.ui.clearAnnotations.connect("clicked(bool)",
                                         self.on_clear_annotations)

        self.ui.addLymphnodeRoiFixed.connect("clicked(bool)",
                                             lambda: self.on_add_roi_lymphnode('fixed'))
        self.ui.addLymphnodeRoiMoving.connect("clicked(bool)",
                                              lambda: self.on_add_roi_lymphnode('moving'))
        self.ui.increasedLymphnodeCheckBox.toggled.connect(
            self.on_lymphnode_increased)

        self.ui.addCarotisgabelPointFixed.connect("clicked(bool)",
                                                  lambda: self.on_add_annotation_point_fixed('carotisgabel'))
        self.ui.addCarotisgabelPointMoving.connect("clicked(bool)",
                                                   lambda: self.on_add_annotation_point_moving('carotisgabel'))
        self.ui.addAbgangavertebralisPointFixed.connect("clicked(bool)",
                                                        lambda: self.on_add_annotation_point_fixed('abgangavertebralis'))
        self.ui.addAbgangavertebralisPointMoving.connect("clicked(bool)",
                                                         lambda: self.on_add_annotation_point_moving('abgangavertebralis'))

        self.ui.recurrencePresentCheckBox.toggled.connect(
            self.on_recurrence_present)
        self.ui.addRecurrenceRoiFixed.connect("clicked(bool)",
                                              self.on_add_roi_recurrence)

        self.ui.hideAnnotations.connect("clicked(bool)",
                                        lambda: self.on_set_annotations_visibility(False))
        self.ui.showAnnotations.connect("clicked(bool)",
                                        lambda: self.on_set_annotations_visibility(True))

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
        self.ui.linearTransformationCheckBox.setEnabled(False)

        # self.dropWidget.load_data_from_dropped_folder(
        #     "/home/koeglf/data/try_new_preprocessing/SerielleCTs_nii_forHumans/xYbaegYf_mw")
        # utils.temp_load_data(self)

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

                if self.ui_is_simple:
                    view_logic.enable_sectra_movements(self.node_diff,
                                                       self.views_third_row)

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

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        view_logic.disable_sectra_movements()
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

        self._remove_custom_observers_from_crosshair()
        self.synchronise_with_displacement_pressed = False
        self.ui.synchronise_views_with_transform.setText(
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

        if self.ui_is_simple:
            view_logic.enable_sectra_movements(self.node_fixed,
                                               self.views_first_row)
            view_logic.enable_sectra_movements(self.node_moving,
                                               self.views_second_row)
            view_logic.enable_sectra_movements(self.node_diff,
                                               self.views_third_row)

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

        if self.node_transform_nonlinear is None:
            slicer.util.errorDisplay("No nonlinear transform found")
            return False

        return True

    # CONNECTOINS

    def on_set_radiologist_id(self) -> None:
        print('setting')
        radiologist_id: str = str(
            self.ui_sub_2.radiologistIDTextEdit.toPlainText())

        if radiologist_id == "":
            slicer.util.errorDisplay("Please enter radiologist ID")
            return

        if not self.study_data_master.participants.__contains__(radiologist_id):
            slicer.util.errorDisplay(
                "Radiologist ID not found in study data master")
            return

        radiologist_name = self.study_data_master.participants[radiologist_id]["name"]

        if not utils.show_question_popup(f"Are you sure {radiologist_name} is the desired participant?"):
            return

        self.current_radiologist_id = radiologist_id

        self.ui_sub_2.start_study_button.setEnabled(True)
        self.ui_sub_2.radiologistSetCheckBox.setChecked(True)
        self.ui_sub_2.start_study_button.toolTip = f"Press to start the study with {radiologist_name}"  # nopep8

    def on_start_study(self) -> None:
        # self.on_simple_ui()
        print("Warning: reomve this default an drestore simple ui")
        self.current_radiologist_id = "rad_1"

        self.ui.start_study_by_user_button.setVisible(True)

    def on_simple_ui(self) -> None:

        self.ui_is_simple = not self.ui_is_simple

        utils.set_ui_simplification(self.ui_is_simple)

        mainWindow = slicer.util.mainWindow()

        if self.ui_is_simple:
            self.ui_sub_1.simple_ui.setText("Advanced UI")
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

            view_logic.enable_sectra_movements(self.node_fixed,
                                               self.views_first_row)
            view_logic.enable_sectra_movements(self.node_moving,
                                               self.views_second_row)
            view_logic.enable_sectra_movements(self.node_diff,
                                               self.views_third_row)
            self.hide_module_parts_for_user_study()

            mainWindow.findChild(
                qt.QWidget, "PanelDockWidget").setMaximumWidth(200)

            self.ui.start_study_by_user_button.setVisible(True)
        else:
            self.ui_sub_1.simple_ui.setText("Simple UI")
            slicer.app.setStyleSheet("""
                QWidget {
                color: black;
                }
                """)

            view_logic.disable_sectra_movements()
            self.show_module_parts_for_user_study()
            mainWindow.findChild(
                qt.QWidget, "PanelDockWidget").setMaximumWidth(1000)
            self.ui.start_study_by_user_button.setVisible(False)

    def on_user_start_study(self) -> None:
        self.ui.current_case_label.setVisible(True)
        # do this after the first case is loaded
        # self.ui.synchronise_views_general.setVisible(self.ui_is_simple)
        self.ui.study_current_task_description_label.setVisible(True)
        tasks.show_task_lymph_node(self.ui)
        self.current_task = tasks.Task.LYMPH_NODE
        self.ui.study_next_task_button.setVisible(True)

    def on_next_task(self) -> None:
        pass

    def on_study_add_point(self) -> None:
        pass

    def on_synchronise_views_wth_trasform(self) -> None:

        if not self._synchronisation_checks():
            return

        self.synchronise_with_displacement_pressed = not self.synchronise_with_displacement_pressed

        if self.synchronise_with_displacement_pressed is True:
            self._set_up_crosshair(self.synchronise_with_displacement_pressed)
            print("pressed to synchronise")
            self.ui.synchronise_views_with_transform.setText(
                "Unsynchronise views with transform (t)")
            self.ui.synchronise_views_general.setText(
                "Unsynchronise views (s)")

            self.use_transform = self.crosshair.use_transform = True
            self.crosshair.use_only_linear_transform = self.use_only_linear_transform

            self.crosshair.offset_diffs = self.current_offset = [0, 0, 0]
            self.crosshair.apply_offsets = False
            self.ui.synchronise_views_manually.setText(
                "Synchronise views manually (m)")
            self.synchronise_manually_pressed = False
        else:
            print("pressed to unsynchronise")
            self._remove_custom_observers_from_crosshair()
            self.ui.synchronise_views_with_transform.setText(
                "Synchronise views with transform (t)")
            self.ui.synchronise_views_general.setText(
                "Synchronise views (s)")
            self.ui.linearTransformationCheckBox.setEnabled(False)

    def on_synchronise_views_manually(self, views: List[List[str]] = None) -> None:

        if not self._synchronisation_checks():
            return

        self.synchronise_manually_pressed = not self.synchronise_manually_pressed

        if self.synchronise_manually_pressed is True:
            self._set_up_crosshair(self.synchronise_manually_pressed)
            print("pressed to synchronise manually")
            self.ui.synchronise_views_manually.setText(
                "Unsynchronise views manually (m)")

            self.use_transform = self.crosshair.use_transform = False
            self.ui.synchronise_views_with_transform.setText(
                "Synchronise views with transform (t)")
            self.synchronise_with_displacement_pressed = False
            self.ui.linearTransformationCheckBox.setEnabled(False)

        else:
            print("pressed to unsynchronise manually")
            self._remove_custom_observers_from_crosshair()
            self.ui.synchronise_views_manually.setText(
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

    def on_synchronise_views_general(self) -> None:

        if not self._synchronisation_checks():
            return

        if self.transformation_mode == utils.TransformationMode.NONE:
            pass
        elif self.transformation_mode == utils.TransformationMode.LINEAR:
            self.on_synchronise_views_wth_trasform()
            self.use_only_linear_transform = self.crosshair.use_only_linear_transform = True
            self.ui.linearTransformationCheckBox.setChecked(True)
        elif self.transformation_mode == utils.TransformationMode.NON_LINEAR:
            self.on_synchronise_views_wth_trasform()
            self.use_only_linear_transform = self.crosshair.use_only_linear_transform = False
            self.ui.linearTransformationCheckBox.setChecked(False)
        else:
            raise ValueError("Unknown transformation mode")

        if self.synchronise_with_displacement_pressed:
            self.ui.synchronise_views_general.setText(
                "Unsynchronise views (s)")
        else:
            self.ui.synchronise_views_general.setText("Synchronise views (s)")

    def on_linear_only(self) -> None:
        print("linear only")
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

    def on_save_annotations(self) -> None:

        if self.annotations_already_saved:
            if not utils.show_warning_popup("Annotations already saved",
                                            "Do you want to overwrite them?"):
                return

        # example name volume: XPqt2AtrAMc~2_followup_LleziZ9eAbs~201_hals_pv_08_i6_b_idose_6
        name_volume_fixed = str(self.node_fixed.GetName())
        name_volume_moving = str(self.node_moving.GetName())
        temp = name_volume_fixed.split("~")
        name_patient = temp[0]

        # check if all annotations are present
        if self.annotation_fixed_roi_lymphnode is None:
            slicer.util.errorDisplay("Please add fixed lymphnode ROI")
            return
        if self.annotation_moving_roi_lymphnode is None:
            slicer.util.errorDisplay("Please add moving lymphnode ROI")
            return

        if self.annotation_fixed_points is None or self.annotation_fixed_points.GetNumberOfControlPoints() == 0:
            slicer.util.errorDisplay("Please add fixed annotation points")
            return

        if self.annotation_moving_points is None or self.annotation_moving_points.GetNumberOfControlPoints() == 0:
            slicer.util.errorDisplay("Please add fixed annotation points")
            return

        if not utils.has_control_point_with_name(self.annotation_fixed_points, f"point_carotisgabel_{name_volume_fixed}"):
            slicer.util.errorDisplay(
                "Please add carotisgabel point for fixed volume")
            return
        if not utils.has_control_point_with_name(self.annotation_moving_points, f"point_carotisgabel_{name_volume_moving}"):
            slicer.util.errorDisplay(
                "Please add carotisgabel point for moving volume")
            return

        if not utils.has_control_point_with_name(self.annotation_fixed_points, f"point_abgangavertebralis_{name_volume_fixed}"):
            slicer.util.errorDisplay(
                "Please add abgangavertebralis point for fixed volume")
            return
        if not utils.has_control_point_with_name(self.annotation_moving_points, f"point_abgangavertebralis_{name_volume_moving}"):
            slicer.util.errorDisplay(
                "Please add abgangavertebralis point for moving volume")
            return

        if self.annotation_moving_roi_lymphnode and self.annotation_bool_lymphnode_increased is False:
            if not utils.show_warning_popup(f"Did you check for increased lymphnode size?",
                                            "(Click OK to continue saving)"):
                return

        if self.annotation_fixed_roi_recurrence is None and self.ui.recurrencePresentCheckBox.isChecked():
            utils.show_info_popup(
                f"You marked that there is a recurrence, but did not add a ROI for it.\nExiting saving.")
            return

        if self.annotation_fixed_roi_recurrence is None:
            if not utils.show_warning_popup(f"Did you check for recurrence?",
                                            "(Click OK to continue saving)"):
                return

        if not utils.show_warning_popup("Have you set the window, level and threshold?",
                                        "(Click OK to continue saving)"):
            return

        path_patient = self.annotations_save_path + name_patient
        if not os.path.exists(path_patient):
            os.makedirs(path_patient)

        slicer.util.saveNode(self.annotation_fixed_roi_lymphnode, path_patient +
                             f"/{self.annotation_fixed_roi_lymphnode.GetName()}.mrk.json")
        slicer.util.saveNode(self.annotation_moving_roi_lymphnode, path_patient +
                             f"/{self.annotation_moving_roi_lymphnode.GetName()}.mrk.json")
        with open(path_patient + f"/lymphnode_increased.txt", "w") as f:
            f.write(str(self.annotation_bool_lymphnode_increased))

        slicer.util.saveNode(self.annotation_fixed_points, path_patient +
                             f"/{self.annotation_fixed_points.GetName()}.mrk.json")
        slicer.util.saveNode(self.annotation_moving_points, path_patient +
                             f"/{self.annotation_fixed_points.GetName()}.mrk.json")

        with open(path_patient + f"/recurrence_exists.txt", "w") as f:
            f.write(str(self.annotation_fixed_roi_recurrence is not None))

        if self.annotation_fixed_roi_recurrence is not None:
            slicer.util.saveNode(self.annotation_fixed_roi_recurrence, path_patient +
                                 f"/{self.annotation_fixed_roi_recurrence.GetName()}.mrk.json")

        disp_node_fixed = self.node_fixed.GetDisplayNode()
        w_l_t_fixed = {'window': disp_node_fixed.GetWindow(),
                       'level': disp_node_fixed.GetLevel(),
                       'threshold': [disp_node_fixed.GetLowerThreshold(), disp_node_fixed.GetUpperThreshold()]}
        with open(path_patient + f"/window_level_threshold_{self.node_fixed.GetName()}.json", "w") as f:
            json.dump(w_l_t_fixed, f)

        disp_node_moving = self.node_moving.GetDisplayNode()
        w_l_t_moving = {'window': disp_node_moving.GetWindow(),
                        'level': disp_node_moving.GetLevel(),
                        'threshold': [disp_node_moving.GetLowerThreshold(), disp_node_moving.GetUpperThreshold()]}
        with open(path_patient + f"/window_level_threshold_{self.node_moving.GetName()}.json", "w") as f:
            json.dump(w_l_t_moving, f)

        self.annotations_already_saved = True

        # show message with Ok only that saving is done
        utils.show_info_popup("Annotations saved")

    def on_clear_annotations(self) -> None:
        if not self.annotations_already_saved:
            if not utils.show_warning_popup("Annotations not saved yet.",
                                            "Do you want to clear them?"):
                return
        else:
            if not utils.show_warning_popup("Annotations already saved.",
                                            "Do you want to clear them?"):
                return

        if self.annotation_fixed_roi_lymphnode is not None:
            slicer.mrmlScene.RemoveNode(self.annotation_fixed_roi_lymphnode)
            self.annotation_fixed_roi_lymphnode = None
            self.ui.lymphnodeRoiFixedCheckbox.setChecked(False)

        if self.annotation_moving_roi_lymphnode is not None:
            slicer.mrmlScene.RemoveNode(self.annotation_moving_roi_lymphnode)
            self.annotation_moving_roi_lymphnode = None
            self.ui.increasedLymphnodeCheckBox.setEnabled(False)
            self.ui.increasedLymphnodeCheckBox.setChecked(False)
            self.ui.lymphnodeRoiMovingCheckbox.setChecked(False)

        if self.annotation_fixed_points is not None:
            slicer.mrmlScene.RemoveNode(self.annotation_fixed_points)
            self.annotation_fixed_points = None
            self.ui.carotisgabelPointFixedCheckbox.setChecked(False)
            self.ui.abgangavertebralisPointFixedCheckbox.setChecked(False)

        if self.annotation_moving_points is not None:
            slicer.mrmlScene.RemoveNode(self.annotation_moving_points)
            self.annotation_moving_points = None
            self.ui.carotisgabelPointMovingCheckbox.setChecked(False)
            self.ui.abgangavertebralisPointMovingCheckbox.setChecked(False)

        if self.annotation_fixed_roi_recurrence is not None:
            slicer.mrmlScene.RemoveNode(self.annotation_fixed_roi_recurrence)
            self.annotation_fixed_roi_recurrence = None
            self.ui.recurrencePresentCheckBox.setChecked(False)
            self.ui.recurrenceRoiFixedCheckbox.setChecked(False)
            self.ui.addRecurrenceRoiFixed.setEnabled(False)

        self.annotations_already_saved = False

    def on_add_roi_lymphnode(self, image: Literal['fixed', 'moving']) -> None:
        if image not in ['fixed', 'moving']:
            raise ValueError("image must be either 'fixed' or 'moving'")

        if image == 'fixed':
            volume_name = self.node_fixed.GetName()
            views = self.views_first_row
            node_annotation = self.annotation_fixed_roi_lymphnode
        else:
            volume_name = self.node_moving.GetName()
            views = self.views_second_row
            node_annotation = self.annotation_moving_roi_lymphnode

        name = str("roi_lymphnode_" + volume_name)

        if node_annotation is not None:
            if utils.show_warning_popup(f"ROI {name.capitalize()} already exists",
                                        "Do you want to overwrite it?"):
                slicer.mrmlScene.RemoveNode(
                    node_annotation)
                if image == 'moving':
                    self.ui.increasedLymphnodeCheckBox.setEnabled(False)
            else:
                return

        new_annotation = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLMarkupsROINode", name)

        view_logic.configure_roi(new_annotation, views)

        if image == 'fixed':
            self.annotation_fixed_roi_lymphnode = new_annotation
            self.ui.lymphnodeRoiFixedCheckbox.setChecked(True)
        else:
            self.annotation_moving_roi_lymphnode = new_annotation
            self.ui.increasedLymphnodeCheckBox.setEnabled(True)
            self.ui.lymphnodeRoiMovingCheckbox.setChecked(True)

    def on_lymphnode_increased(self) -> None:
        self.annotation_bool_lymphnode_increased = not self.annotation_bool_lymphnode_increased

    def _add_point_list(self) -> None:
        if self.annotation_fixed_points is None:

            self.annotation_fixed_points = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLMarkupsFiducialNode", f"points_{self.node_fixed.GetName()}")

            self.annotation_fixed_points.GetDisplayNode().SetGlyphScale(1)
            self.annotation_fixed_points.GetDisplayNode().SetTextScale(2)

        if self.annotation_moving_points is None:
            self.annotation_moving_points = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLMarkupsFiducialNode", f"points_{self.node_moving.GetName()}")

            self.annotation_moving_points.GetDisplayNode().SetGlyphScale(1)
            self.annotation_moving_points.GetDisplayNode().SetTextScale(2)

    def on_add_annotation_point_fixed(
            self,
            point_name: Literal['carotisgabel', 'abgangavertebralis']
    ) -> None:

        self._add_point_list()

        volume_name = self.node_fixed.GetName()

        name = "point_" + point_name + '_' + volume_name

        if utils.has_control_point_with_name(self.annotation_fixed_points, name):
            if utils.show_warning_popup(f"Point {point_name.capitalize()} already exists",
                                        "Do you want to overwrite it?"):
                utils.remove_control_point_by_name(self.annotation_fixed_points,
                                                   name)
            else:
                return

        pos = [view_logic.get_view_offset(view) for view in self.views_first_row]  # nopep8

        self.annotation_fixed_points.AddControlPointWorld([-pos[2], pos[1], pos[0]],
                                                          name)

        if point_name == 'carotisgabel':
            self.ui.carotisgabelPointFixedCheckbox.setChecked(True)
        else:
            self.ui.abgangavertebralisPointFixedCheckbox.setChecked(True)

        utils.show_node_only_in_views(self.annotation_fixed_points,
                                      self.views_first_row)

    def on_add_annotation_point_moving(
            self,
            point_name: Literal['carotisgabel', 'abgangavertebralis']
    ) -> None:

        self._add_point_list()

        volume_name = self.node_moving.GetName()

        name = "point_" + point_name + '_' + volume_name

        if utils.has_control_point_with_name(self.annotation_moving_points, name):
            if utils.show_warning_popup(f"Point {point_name.capitalize()} already exists",
                                        "Do you want to overwrite it?"):
                utils.remove_control_point_by_name(self.annotation_moving_points,
                                                   name)
            else:
                return

        pos = [view_logic.get_view_offset(view) for view in self.views_second_row]  # nopep8

        self.annotation_moving_points.AddControlPointWorld([-pos[2], pos[1], pos[0]],
                                                           name)

        if point_name == 'carotisgabel':
            self.ui.carotisgabelPointMovingCheckbox.setChecked(True)
        else:
            self.ui.abgangavertebralisPointMovingCheckbox.setChecked(True)

        utils.show_node_only_in_views(self.annotation_moving_points,
                                      self.views_second_row)

    def on_recurrence_present(self) -> None:
        if self.ui.recurrencePresentCheckBox.isChecked():
            self.ui.addRecurrenceRoiFixed.setEnabled(True)
            return

        # trying to uncheck - only allow with warning
        if self.ui.recurrencePresentCheckBox.isChecked() is False:
            if self.annotation_fixed_roi_recurrence is None:
                self.ui.addRecurrenceRoiFixed.setEnabled(False)
            else:
                if utils.show_warning_popup(f"You alreday created a ROI for the recurrence.",
                                            "Do you want to remove it?"):
                    slicer.mrmlScene.RemoveNode(
                        self.annotation_fixed_roi_recurrence)
                    self.annotation_fixed_roi_recurrence = None
                    self.ui.addRecurrenceRoiFixed.setEnabled(False)
                else:
                    self.ui.recurrencePresentCheckBox.setChecked(True)
                    self.ui.addRecurrenceRoiFixed.setEnabled(True)

    def on_add_roi_recurrence(self) -> None:

        name = str("roi_recurrence_" + self.node_moving.GetName())

        if self.annotation_fixed_roi_recurrence is not None:
            if utils.show_warning_popup(f"ROI {name.capitalize()} already exists",
                                        "Do you want to overwrite it?"):
                slicer.mrmlScene.RemoveNode(
                    self.annotation_fixed_roi_recurrence)
            else:
                return

        self.annotation_fixed_roi_recurrence = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLMarkupsROINode", name)

        view_logic.configure_roi(
            self.annotation_fixed_roi_recurrence, self.views_first_row)

        self.ui.recurrenceRoiFixedCheckbox.setChecked(True)

    def on_set_annotations_visibility(self, visibility: bool) -> None:

        for annotation in [self.annotation_fixed_roi_lymphnode,
                           self.annotation_moving_roi_lymphnode,
                           self.annotation_fixed_points,
                           self.annotation_moving_points,
                           self.annotation_fixed_roi_recurrence]:
            if annotation is not None:
                annotation.GetDisplayNode().SetVisibility(visibility)

    def hide_module_parts_for_user_study(self) -> None:
        self.ui.studyCollapsibleButton.setHidden(True)
        self.ui.inputsCollapsibleButton.setHidden(True)
        self.ui.controlsCollapsibleButton.setHidden(True)
        # self.ui.label_4.setVisible(False)
        # self.ui.button_2x3.setVisible(False)
        # self.ui.button_3x3.setVisible(False)
        # self.ui.synchronise_views_with_transform.setVisible(False)
        # self.ui.linearTransformationCheckBox.setVisible(False)
        # self.ui.remove_all_data.setVisible(False)
        self.ui.annotationsCollapsibleButton.setHidden(True)
        self.loadingCollapsible.setHidden(True)

        self.ui.current_case_label.setVisible(False)

    def show_module_parts_for_user_study(self) -> None:
        self.ui.studyCollapsibleButton.setHidden(False)
        self.ui.inputsCollapsibleButton.setHidden(False)
        self.ui.controlsCollapsibleButton.setHidden(False)
        # self.ui.label_4.setVisible(True)
        # self.ui.button_2x3.setVisible(True)
        # self.ui.button_3x3.setVisible(True)
        # self.ui.synchronise_views_with_transform.setVisible(True)
        # self.ui.linearTransformationCheckBox.setVisible(True)
        # self.ui.remove_all_data.setVisible(True)
        self.ui.annotationsCollapsibleButton.setHidden(False)
        self.loadingCollapsible.setHidden(False)

    def update_cursor_view(self) -> None:

        def wrapper(self, callee, event):  # pylint: disable=unused-argument
            position = self.node_crosshair.GetCursorPositionXYZ([0]*3)
            if position is not None:
                self.crosshair.cursor_view = position.GetName()

        observer_tag = self.node_crosshair.AddObserver(slicer.vtkMRMLCrosshairNode.CursorPositionModifiedEvent,
                                                       functools.partial(wrapper, self))
        self.crosshair_custom_observer_tags.append(observer_tag)

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

        self.ui.linearTransformationCheckBox.setEnabled(True)

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

    def _remove_custom_observers_from_crosshair(self) -> None:
        for observer_tag in self.crosshair_custom_observer_tags:
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
