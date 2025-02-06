import os

from typing import Optional, TYPE_CHECKING

import slicer
import qt

from registrationViewerLib import study_loading, tasks, utils, view_logic

if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget


# CONNECTIONS
def on_set_radiologist_id(self: "registrationViewerWidget") -> None:

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

    self.current_patient_list = self.study_data_master.patient_list(self.current_radiologist_id)  # nopep8
    self.current_patient_idx = 0


def on_simple_ui(self: "registrationViewerWidget") -> None:

    self.ui_is_simple = not self.ui_is_simple

    utils.set_ui_simplification(self.ui_is_simple)

    mainWindow = slicer.util.mainWindow()

    if self.ui_is_simple:
        self.ui_sub_1.simple_ui_button.setText("Advanced UI")
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
        hide_module_parts_for_user_study(self)

        mainWindow.findChild(
            qt.QWidget, "PanelDockWidget").setMaximumWidth(1000)

        self.ui_sub_6.start_study_by_user_button.setVisible(True)
    else:
        self.ui_sub_1.simple_ui_button.setText("Simple UI")
        slicer.app.setStyleSheet("""
            QWidget {
            color: black;
            }
            """)

        view_logic.disable_sectra_movements()
        show_module_parts_for_user_study(self)
        mainWindow.findChild(
            qt.QWidget, "PanelDockWidget").setMaximumWidth(1000)
        self.ui_sub_6.start_study_by_user_button.setVisible(False)


def on_start_study(self: "registrationViewerWidget") -> None:

    self.current_radiologist_id = 'rad_1'
    on_simple_ui(self)
    self.ui_sub_6.start_study_by_user_button.setVisible(True)


def on_user_start_study(self: "registrationViewerWidget") -> None:
    """
    this should:
    1. load data (in such a way that it is not displayed)
    1. show task description
    1. when data is loaded a button to start task should be displayed
    1. when task is started data should be shown

    """
    self.study_progress_bar_patients = utils.show_progressbar(
        ui=self.ui_sub_6,
        idx=1,
        initial=1,
        maximum=len(self.study_data_master.patient_list(
            self.current_radiologist_id))
    )
    self.study_progress_bar_tasks = utils.show_progressbar(
        ui=self.ui_sub_6,
        idx=2,
        initial=1,
        maximum=4
    )

    self.study_progress_bar_patients.setVisible(False)
    self.ui_sub_6.progress_label_1.setVisible(False)
    self.study_progress_bar_tasks.setVisible(False)
    self.ui_sub_6.progress_label_2.setVisible(False)

    self.ui_sub_6.start_study_by_user_button.setVisible(False)

    self.current_task_idx = -1
    self.current_patient_idx = -1

    self.on_study_next_patient()


def on_study_next_patient(self: "registrationViewerWidget") -> None:

    save_annotations(self)
    clear_annotations(self)
    self.on_remove_all_data()

    self.current_patient_idx += 1
    self.current_task_idx = -1

    self.ui_sub_6.study_current_task_description_label.setVisible(False)
    self.ui_sub_6.synchronise_views_general.setVisible(False)
    self.ui_sub_6.study_add_point_button.setVisible(False)
    self.ui_sub_6.study_center_on_point_button.setVisible(False)
    self.ui_sub_6.study_dropdown.setVisible(False)
    self.ui_sub_6.study_checkbox.setVisible(False)
    self.ui_sub_6.study_next_task_button.setVisible(False)
    self.ui_sub_6.study_next_patient_button.setVisible(False)

    study_loading.load_study_volumes(self, self.current_patient_path)

    self.study_progress_bar_patients.setValue(self.current_patient_idx + 1)

    self.study_progress_bar_patients.setVisible(True)
    self.ui_sub_6.progress_label_1.setVisible(True)
    self.study_progress_bar_tasks.setVisible(True)
    self.ui_sub_6.progress_label_2.setVisible(True)

    self.ui_sub_6.study_current_task_description_label.setVisible(True)
    self.ui_sub_6.synchronise_views_general.setVisible(True)
    self.ui_sub_6.study_add_point_button.setVisible(True)
    self.ui_sub_6.study_center_on_point_button.setVisible(True)
    self.ui_sub_6.study_dropdown.setVisible(True)
    self.ui_sub_6.study_next_task_button.setVisible(True)

    # self.ui_sub_6.current_case_label.setText(f"{self.current_patient_name} {self.current_patient_transform_type}")  # nopep8

    if self.current_patient_transform_type == utils.TransformType.NONE:
        self.unsynchronise_views()
        self.ui_sub_6.synchronise_views_general.setVisible(False)
        pass
    elif self.current_patient_transform_type == utils.TransformType.LINEAR:
        self.use_only_linear_transform = True
        if self.crosshair:
            self.crosshair.use_only_linear_transform = True
        self.study_current_transform_type = utils.TransformType.LINEAR
        self.ui_sub_6.synchronise_views_general.setVisible(True)
    elif self.current_patient_transform_type == utils.TransformType.NONLINEAR:
        self.use_only_linear_transform = False
        if self.crosshair:
            self.crosshair.use_only_linear_transform = False
        self.study_current_transform_type = utils.TransformType.NONLINEAR
        self.ui_sub_6.synchronise_views_general.setVisible(True)

    else:
        print(f"{self.current_patient_name=}")
        raise ValueError(f"Unknown transformation type {self.current_patient_name}")  # nopep8

    on_next_task(self)


