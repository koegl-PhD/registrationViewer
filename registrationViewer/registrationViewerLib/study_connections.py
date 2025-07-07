import logging

from typing import Optional, TYPE_CHECKING, Literal

import slicer
import qt

from registrationViewerLib import log_utils, sectra, study, tasks, tasks_ui_logic, texts, utils, view_logic
from registrationViewerLib.custom_logging import configure_logger, log, LogType

if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget


def set_connections(self: "registrationViewerWidget") -> None:
    """
    Set all UI-backend connections
    """

    self.ui_sub_2.training_examples_SetCheckBox.toggled.connect(
        lambda: btn_call_on_training_example_checkbox(self)
    )

    self.ui_sub_2.data_master_path_edit.currentPathChanged.connect(
        lambda: on_master_json_path_changed(self))

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

    self.ui_sub_6.pause_button.connect("clicked(bool)", on_pause_button)

    self.ui_sub_6.info_button.connect("clicked(bool)", on_info_button)

    self.ui_sub_6.synchronise_views_general.connect("clicked(bool)",
                                                    lambda: btn_call_on_synchronise_views_general(self))

    self.ui_sub_6.start_study_by_user_button.connect("clicked(bool)",
                                                     lambda: btn_call_on_user_start_study(self))
    self.ui_sub_6.study_add_point_button.connect("clicked(bool)",
                                                 lambda: btn_call_on_add_annotation_point(self))
    self.ui_sub_6.study_center_on_user_point_button.connect("clicked(bool)",
                                                            lambda: btn_call_on_center_on_point(self, "user"))
    self.ui_sub_6.study_center_on_gt_point_button.connect("clicked(bool)",
                                                          lambda: btn_call_on_center_on_point(self, "gt"))
    self.ui_sub_6.study_next_task_button.connect("clicked(bool)",
                                                 lambda: btn_call_on_next_task(self))
    self.ui_sub_6.study_checkbox.toggled.connect(
        lambda: btn_call_on_checkbox(self))
    self.ui_sub_6.study_dropdown.currentIndexChanged.connect(
        lambda: btn_call_on_selection_changed(self))


def on_master_json_path_changed(self: "registrationViewerWidget") -> None:
    """
    Once the path to the data master changed ste the checkbox to true
    """
    self.ui_sub_2.data_master_checkbox.setChecked(True)


def on_pause_button() -> None:
    """
    Opens PAUSE popup and logs that the user paused the study
    """

    log(logging.INFO, LogType.U_BUTTON, "User paused study")

    utils.show_fullscreen_popup_with_callback(title=texts.Titles.STUDY_PAUSED,
                                              content=texts.Contents.OK_TO_RESMUE,
                                              center_text=True,
                                              on_ok=lambda: log(logging.INFO, LogType.U_BUTTON, "User resumed study"))


def on_info_button() -> None:
    """
    Opens info popup with available controls and logs that the user paused the study
    """

    log(logging.INFO, LogType.U_BUTTON, "User clicked on info button")

    utils.show_fullscreen_popup_with_image(image_path='/home/koeglf/Documents/code/registrationViewer/registrationViewer/Resources/Icons/legend.png',
                                           title=texts.Titles.STUDY_INSTRUCTIONS,
                                           on_ok=lambda: log(logging.INFO, LogType.U_BUTTON, "User resumed study"))


def btn_call_on_synchronise_views_general(self: "registrationViewerWidget") -> None:

    if self.synchronise_with_displacement_pressed or self.synchronise_manually_pressed:
        text = f"User unsynchronised views ~ {self.study_current_transform_type}"
    else:
        text = f"User synchronised views ~ {self.study_current_transform_type}"

    log(logging.INFO, LogType.U_BUTTON, text)

    on_synchronise_views_general(self)


def key_call_on_synchronise_views_general(self: "registrationViewerWidget") -> None:

    if self.synchronise_with_displacement_pressed or self.synchronise_manually_pressed:
        text = f"User unsynchronised views ~ {self.study_current_transform_type}"
    else:
        text = f"User synchronised views ~ {self.study_current_transform_type}"

    log(logging.INFO, LogType.U_KEYBOARD, text)

    on_synchronise_views_general(self)


