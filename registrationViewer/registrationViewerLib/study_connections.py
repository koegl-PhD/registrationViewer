import logging

from typing import Optional, TYPE_CHECKING

import slicer
import qt

from registrationViewerLib import tasks_ui_logic, tasks, utils, view_logic, study
from registrationViewerLib.custom_logging import configure_logger, set_log_prefix, log, LogType

if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget


def set_connections(self: "registrationViewerWidget") -> None:
    self.ui_sub_2.set_radiologist_id_button.connect("clicked(bool)",
                                                    lambda: btn_call_on_set_radiologist_id(self))
    self.ui_sub_2.start_study_button.connect("clicked(bool)",
                                             lambda: btn_call_on_start_study(self))

    def _on_text_changed():
        self.ui_sub_2.start_study_button.setEnabled(False)
        self.ui_sub_2.radiologistSetCheckBox.setChecked(False)
        self.ui_sub_2.start_study_button.toolTip = "Please set radiologist ID first"

    self.ui_sub_2.radiologistIDTextEdit.textChanged.connect(
        _on_text_changed)

    self.ui_sub_6.synchronise_views_general.connect("clicked(bool)",
                                                    lambda: btn_call_on_synchronise_views_general(self))

    self.ui_sub_6.start_study_by_user_button.connect("clicked(bool)",
                                                     lambda: btn_call_on_user_start_study(self))
    self.ui_sub_6.study_add_point_button.connect("clicked(bool)",
                                                 lambda: btn_call_on_add_annotation_point(self))
    self.ui_sub_6.study_center_on_point_button.connect("clicked(bool)",
                                                       lambda: btn_call_on_center_on_point(self))
    self.ui_sub_6.study_next_task_button.connect("clicked(bool)",
                                                 lambda: btn_call_on_next_task(self))
    self.ui_sub_6.study_next_patient_button.connect("clicked(bool)",
                                                    lambda: btn_call_on_study_next_patient(self))
    self.ui_sub_6.study_checkbox.toggled.connect(
        lambda: btn_call_on_checkbox(self))
    self.ui_sub_6.study_dropdown.currentIndexChanged.connect(
        lambda: btn_call_on_selection_changed(self))


def btn_call_on_synchronise_views_general(self: "registrationViewerWidget") -> None:

    if self.synchronise_with_displacement_pressed:
        text = "User unsynchronised views"
    else:
        text = "User synchronised views"

    log(logging.INFO, LogType.BUTTON, text)

    on_synchronise_views_general(self)


def key_call_on_synchronise_views_general(self: "registrationViewerWidget") -> None:

    if self.synchronise_with_displacement_pressed:
        text = "User unsynchronised views"
    else:
        text = "User synchronised views"

    log(logging.INFO, LogType.KEYBOARD, text)

    on_synchronise_views_general(self)


def on_synchronise_views_general(self: "registrationViewerWidget") -> None:

    if not self._synchronisation_checks():
        return

    if self.study_current_transform_type == utils.TransformType.NONE:
        pass
    elif self.study_current_transform_type == utils.TransformType.LINEAR:
        print(f"linear")
        self.on_synchronise_views_wth_trasform()
        self.use_only_linear_transform = self.crosshair.use_only_linear_transform = True
        self.ui_sub_4.linearTransformationCheckBox.setChecked(True)
    elif self.study_current_transform_type == utils.TransformType.NONLINEAR:
        print(f"nonlinear")
        self.on_synchronise_views_wth_trasform()
        self.use_only_linear_transform = self.crosshair.use_only_linear_transform = False
        self.ui_sub_4.linearTransformationCheckBox.setChecked(False)
    else:
        raise ValueError("Unknown transformation mode")

    if self.synchronise_with_displacement_pressed:
        self.ui_sub_6.synchronise_views_general.setText(
            "Unsynchronise views (s)")
    else:
        self.ui_sub_6.synchronise_views_general.setText(
            "Synchronise views (s)")

    self.ui_sub_4.synchronise_views_with_transform.setVisible(False)
    self.ui_sub_4.synchronise_views_manually.setVisible(False)


def btn_call_on_set_radiologist_id(self: "registrationViewerWidget") -> None:
    on_set_radiologist_id(self)


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

    configure_logger(f"{self.study_data_master.path_study_output}{self.current_radiologist_id}/{self.current_radiologist_id}.log")  # nopep8