def on_next_task(self: "registrationViewerWidget") -> None:
    self.ui_sub_6.study_next_task_button.setEnabled(False)
    self.ui_sub_6.study_next_task_button.toolTip = "Please add annotation point first"  # nopep8

    self.ui_sub_6.study_center_on_point_button.setEnabled(False)

    save_annotations(self, specific_task=self.current_task)

    self.current_task_idx += 1
    self.study_progress_bar_tasks.setValue(self.current_task_idx + 1)

    if self.current_task_idx == 0:
        tasks.show_task_lymphnode(self.ui_sub_6, self.study_node_points)
    elif self.current_task_idx == 1:
        tasks.show_task_carotisgabel(self.ui_sub_6, self.study_node_points)
    elif self.current_task_idx == 2:
        tasks.show_task_avertebralis(self.ui_sub_6, self.study_node_points)
    elif self.current_task_idx == 3:
        tasks.show_task_recurrence(self.ui_sub_6, self.study_node_points)
        self.ui_sub_6.study_next_patient_button.setVisible(True)
        self.ui_sub_6.study_next_patient_button.setEnabled(True)
        self.ui_sub_6.study_next_patient_button.toolTip = ""  # nopep8
        self.ui_sub_6.study_next_task_button.setVisible(False)


def on_add_annotation_point(self: "registrationViewerWidget") -> None:

    volume_name = self.node_fixed.GetName()

    if self.study_node_points[self.current_task] is not None:
        if utils.show_warning_popup(f"Point {self.current_task.value} already exists",
                                    "Do you want to overwrite it?"):
            slicer.mrmlScene.RemoveNode(
                self.study_node_points[self.current_task])
            self.study_node_points[self.current_task] = None
            self.ui_sub_6.study_center_on_point_button.setEnabled(False)
        else:
            return

    if self.study_node_points[self.current_task] is None:
        self.study_node_points[self.current_task] = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLMarkupsFiducialNode", f"{self.current_task.value}_{self.current_radiologist_id}_{volume_name}")
        self.study_node_points[self.current_task].GetDisplayNode(
        ).SetGlyphScale(1)
        self.study_node_points[self.current_task].GetDisplayNode(
        ).SetTextScale(2)

    pos = [view_logic.get_view_offset(view) for view in self.views_first_row]  # nopep8

    self.study_node_points[self.current_task].AddControlPointWorld([-pos[2], pos[1], pos[0]],
                                                                   'p')

    utils.show_node_only_in_views(self.study_node_points[self.current_task],
                                  self.views_first_row)

    if self.current_task_idx == 3:
        self.ui_sub_6.study_next_patient_button.setEnabled(True)
        self.ui_sub_6.study_next_patient_button.toolTip = ""  # nopep8

        # Temporarily block signals wo se don't trigger the callbacks
        self.ui_sub_6.study_checkbox.blockSignals(True)
        self.ui_sub_6.study_checkbox.setChecked(True)
        self.ui_sub_6.study_checkbox.blockSignals(False)

        self.study_recurrence_present = True
    else:
        self.ui_sub_6.study_next_task_button.setEnabled(True)
        self.ui_sub_6.study_next_task_button.toolTip = ""  # nopep8

    self.ui_sub_6.study_center_on_point_button.setEnabled(True)