def on_synchronise_views_general(self: "registrationViewerWidget") -> None:

    if not self.synchronisation_checks():
        return

    if self.study_current_transform_type == utils.TransformType.NONE:
        print("manual")
        self.on_synchronise_views_manually()
    elif self.study_current_transform_type == utils.TransformType.LINEAR:
        print("linear")
        self.on_synchronise_views_wth_trasform()
        self.use_only_linear_transform = self.crosshair.use_only_linear_transform = True
        utils.set_linear_checkbox_with_signal_block(self, True)
    elif self.study_current_transform_type == utils.TransformType.NONLINEAR:
        print("nonlinear")
        self.on_synchronise_views_wth_trasform()
        self.use_only_linear_transform = self.crosshair.use_only_linear_transform = False
        utils.set_linear_checkbox_with_signal_block(self, False)
    else:
        raise ValueError("Unknown transformation mode")

    if self.synchronise_with_displacement_pressed or self.synchronise_manually_pressed:
        if self.current_patient_transform_type == utils.TransformType.NONE:
            self.ui_sub_6.synchronise_views_general.setText(
                texts.Buttons.TURN_MANUAL_TRANSFORMATION_OFF)
        else:
            self.ui_sub_6.synchronise_views_general.setText(
                texts.Buttons.TURN_TRANSFORMATION_OFF)
    else:
        if self.current_patient_transform_type == utils.TransformType.NONE:
            self.ui_sub_6.synchronise_views_general.setText(
                texts.Buttons.TURN_MANUAL_TRANSFORMATION_ON)
        else:
            self.ui_sub_6.synchronise_views_general.setText(
                texts.Buttons.TURN_TRANSFORMATION_ON)

    self.ui_sub_4.synchronise_views_with_transform.setVisible(False)
    self.ui_sub_4.synchronise_views_manually.setVisible(False)


def btn_call_on_set_radiologist_id(self: "registrationViewerWidget") -> None:
    on_set_radiologist_id(self)


def on_set_radiologist_id(self: "registrationViewerWidget") -> None:

    self.study_data = study.StudyData(
        self.ui_sub_2.data_master_path_edit.currentPath)

    radiologist_id: str = str(
        self.ui_sub_2.radiologistIDTextEdit.toPlainText())

    if radiologist_id == "":
        slicer.util.errorDisplay("Please enter radiologist ID")
        return

    if not self.study_data.participants.__contains__(radiologist_id):
        slicer.util.errorDisplay(
            f"Radiologist {radiologist_id} not found in study data master. Only contains {self.study_data.participants.keys()}")
        return

    radiologist_name = self.study_data.participants[radiologist_id]["name"]

    if not utils.show_question_popup(f"Are you sure {radiologist_name} is the desired participant?"):
        return

    self.current_radiologist_id = radiologist_id

    self.ui_sub_2.start_study_button.setEnabled(True)
    self.ui_sub_2.radiologistSetCheckBox.setChecked(True)
    self.ui_sub_2.start_study_button.toolTip = f"Press to start the study with {radiologist_name}"  # nopep8

    configure_logger(self,
                     f"{self.study_data.path_study_output}{self.current_radiologist_id}/{self.current_radiologist_id}.log",
                     "RegistrationEvaluation")  # nopep8

    if self.ui_sub_2.starting_task_numberTextEdit.toPlainText() == "-1":
        self.ui_sub_2.starting_task_numberTextEdit.setText(
            self.number_of_training_tasks + 1)

    self._set_up_crosshair(False)


def btn_call_on_training_example_checkbox(self: "registrationViewerWidget") -> None:

    self.checkbox_training_cases = self.ui_sub_2.training_examples_SetCheckBox.isChecked()


def btn_call_on_simple_ui(self: "registrationViewerWidget", value: Optional[bool] = None) -> None:
    on_simple_ui(self, value)


def on_simple_ui(self: "registrationViewerWidget", value: Optional[bool] = None, inital: bool = False) -> None:

    self.ui_is_simple = not self.ui_is_simple

    if value is not None:
        self.ui_is_simple = value

    log(logging.INFO, LogType.INTERNAL,
        f"UI set to {'simple' if self.ui_is_simple else 'advanced'}")

    utils.set_ui_simplification(self)

    mainWindow = slicer.util.mainWindow()

    if self.ui_is_simple:
        self.ui_sub_1.simple_ui_button.setText("Advanced UI")
        sectra.set_sectra_style_sheet()
        sectra.enable_sectra_movements()
        view_logic.attach_continuous_slice_offset_observers(self)
        view_logic.attach_key_arrow_observers(self)

        study.hide_organiser_ui_elements(self)

        mainWindow.findChild(
            qt.QWidget, "PanelDockWidget").setMaximumWidth(1000)

        if inital:
            self.ui_sub_6.start_study_by_user_button.setVisible(True)
            self.ui_sub_6.pause_button.setVisible(False)
            self.ui_sub_6.info_button.setVisible(False)
        else:
            self.ui_sub_6.Form_user_study.setVisible(True)
    else:
        self.ui_sub_1.simple_ui_button.setText("Simple UI")

        sectra.set_normal_style_sheet()
        sectra.disable_sectra_movements()
        view_logic.detach_continuous_slice_offset_observers(self)
        view_logic.dettach_key_arrow_observers(self)

        mainWindow.findChild(
            qt.QWidget, "PanelDockWidget").setMaximumWidth(1000)

        study.show_organiser_ui_elements(self)
        self.ui_sub_6.Form_user_study.setVisible(False)