def on_simple_ui(self: "registrationViewerWidget", value: Optional[bool] = None) -> None:

    self.ui_is_simple = not self.ui_is_simple

    if value is not None:
        self.ui_is_simple = value

    # utils.set_ui_simplification(self.ui_is_simple)

    mainWindow = slicer.util.mainWindow()

    if self.ui_is_simple:
        self.ui_sub_1.simple_ui_button.setText("Advanced UI")
        # slicer.app.setStyleSheet("""
        #     QWidget {
        #         background-color: #060f21;
        #         color: white;
        #     }
        #     QMainWindow {
        #         background-color: #060f21;
        #     }
        #     qSlicerLayoutManager {
        #         background-color: #060f21;
        #     }
        #     """)

        study.hide_module_parts_for_user_study(self)

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
        study.show_module_parts_for_user_study(self)
        mainWindow.findChild(
            qt.QWidget, "PanelDockWidget").setMaximumWidth(1000)
        self.ui_sub_6.start_study_by_user_button.setVisible(False)


def btn_call_on_start_study(self: "registrationViewerWidget") -> None:
    on_start_study(self)


def on_start_study(self: "registrationViewerWidget") -> None:
    on_simple_ui(self, True)
    self.ui_sub_6.start_study_by_user_button.setVisible(True)


def btn_call_on_user_start_study(self: "registrationViewerWidget") -> None:
    set_log_prefix(f"{self.current_radiologist_id}")

    log(logging.INFO, LogType.BUTTON, "User started study")

    on_user_start_study(self)


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
        maximum=len(tasks.TASK_ORDER)
    )

    self.study_progress_bar_patients.setVisible(False)
    self.ui_sub_6.progress_label_1.setVisible(False)
    self.study_progress_bar_tasks.setVisible(False)
    self.ui_sub_6.progress_label_2.setVisible(False)

    self.ui_sub_6.start_study_by_user_button.setVisible(False)

    self.current_task_idx = -1
    self.current_patient_idx = -1

    on_study_next_patient(self)


def btn_call_on_center_on_point(self: "registrationViewerWidget") -> None:
    log(logging.INFO, LogType.BUTTON, "User centered on point")

    utils.center_on_point(
        self.study_node_points[self.current_task], self.group_first_row)


def btn_call_on_study_next_patient(self: "registrationViewerWidget") -> None:
    on_study_next_patient(self)


def on_study_next_patient(self: "registrationViewerWidget") -> None:

    if self.current_patient_idx >= 0:
        study.save_annotations(self,
                               serialise_to_log=True,
                               final_save=True)

    study.clear_annotations(self)

    self.current_patient_idx += 1
    self.current_task_idx = -1

    set_log_prefix(
        f"{self.current_radiologist_id} ~ {self.current_patient_name}")
    log(logging.INFO, LogType.BUTTON, "User started patient")

    self.study_progress_bar_patients.setValue(self.current_patient_idx + 1)
    self.study_progress_bar_patients.setVisible(True)
    self.ui_sub_6.progress_label_1.setVisible(True)
    self.study_progress_bar_tasks.setVisible(True)
    self.ui_sub_6.progress_label_2.setVisible(True)
    self.study_progress_bar_tasks.setValue(1)

    self.on_remove_all_data()

    if self.current_patient_idx >= len(self.current_patient_list):
        log(logging.INFO, LogType.BUTTON, "User finished study")
        utils.show_info_popup("Study finished", "You have finished the study")
        return

    self.ui_sub_6.study_current_task_description_label.setVisible(False)
    self.ui_sub_6.synchronise_views_general.setVisible(False)
    self.ui_sub_6.study_add_point_button.setVisible(False)
    self.ui_sub_6.study_center_on_point_button.setVisible(False)
    self.ui_sub_6.study_dropdown.setVisible(False)
    self.ui_sub_6.study_checkbox.setVisible(False)
    self.ui_sub_6.study_next_task_button.setVisible(False)
    self.ui_sub_6.study_next_patient_button.setVisible(False)

    study.load_study_volumes(self, self.current_patient_path)
    study.load_ground_truth_annotations(self,
                                        self.current_patient_name,
                                        self.node_moving.GetName())

    log(logging.INFO, LogType.OTHER, "Data loaded")

    self.ui_sub_6.study_current_task_description_label.setVisible(True)
    self.ui_sub_6.synchronise_views_general.setVisible(True)
    self.ui_sub_6.study_add_point_button.setVisible(True)
    self.ui_sub_6.study_center_on_point_button.setVisible(True)
    self.ui_sub_6.study_dropdown.setVisible(True)
    self.ui_sub_6.study_next_task_button.setVisible(True)

    self.ui_sub_6.current_case_label.setText(f"{self.current_patient_name} {self.current_patient_transform_type}")  # nopep8

    if self.current_patient_transform_type == utils.TransformType.NONE:
        self.unsynchronise_views()
        self.ui_sub_6.synchronise_views_general.setVisible(False)
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