def on_checkbox(self: "registrationViewerWidget") -> None:
    if self.current_task != tasks.Task.RECURRENCE:
        return

    self.study_recurrence_present = not self.study_recurrence_present

    point = self.study_node_points[tasks.Task.RECURRENCE]

    if self.study_recurrence_present:
        if point is None:
            self.ui_sub_6.study_next_patient_button.setEnabled(False)
            self.ui_sub_6.study_next_patient_button.toolTip = "Please add annotation point first"  # nopep8

        else:
            self.ui_sub_6.study_next_patient_button.setEnabled(True)
            self.ui_sub_6.study_next_patient_button.toolTip = ""  # nopep8

    else:
        if point is not None:
            if utils.show_warning_popup(f"Do you want to remove the point you already set for the recurrence?",
                                        ""):
                slicer.mrmlScene.RemoveNode(point)
                self.study_node_points[tasks.Task.RECURRENCE] = None
                self.ui_sub_6.study_checkbox.blockSignals(True)
                self.ui_sub_6.study_checkbox.setChecked(False)
                self.ui_sub_6.study_checkbox.blockSignals(False)
                self.study_recurrence_present = False
                self.ui_sub_6.study_center_on_point_button.setEnabled(
                    False)
            else:
                self.ui_sub_6.study_checkbox.blockSignals(True)
                self.ui_sub_6.study_checkbox.setChecked(True)
                self.ui_sub_6.study_checkbox.blockSignals(False)
                self.study_recurrence_present = True

        self.ui_sub_6.study_next_patient_button.setEnabled(True)
        self.ui_sub_6.study_next_patient_button.toolTip = ""  # nopep8


def on_selection_changed(self: "registrationViewerWidget") -> None:
    if self.current_task == tasks.Task.LYMPH_NODE:

        if self.ui_sub_6.study_dropdown.currentText == "Size increased":
            self.study_lymphnode_size = "Size increased"
        elif self.ui_sub_6.study_dropdown.currentText == "Size decreased":
            self.study_lymphnode_size = "Size decreased"
        elif self.ui_sub_6.study_dropdown.currentText == "Size same":
            self.study_lymphnode_size = "Size same"
        else:
            raise ValueError("Unknown lymphnode size")


def save_annotations(self: "registrationViewerWidget",
                     specific_task: Optional[tasks.Task] = None) -> None:

    if self.current_task_idx < 0:
        return

    path_patient = f"{self.study_data_master.path_study_output}{self.current_radiologist_id}/{self.current_patient_name}"  # nopep8
    if not os.path.exists(path_patient):
        os.makedirs(path_patient)

    if specific_task is None or specific_task == tasks.Task.LYMPH_NODE:
        tasks.save_lymphnode(path_patient,
                             self.study_node_points,
                             self.study_lymphnode_size)
    if specific_task is None or specific_task == tasks.Task.CAROTIS_GABEL:
        tasks.save_carotisgabel(path_patient,
                                self.study_node_points)
    if specific_task is None or specific_task == tasks.Task.A_VERTEBRALIS:
        tasks.save_avertebralis(path_patient,
                                self.study_node_points)
    if specific_task is None or specific_task == tasks.Task.RECURRENCE:
        tasks.save_recurrence(path_patient,
                              self.study_node_points,
                              self.study_recurrence_present)


def clear_annotations(self: "registrationViewerWidget") -> None:
    if self.current_task_idx <= 0:
        return

    for task, point in self.study_node_points.items():
        if point is not None:
            slicer.mrmlScene.RemoveNode(point)
            self.study_node_points[task] = None

    self.study_lymphnode_size = ""
    self.study_recurrence_present = False

    self.ui_sub_6.study_checkbox.blockSignals(True)
    self.ui_sub_6.study_checkbox.setChecked(False)
    self.ui_sub_6.study_checkbox.blockSignals(False)
    self.ui_sub_6.study_dropdown.setCurrentText('Size same')


def hide_module_parts_for_user_study(self: "registrationViewerWidget") -> None:
    self.ui_sub_1.simple_ui_button.setHidden(False)
    self.ui_sub_2.studyCollapsibleButton.setHidden(True)
    self.ui_sub_3.inputsCollapsibleButton.setHidden(True)
    self.ui_sub_4.controlsCollapsibleButton.setHidden(True)
    self.ui_sub_5.annotationsCollapsibleButton.setHidden(True)
    self.loadingCollapsible.setHidden(True)

    self.ui_sub_6.current_case_label.setVisible(False)
    self.ui_sub_6.Form_user_study.setHidden(False)
    self.ui_sub_6.study_center_on_point_button.setVisible(False)


def show_module_parts_for_user_study(self: "registrationViewerWidget") -> None:
    self.ui_sub_2.studyCollapsibleButton.setHidden(False)
    self.ui_sub_3.inputsCollapsibleButton.setHidden(False)
    self.ui_sub_4.controlsCollapsibleButton.setHidden(False)
    self.ui_sub_5.annotationsCollapsibleButton.setHidden(False)
    self.loadingCollapsible.setHidden(False)

    self.ui_sub_6.Form_user_study.setHidden(True)