def btn_call_on_start_study(self: "registrationViewerWidget") -> None:

    log(logging.INFO, LogType.U_BUTTON, "Organiser started study")

    organiser_start_study(self)


def organiser_start_study(self: "registrationViewerWidget") -> None:

    on_simple_ui(self, True, inital=True)

    self.ui_sub_6.start_study_by_user_button.setVisible(True)
    self.ui_sub_6.current_rad_name.setVisible(True)
    self.ui_sub_1.simple_ui_button.setVisible(False)

    utils.set_button_texts(self)

    self.combination_starting_offset = int(
        self.ui_sub_2.starting_task_numberTextEdit.toPlainText()) - 1

    if self.combination_starting_offset < self.number_of_full_training_tasks:
        raise ValueError(
            f"You have to start with at least the first normal task, which is {self.number_of_simple_training_tasks + 1}"
        )

    if self.show_training_cases:
        self.current_combination_idx = 0
        self.chunk_idx = 0

        utils.set_buttons_for_simple_training_cases(self)
        study.add_calibration_training_points(self)
    else:
        self.current_combination_idx = self.combination_starting_offset

        self.chunk_idx = self.study_data.get_chunk_idx(
            self.current_patient_name)

    log_utils.log_all_chunks(self)
    log_utils.log_all_tasks(self)

    study.load_current_chunk(self)
    sectra.setup_sectra_movements(self)


def btn_call_on_user_start_study(self: "registrationViewerWidget") -> None:
    log(logging.INFO, LogType.U_BUTTON, "User started study")

    start_study(self)


def start_study(self: "registrationViewerWidget") -> None:
    """
    this should:
    1. load data (in such a way that it is not displayed)
    1. show task description
    1. when data is loaded a button to start task should be displayed
    1. when task is started data should be shown

    """
    self.ui_sub_6.start_study_by_user_button.setVisible(False)
    self.ui_sub_6.pause_button.setVisible(True)
    self.ui_sub_6.info_button.setVisible(True)
    self.ui_sub_6.study_next_task_button.setVisible(True)
    self.ui_sub_6.synchronise_views_general.setVisible(True)

    next_task(self, initial=True)


def btn_call_on_next_task(self: "registrationViewerWidget") -> None:

    log(logging.INFO, LogType.U_BUTTON, self.next_task_log_text)

    next_task(self, initial=False)