def btn_call_on_next_task(self: "registrationViewerWidget") -> None:
    on_next_task(self)


def on_next_task(self: "registrationViewerWidget") -> None:

    self.ui_sub_6.study_next_task_button.setEnabled(False)
    self.ui_sub_6.study_next_task_button.toolTip = "Please add annotation point first"  # nopep8

    self.ui_sub_6.study_center_on_point_button.setEnabled(False)

    if self.current_task_idx >= 0:
        study.save_annotations(self,
                               specific_task=self.current_task,
                               serialise_to_log=True)

    self.current_task_idx += 1
    self.study_progress_bar_tasks.setValue(self.current_task_idx + 1)

    set_log_prefix(f"{self.current_radiologist_id} ~ {self.current_patient_name} ~ {self.current_task.value}")  # nopep8
    log(logging.INFO, LogType.BUTTON, "User started task")

    tasks_ui_logic.show_task(
        self.ui_sub_6,
        self.current_task,
        self.study_node_points,
        self.study_node_groundtruth_points,
        self.group_second_row
    )

    if self.current_task == tasks.Task.RECURRENCE:
        self.ui_sub_6.study_next_patient_button.setVisible(True)
        self.ui_sub_6.study_next_patient_button.setEnabled(True)
        self.ui_sub_6.study_next_patient_button.toolTip = ""  # nopep8
        self.ui_sub_6.study_next_task_button.setVisible(False)
    else:
        self.ui_sub_6.study_next_patient_button.setVisible(False)
        self.ui_sub_6.study_next_patient_button.setEnabled(False)
        self.ui_sub_6.study_next_patient_button.toolTip = ""  # nopep8
        self.ui_sub_6.study_next_task_button.setVisible(True)


def btn_call_on_add_annotation_point(self: "registrationViewerWidget") -> None:

    log(logging.INFO, LogType.BUTTON, "User clicked on add point")
    on_add_annotation_point(self)


def on_add_annotation_point(self: "registrationViewerWidget") -> None:

    volume_name = self.node_fixed.GetName()

    overwrote = False

    if self.study_node_points[self.current_task] is not None:
        if utils.show_warning_popup(f"Point {self.current_task.value} already exists",
                                    "Do you want to overwrite it?"):
            slicer.mrmlScene.RemoveNode(
                self.study_node_points[self.current_task])
            self.study_node_points[self.current_task] = None
            self.ui_sub_6.study_center_on_point_button.setEnabled(False)

            log(logging.INFO, LogType.BUTTON, "User overwrote annotation point")
            overwrote = True

        else:
            log(logging.INFO, LogType.BUTTON,
                "User cancelled overwriting annotation point")
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

    if self.current_task == tasks.Task.RECURRENCE:
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

    if not overwrote:
        log(logging.INFO, LogType.BUTTON, "User added annotation point")


def btn_call_on_checkbox(self: "registrationViewerWidget") -> None:
    log(logging.INFO, LogType.MOUSE, "User clicked on checkbox")
    on_checkbox(self)


def on_checkbox(self: "registrationViewerWidget") -> None:
    overwrote = False

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

        log(logging.INFO, LogType.BUTTON, "User checked checkbox")

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

                log(logging.INFO, LogType.BUTTON,
                    "User unchecked checkbox and removed annotation point")
                overwrote = True
            else:
                self.ui_sub_6.study_checkbox.blockSignals(True)
                self.ui_sub_6.study_checkbox.setChecked(True)
                self.ui_sub_6.study_checkbox.blockSignals(False)
                self.study_recurrence_present = True

                log(logging.INFO, LogType.BUTTON,
                    'User cancelled unchecking and removing annotation point')

        self.ui_sub_6.study_next_patient_button.setEnabled(True)
        self.ui_sub_6.study_next_patient_button.toolTip = ""  # nopep8

    if self.study_recurrence_present is False and overwrote is False:
        log(logging.INFO, LogType.BUTTON, "User unchecked checkbox")


def btn_call_on_selection_changed(self: "registrationViewerWidget") -> None:
    on_selection_changed(self)


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

        log(logging.INFO, LogType.MOUSE,
            f"User changed selection to {self.study_lymphnode_size}")
