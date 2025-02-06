import os

from typing import Optional, TYPE_CHECKING

import slicer
import qt

from registrationViewerLib import utils, view_logic, tasks

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
        self.hide_module_parts_for_user_study()

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
        self.show_module_parts_for_user_study()
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