def next_task(self: "registrationViewerWidget", initial: bool) -> None:

    is_next_patient = False

    self.study_progress_bar_patients.show()
    self.study_progress_bar_tasks.show()

    if self.first_time_description_show:
        self.full_screen_block.open()

        utils.show_fullscreen_popup_with_callback(title=texts.Titles.STUDY_DESCRIPTION,
                                                  content=texts.Contents.STUDY_DESCRIPTION,
                                                  text_size=14,
                                                  on_ok=lambda: log(logging.INFO, LogType.U_BUTTON, "User closed study description"))

        self.first_time_description_show = False

    if self.show_training_cases:
        if self.first_time_training_description_show and self.is_current_task_training:

            utils.show_fullscreen_popup_with_callback(title=texts.Titles.STUDY_DESCRIPTION,
                                                      content=texts.Contents.TRAINING_STUDY_DESCRIPTION,
                                                      text_size=14,
                                                      on_ok=lambda: log(logging.INFO, LogType.U_BUTTON, "User closed training study description"))

            utils.show_fullscreen_popup_with_image(image_path='/home/koeglf/Documents/code/registrationViewer/registrationViewer/Resources/Icons/legend.png',
                                                   title=texts.Titles.USER_ICONS,
                                                   on_ok=lambda: log(logging.INFO, LogType.U_BUTTON, "User closed info popup"))

            self.first_time_training_description_show = False

            self.study_progress_bar_patients.set_max(
                self.number_of_training_patients)
            self.study_progress_bar_tasks.set_max(1)

    if self.first_time_info_show and not self.is_patient_task_transform_comb_training(self.current_combination_idx + 1):

        self.full_screen_block.open()

        if self.show_training_cases:
            utils.show_fullscreen_popup_with_callback(title=texts.Titles.STUDY_DESCRIPTION,
                                                      content=texts.Contents.STUDY_BEGINS,
                                                      text_size=40,
                                                      center_text=True,
                                                      on_ok=lambda: log(logging.INFO, LogType.U_BUTTON, "User closed study begins"))

        if not self.show_training_cases:
            utils.show_fullscreen_popup_with_image(image_path='/home/koeglf/Documents/code/registrationViewer/registrationViewer/Resources/Icons/legend.png',
                                                   title=texts.Titles.USER_ICONS,
                                                   on_ok=lambda: log(logging.INFO, LogType.U_BUTTON, "User closed info popup"))

        self.study_progress_bar_patients.set_max(
            self.number_of_study_patients(with_calibration=True))
        self.study_progress_bar_tasks.set_max(len(tasks.TASK_ORDER))

        self.first_time_info_show = False

        utils.reset_buttons_after_training_cases(self)

    if self.current_combination_idx == self.number_of_study_tasks + self.number_of_training_tasks - 1:
        study.save_annotations(self,
                               task_type=self.current_task,
                               serialise_to_log=True)

        log(logging.INFO, LogType.U_BUTTON, "User finished study")
        utils.show_fullscreen_popup_with_callback(texts.Titles.STUDY_FINISHED,
                                                  texts.Contents.STUDY_FINISHED.format(
                                                      insert=self.current_radiologist_name),
                                                  center_text=True)
        return

    if not initial:

        study.save_annotations(self,
                               task_type=self.current_task,
                               serialise_to_log=True)

        study.clear_current_user_annotation(self)

        self.current_combination_idx += 1
        self.current_training_combination_idx += 1

        if self.show_training_cases and self.current_training_combination_idx == self.number_of_training_tasks:
            self.current_combination_idx = self.combination_starting_offset

        if not self.study_data.in_chunk(self.current_patient_name, self.chunk_idx):
            self.chunk_idx = self.study_data.get_chunk_idx(
                self.current_patient_name)

            self.full_screen_block.open(content=texts.Contents.LOADING_DATA)
            study.clear_one_chunk(self)
            study.load_current_chunk(self)

    if self.is_current_task_full_training_example:
        self.study_progress_bar_tasks.set_max(len(tasks.TASK_ORDER))
        utils.set_buttons_for_full_training_cases(self)

    if self.current_task == tasks.Task.A_VERTEBRALIS_R and not self.is_current_task_training:
        is_next_patient = True
        self.full_screen_block.open("", "")

        def _on_popup_ok() -> None:
            log(logging.INFO, LogType.U_BUTTON, "User started next patient")

        reg_text = texts.Contents.REGISTRATION_NOT_AVAILABLE if self.current_patient_transform_type == utils.TransformType.NONE else texts.Contents.REGISTRATION_AVAILABLE

        utils.show_fullscreen_popup_with_callback(title="",
                                                  content=texts.Contents.CURRENT_PATIENT_COUNTER.format(current=self.current_patient_idx + 1 - self.number_of_training_patients,
                                                                                                        total=self.number_of_study_patients(
                                                                                                            with_calibration=True),
                                                                                                        registration=reg_text),
                                                  center_text=True,
                                                  on_ok=_on_popup_ok)

    if self.current_task == tasks.Task.A_VERTEBRALIS_R and self.is_current_task_full_training_example:
        is_next_patient = True
        self.full_screen_block.open("", "")

        def _on_popup_ok() -> None:
            log(logging.INFO, LogType.U_BUTTON, "User started next patient")

        reg_text = texts.Contents.REGISTRATION_NOT_AVAILABLE if self.current_patient_transform_type == utils.TransformType.NONE else texts.Contents.REGISTRATION_AVAILABLE

        utils.show_fullscreen_popup_with_callback(title="",
                                                  content=texts.Contents.CURRENT_PATIENT_COUNTER_TRAINING.format(current=self.current_patient_idx + 1,
                                                                                                                 total=self.number_of_training_patients,
                                                                                                                 registration=reg_text),
                                                  center_text=True,
                                                  on_ok=_on_popup_ok)

    if self.is_current_task_simple_training_example:
        is_next_patient = True

    utils.set_up_synchronisation(self, is_next_patient)
    utils.set_up_data_nodes(self)

    log(logging.INFO, LogType.INTERNAL, self.start_task_log_text)

    print(self.current_patient_task_transform_comb)

    self.ui_sub_6.study_next_task_button.setEnabled(False)

    self.ui_sub_6.study_next_task_button.toolTip = texts.ToolTips.ADD_POINT_FIRST

    self.ui_sub_6.study_center_on_user_point_button.setEnabled(False)

    if self.is_current_task_training:
        self.study_progress_bar_patients.set_value(
            self.current_patient_idx + 1
        )
        if self.is_current_task_simple_training_example:
            self.study_progress_bar_tasks.set_value(1)
        else:
            self.study_progress_bar_tasks.set_value(
                ((self.current_combination_idx - self.number_of_simple_training_tasks) % 6) + 1)
    else:

        self.study_progress_bar_tasks.set_value(
            (self.current_combination_idx - self.number_of_training_tasks) % 6 + 1)
        self.study_progress_bar_patients.set_value(
            self.current_patient_idx + 1 - self.number_of_training_patients
        )

    tasks_ui_logic.show_task(self)
    self.study_recurrence_present = False

    if self.current_task == tasks.Task.RECURRENCE:
        if self.is_current_task_full_training_example:
            self.ui_sub_6.study_next_task_button.setText(
                texts.Buttons.TRAINING_NEXT_PATIENT_BUTTON)
        else:
            self.ui_sub_6.study_next_task_button.setText(
                texts.Buttons.NEXT_PATIENT_BUTTON)
    else:
        self.ui_sub_6.study_next_task_button.setText(
            texts.Buttons.NEXT_TASK_BUTTON)

    if self.show_training_cases:
        if self.is_current_task_simple_training_example:
            self.ui_sub_6.study_next_task_button.setText(
                texts.Buttons.TRAINING_NEXT_PATIENT_BUTTON)
        if self.is_current_task_full_training_example:
            self.ui_sub_6.study_next_task_button.setText(
                texts.Buttons.TRAINING_NEXT_TASK_BUTTON)
        if self.current_combination_idx == self.number_of_training_tasks - 1:
            self.ui_sub_6.study_next_task_button.setText(
                texts.Buttons.PROCCED_TO_STUDY)

    if self.current_combination_idx == self.number_of_study_tasks + self.number_of_training_tasks - 1:
        self.ui_sub_6.study_next_task_button.setText(
            texts.Buttons.FINISH_STUDY)


