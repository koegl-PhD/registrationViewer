import logging

from typing import TYPE_CHECKING

import slicer
import vtk

from registrationViewerLib import utils
from registrationViewerLib.custom_logging import log, LogType


if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget

enable_sectra = False
dragging = {}


def set_sectra_style_sheet() -> None:
    """
    Set style to sectra blue
    """
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


def set_normal_style_sheet() -> None:
    """
    Set style to normal slicer
    """
    slicer.app.setStyleSheet("""
            QWidget {
            color: black;
            }
            """)


def _is_right_drag(view_name: str) -> bool:
    if dragging[view_name]["right_click_drag"] and not dragging[view_name]["left_click_drag"] and not dragging[view_name]["middle_click_drag"]:
        return True
    return False


def _is_left_drag(view_name: str) -> bool:
    if dragging[view_name]["left_click_drag"] and not dragging[view_name]["middle_click_drag"] and not dragging[view_name]["right_click_drag"]:
        return True
    return False


def _is_middle_drag(view_name: str) -> bool:
    if dragging[view_name]["middle_click_drag"] and not dragging[view_name]["left_click_drag"] and not dragging[view_name]["right_click_drag"]:
        return True
    return False


def _is_left_and_middle_drag(view_name: str) -> bool:
    if dragging[view_name]["left_click_drag"] and dragging[view_name]["middle_click_drag"] and not dragging[view_name]["right_click_drag"]:
        return True
    return False


def _is_right_and_middle_drag(view_name: str) -> bool:
    if dragging[view_name]["right_click_drag"] and dragging[view_name]["middle_click_drag"] and not dragging[view_name]["left_click_drag"]:
        return True
    return False


def _is_left_and_right_drag(view_name: str) -> bool:
    if dragging[view_name]["left_click_drag"] and dragging[view_name]["right_click_drag"] and not dragging[view_name]["middle_click_drag"]:
        return True
    return False