def btn_call_on_add_annotation_point(self: "registrationViewerWidget") -> None:
    log(logging.INFO, LogType.U_BUTTON, "User clicked on add point")

    add_annotation_point(self)


def add_annotation_point(self: "registrationViewerWidget") -> None:

    volume_name = self.node_fixed.GetName()

    overwrote = False

    if self.study_node_annotation is not None:
        if utils.show_warning_popup(title=texts.Titles.WARNING_POINT_EXISTS.format(insert=self.current_task.value),
                                    content=texts.Contents.QUESTION_OVERWRITE_POINT):
            slicer.mrmlScene.RemoveNode(self.study_node_annotation)
            self.study_node_annotation = None
            self.ui_sub_6.study_center_on_user_point_button.setEnabled(False)

            log(logging.INFO, LogType.U_BUTTON,
                "User overwrote annotation point")
            overwrote = True

        else:
            log(logging.INFO, LogType.U_BUTTON,
                "User cancelled overwriting annotation point")
            return

    if self.study_node_annotation is None:
        self.study_node_annotation = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLMarkupsFiducialNode", f"{self.current_task.value}_{self.current_radiologist_id}_{volume_name}")
        self.study_node_annotation.GetDisplayNode(
        ).SetGlyphScale(1)
        self.study_node_annotation.GetDisplayNode(
        ).SetTextScale(2)
        self.study_node_annotation.GetDisplayNode(
        ).SetSelectedColor(utils.Colors.YELLOW.value)

    pos = [view_logic.get_view_offset(view) for view in self.views_first_row]  # nopep8

    self.study_node_annotation.AddControlPointWorld([-pos[2], pos[1], pos[0]],
                                                    'p')

    utils.show_node_only_in_views(self.study_node_annotation,
                                  self.views_first_row)

    if self.current_task == tasks.Task.RECURRENCE:
        # Temporarily block signals wo se don't trigger the callbacks
        utils.set_checkbox_with_signal_block(self, True)

        self.study_recurrence_present = True

    self.ui_sub_6.study_next_task_button.setEnabled(True)
    self.ui_sub_6.study_next_task_button.toolTip = ""  # nopep8
    self.ui_sub_6.study_center_on_user_point_button.setEnabled(True)

    if not overwrote:
        log(logging.INFO, LogType.INTERNAL, "Annotation point added")


def btn_call_on_checkbox(self: "registrationViewerWidget") -> None:
    log(logging.INFO, LogType.U_BUTTON, "User clicked on checkbox")
    checkbox(self)


def checkbox(self: "registrationViewerWidget") -> None:
    if self.current_task != tasks.Task.RECURRENCE:
        return

    if self.ui_sub_6.study_checkbox.isChecked() and self.study_node_annotation is None:
        self.ui_sub_6.study_next_task_button.setEnabled(False)
        self.ui_sub_6.study_next_task_button.toolTip = texts.ToolTips.ADD_POINT_FIRST

        log(logging.INFO, LogType.INTERNAL, "Checkbox checked")

    elif self.ui_sub_6.study_checkbox.isChecked() and self.study_node_annotation:
        self.ui_sub_6.study_next_task_button.setEnabled(True)
        self.ui_sub_6.study_next_task_button.toolTip = ""

        log(logging.INFO, LogType.INTERNAL, "Checkbox checked")

    elif not self.ui_sub_6.study_checkbox.isChecked() and self.study_node_annotation is None:
        self.ui_sub_6.study_next_task_button.setEnabled(True)
        self.ui_sub_6.study_next_task_button.toolTip = ""

        log(logging.INFO, LogType.INTERNAL, "Checkbox unchecked")

    else:
        if utils.show_warning_popup(content=texts.Contents.WARNING_REMOVE_RECURRENCE_POINT,
                                    title=texts.Titles.WARNING):

            slicer.mrmlScene.RemoveNode(self.study_node_annotation)
            self.study_node_annotation = None

            self.ui_sub_6.study_center_on_user_point_button.setEnabled(
                False)

            log(logging.INFO, LogType.U_BUTTON,
                "User unchecked checkbox and removed annotation point")
            log(logging.INFO, LogType.INTERNAL, "Checkbox unchecked")

        else:
            utils.set_checkbox_with_signal_block(self, True)

            log(logging.INFO, LogType.U_BUTTON,
                'User cancelled unchecking and removing annotation point')
            log(logging.INFO, LogType.INTERNAL, "Checkbox checked")

        self.ui_sub_6.study_next_task_button.setEnabled(True)
        self.ui_sub_6.study_next_task_button.toolTip = ""

    self.study_recurrence_present = self.ui_sub_6.study_checkbox.isChecked()


def btn_call_on_center_on_point(self: "registrationViewerWidget",
                                point_type: Literal["user", "gt"]) -> None:

    log(logging.INFO, LogType.U_BUTTON, f"User centered on {point_type} point")

    if point_type == "user":
        point = self.study_node_annotation
        group = self.group_first_row
    elif point_type == "gt":
        point = self.study_node_groundtruth_points[self.current_patient_name][self.current_task]
        group = self.group_second_row
    else:
        log(logging.ERROR, LogType.INTERNAL, "Unknown point type")
        return

    utils.center_on_point(point, group)


def btn_call_on_selection_changed(self: "registrationViewerWidget") -> None:
    on_selection_changed(self)


def on_selection_changed(self: "registrationViewerWidget") -> None:

    if self.current_task == tasks.Task.LYMPH_NODE:

        if self.ui_sub_6.study_dropdown.currentText == texts.Buttons.DROPDOWN_INCREASED:
            self.study_lymphnode_size = "Size increased"
        elif self.ui_sub_6.study_dropdown.currentText == texts.Buttons.DROPDOWN_DECREASED:
            self.study_lymphnode_size = "Size decreased"
        elif self.ui_sub_6.study_dropdown.currentText == texts.Buttons.DROPDOWN_UNCHANGED:
            self.study_lymphnode_size = "Size same"
        else:
            raise ValueError("Unknown lymphnode size")

        log(logging.INFO, LogType.U_BUTTON, self.study_lymphnode_size)