def setup_sectra_movements(
    self: "registrationViewerWidget",
    sensitivity_pan: float = 1.0,
    sensitivity_window_level: float = 1.0,
    sensitivity_scroll: float = 0.4,
    sensitivity_zoom: float = 0.01
):
    """
    Set up all mouse movmeents to mimic SECTRA
    """

    def create_drag_handlers(view_name):
        dragging[view_name] = {
            "left_click_drag": False,
            "middle_click_drag": False,
            "right_click_drag": False,
            "wheel_scroll": False,
            "last_mouse_position": None,
            "logged_drag_scroll": False,
            "logged_window_level": False,
            "logged_zoom": False,
            "logged_pan": False,
        }

        def start_letf_drag(caller, event):
            if not enable_sectra:
                return

            dragging[view_name]["left_click_drag"] = True
            dragging[view_name]["last_mouse_position"] = caller.GetEventPosition()

        def start_middle_drag(caller, event):
            if not enable_sectra:
                return

            dragging[view_name]["middle_click_drag"] = True
            dragging[view_name]["last_mouse_position"] = caller.GetEventPosition()

        def start_right_drag(caller, event):
            if not enable_sectra:
                return

            dragging[view_name]["right_click_drag"] = True
            dragging[view_name]["last_mouse_position"] = caller.GetEventPosition()

        def start_wheel_scroll_forward(caller, event):
            if not enable_sectra:
                return
            _wheel_scroll(caller, event, 1)

        def start_wheel_scroll_backward(caller, event):
            if not enable_sectra:
                return
            _wheel_scroll(caller, event, -1)

        def _wheel_scroll(caller, event, delta):
            slice_logic = slicer.app.layoutManager().sliceWidget(view_name).sliceLogic()

            slice_offset = slice_logic.GetSliceOffset()

            new_slice_offset = slice_offset + delta * sensitivity_scroll

            slice_logic.SetSliceOffset(new_slice_offset)

            log(logging.INFO, LogType.U_MOUSE,
                f"Wheel_Scroll ~ {view_name} ~ d={delta:+}")

        def _drag_scroll(caller, event):

            if dragging[view_name]["logged_window_level"]:
                log(logging.INFO, LogType.U_MOUSE, "End Window_Level")
                dragging[view_name]["logged_window_level"] = False

            if not dragging[view_name]["logged_drag_scroll"]:
                log(logging.INFO, LogType.U_MOUSE,
                    f"Start Drag_Scroll ~ {view_name}")
                dragging[view_name]["logged_drag_scroll"] = True

            current_mouse_position = caller.GetEventPosition()

            dy = (current_mouse_position[1] -
                  dragging[view_name]["last_mouse_position"][1]) * sensitivity_scroll

            dragging[view_name]["last_mouse_position"] = current_mouse_position

            if abs(dy) > 0:
                position = slicer.util.getNode("*Crosshair*").GetCursorPositionXYZ([0]*3)  # nopep8
                if position is not None:
                    current_view = position.GetName()
                    slice_logic = slicer.app.layoutManager().sliceWidget(current_view).sliceLogic()
                    slice_offset = slice_logic.GetSliceOffset()
                    new_slice_offset = slice_offset - dy * sensitivity_scroll
                    slice_logic.SetSliceOffset(new_slice_offset)

                    log(logging.INFO, LogType.U_MOUSE,
                        f"Drag_Scroll ~ {current_mouse_position}")

        def _drag_window_level(caller, dy):

            if dragging[view_name]["logged_drag_scroll"]:
                log(logging.INFO, LogType.U_MOUSE, "End Drag_Scroll")
                dragging[view_name]["logged_drag_scroll"] = False

            if not dragging[view_name]["logged_window_level"]:
                log(logging.INFO, LogType.U_MOUSE,
                    f"Start Window_Level ~ {view_name}")
                dragging[view_name]["logged_window_level"] = True

            current_mouse_position = caller.GetEventPosition()

            dx = (current_mouse_position[0] -
                  dragging[view_name]["last_mouse_position"][0]) * sensitivity_window_level
            dy = (current_mouse_position[1] -
                  dragging[view_name]["last_mouse_position"][1]) * sensitivity_window_level

            dragging[view_name]["last_mouse_position"] = current_mouse_position

            if utils.get_cursor_view_name() in self.views_first_row:
                current_node = self.node_fixed
            elif utils.get_cursor_view_name() in self.views_second_row:
                current_node = self.node_moving
            else:
                return

            display_node = current_node.GetDisplayNode()
            if not display_node:
                return

            current_window = display_node.GetWindow()
            current_level = display_node.GetLevel()

            new_window = max(1, current_window - dx)
            new_level = current_level + dy

            utils.set_window_level(current_node,
                                   new_window,
                                   new_level)

            log(logging.INFO, LogType.U_MOUSE,
                f"Window_Level ~ {current_mouse_position}")

        def _drag_zoom(caller, event):

            if dragging[view_name]["logged_pan"]:
                log(logging.INFO, LogType.U_MOUSE, "End Pan")
                dragging[view_name]["logged_pan"] = False

            if not dragging[view_name]["logged_zoom"]:
                log(logging.INFO, LogType.U_MOUSE, f"Start Zoom ~ {view_name}")
                dragging[view_name]["logged_zoom"] = True

            current_mouse_position = caller.GetEventPosition()

            dy = (current_mouse_position[1] -
                  dragging[view_name]["last_mouse_position"][1]) * sensitivity_zoom

            # guard against inversion
            if 1 - dy <= 0:
                print("guarding against inv")
                return

            dragging[view_name]["last_mouse_position"] = current_mouse_position

            slice_node = slicer.app.layoutManager().sliceWidget(view_name).sliceLogic().GetSliceNode()  # nopep8

            new_FOV_x = slice_node.GetFieldOfView()[0] * (1 - dy)  # nopep8 pylint: disable=invalid-name
            new_FOV_y = slice_node.GetFieldOfView()[1] * (1 - dy)  # nopep8 pylint: disable=invalid-name
            new_FOV_z = slice_node.GetFieldOfView()[2]             # nopep8 pylint: disable=invalid-name

            # guard against zooming out too much: all have to be smaller than 2000
            if all(fov < 2000 for fov in (new_FOV_x, new_FOV_y, new_FOV_z)):
                slice_node.SetFieldOfView(new_FOV_x, new_FOV_y, new_FOV_z)
                slice_node.UpdateMatrices()

            log(logging.INFO, LogType.U_MOUSE,
                f"Zoom ~ {current_mouse_position} ~ d={dy:+}")

        def _drag_pan(caller, event):

            if dragging[view_name]["logged_zoom"]:
                log(logging.INFO, LogType.U_MOUSE, "End Zoom")
                dragging[view_name]["logged_zoom"] = False

            if not dragging[view_name]["logged_pan"]:
                log(logging.INFO, LogType.U_MOUSE, f"Start Pan ~ {view_name}")
                dragging[view_name]["logged_pan"] = True

            slice_widget = slicer.app.layoutManager().sliceWidget(view_name)
            slice_node = slice_widget.sliceLogic().GetSliceNode()

            # Get current zoom factor (field of view)
            slice_view = slice_widget.sliceView()
            field_of_view = slice_view.width / slice_node.GetFieldOfView()[0]

            adjusted_sensitivity = sensitivity_pan / field_of_view

            current_mouse_position = caller.GetEventPosition()

            dx = (current_mouse_position[0] - dragging[view_name]["last_mouse_position"][0]) \
                * adjusted_sensitivity
            dy = (current_mouse_position[1] - dragging[view_name]["last_mouse_position"][1]) \
                * adjusted_sensitivity

            dragging[view_name]["last_mouse_position"] = current_mouse_position

            origin = list(slice_node.GetXYZOrigin())

            origin[0] -= dx
            origin[1] -= dy

            slice_node.SetXYZOrigin(origin)

            log(logging.INFO, LogType.U_MOUSE,
                f"Pan ~ {current_mouse_position}")

        def drag(caller, event):

            if not enable_sectra:
                return

            if _is_left_drag(view_name):
                _drag_pan(caller, event)
            elif _is_middle_drag(view_name):
                _drag_window_level(caller, event)
            elif _is_left_and_middle_drag(view_name) or _is_right_and_middle_drag(view_name):
                _drag_scroll(caller, event)
            elif _is_left_and_right_drag(view_name):
                _drag_zoom(caller, event)

        def drag_end(caller, event):
            if not enable_sectra:
                return

            if dragging[view_name]["logged_drag_scroll"]:
                log(logging.INFO, LogType.U_MOUSE, "End Scroll")
            if dragging[view_name]["logged_window_level"]:
                log(logging.INFO, LogType.U_MOUSE, "End Window_Level")
            if dragging[view_name]["logged_zoom"]:
                log(logging.INFO, LogType.U_MOUSE, "End Zoom")
            if dragging[view_name]["logged_pan"]:
                log(logging.INFO, LogType.U_MOUSE, "End Pan")

            dragging[view_name]["middle_click_drag"] = False
            dragging[view_name]["left_click_drag"] = False
            dragging[view_name]["right_click_drag"] = False
            dragging[view_name]["last_mouse_position"] = None
            dragging[view_name]["logged_drag_scroll"] = False
            dragging[view_name]["logged_window_level"] = False
            dragging[view_name]["logged_zoom"] = False
            dragging[view_name]["logged_pan"] = False

        return (start_letf_drag, start_middle_drag, start_right_drag,
                start_wheel_scroll_forward, start_wheel_scroll_backward, drag, drag_end)

    for view_name in self.views_first_row + self.views_second_row:

        interactor = slicer.app.layoutManager().sliceWidget(
            view_name).sliceView().interactor()

        if interactor.HasObserver(vtk.vtkCommand.MiddleButtonPressEvent):
            interactor.RemoveObservers(vtk.vtkCommand.MiddleButtonPressEvent)
        if interactor.HasObserver(vtk.vtkCommand.RightButtonPressEvent):
            interactor.RemoveObservers(vtk.vtkCommand.RightButtonPressEvent)
        if interactor.HasObserver(vtk.vtkCommand.MouseWheelBackwardEvent):
            interactor.RemoveObservers(vtk.vtkCommand.MouseWheelBackwardEvent)
        if interactor.HasObserver(vtk.vtkCommand.MouseWheelForwardEvent):
            interactor.RemoveObservers(vtk.vtkCommand.MouseWheelForwardEvent)

        (start_letf_drag, start_middle_drag, start_right_drag,
         start_wheel_scroll_forward, start_wheel_scroll_backward, drag, drag_end) = create_drag_handlers(view_name)

        interactor.AddObserver(vtk.vtkCommand.LeftButtonPressEvent, start_letf_drag)  # nopep8
        interactor.AddObserver(vtk.vtkCommand.MiddleButtonPressEvent, start_middle_drag)  # nopep8
        interactor.AddObserver(vtk.vtkCommand.RightButtonPressEvent, start_right_drag)  # nopep8
        interactor.AddObserver(vtk.vtkCommand.MouseWheelForwardEvent, start_wheel_scroll_forward)  # nopep8
        interactor.AddObserver(vtk.vtkCommand.MouseWheelBackwardEvent, start_wheel_scroll_backward)  # nopep8

        interactor.AddObserver(vtk.vtkCommand.MouseMoveEvent, drag, 1.0)  # nopep8

        interactor.AddObserver(vtk.vtkCommand.LeftButtonReleaseEvent, drag_end)  # nopep8
        interactor.AddObserver(vtk.vtkCommand.MiddleButtonReleaseEvent, drag_end)  # nopep8
        interactor.AddObserver(vtk.vtkCommand.RightButtonReleaseEvent, drag_end)  # nopep8


def enable_sectra_movements() -> None:
    """
    Enable sectra movements
    """

    global enable_sectra
    enable_sectra = True


def disable_sectra_movements() -> None:
    """
    Disable scrolling through dragging by removing observers from slice views.

    This function should be called after enable_scrolling_through_dragging() 
    to remove the drag event observers.
    """
    global enable_sectra
    enable_sectra = False
