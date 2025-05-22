from enum import Enum
import logging
import random


from typing import List, Literal, Tuple, TYPE_CHECKING

import qt
from qt import QEvent, QObject
import slicer
from slicer import vtkMRMLScalarVolumeNode
import vtk

import registrationViewerLib.utils as utils
from registrationViewerLib.custom_logging import log, LogType

if TYPE_CHECKING:
    from ..registrationViewer import registrationViewerWidget


class Layout(Enum):
    L_1X2_RED = 801
    L_1X2_GREEN = 802
    L_1X2_YELLOW = 803
    L_2X3 = 701
    L_3X3 = 601


layout_callback = None

dragging = {}
disable_sectra = True


def register_layout_callback(callback):
    global layout_callback
    layout_callback = callback


def update_views_with_volume(views: List[str], volume: vtkMRMLScalarVolumeNode) -> None:
    for view in views:
        slice_logic = slicer.app.layoutManager().sliceWidget(view).sliceLogic()
        composite_node = slice_logic.GetSliceCompositeNode()

        if volume:
            composite_node.SetBackgroundVolumeID(volume.GetID())
        else:
            composite_node.SetBackgroundVolumeID(None)

        composite_node.SetForegroundVolumeID(None)


def link_views(views: List[str]) -> None:
    """
    Links the given views.

    @param views: The views to link.
    """

    for view in views:
        sliceLogic = slicer.app.layoutManager().sliceWidget(view).sliceLogic()
        compositeNode = sliceLogic.GetSliceCompositeNode()
        compositeNode.SetLinkedControl(True)


def unlink_views(views: List[str]) -> None:

    for view in views:
        sliceLogic = slicer.app.layoutManager().sliceWidget(view).sliceLogic()
        compositeNode = sliceLogic.GetSliceCompositeNode()
        compositeNode.SetLinkedControl(False)


class ViewClickFilter(QObject):
    def __init__(self, to_layout: Literal["set_1x2_layout", "set_2x3_layout", "set_3x3_layout"], parent=None):
        super().__init__(parent)
        self.view_widgets = {}
        self.to_layout = to_layout

    def add_view(self, name, widget):
        self.view_widgets[widget] = name

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonDblClick:
            if watched in self.view_widgets:
                view_name = self.view_widgets[watched]

                if self.to_layout == "set_1x2_layout":
                    set_1x2_layout(view_name[:-1])

                    log(logging.INFO, LogType.U_MOUSE,
                        f"Double click ~ {view_name}")
                elif self.to_layout == "set_2x3_layout":
                    set_2x3_layout()
                    log(logging.INFO, LogType.U_MOUSE,
                        f"Double click ~ {view_name}")

                elif self.to_layout == "set_3x3_layout":
                    set_3x3_layout()

                return True  # Event has been handled
        return QObject.eventFilter(self, watched, event)


def set_1x2_layout(color: Literal["Red", "Green", "Yellow"]) -> None:
    """
    Create a custom 1x2 layout for the given color.
    The two views (e.g., Red1 and Red2) are shown side by side.

    Parameters:
    - color (str): The color of the slice view to use ("Red", "Green", or "Yellow").
    """

    if color not in ["Red", "Green", "Yellow"]:
        raise ValueError("Invalid color. Must be 'Red', 'Green', or 'Yellow'.")

    if color == "Red":
        orientation = "Axial"
        hexColor = "#F34A33"
    elif color == "Green":
        orientation = "Coronal"
        hexColor = "#6EB04B"
    else:
        orientation = "Sagittal"
        hexColor = "#EDD54C"

    customLayout = f"""
    <layout type="vertical" split="true">
        <item>
            <layout type="horizontal">
                <item>
                    <view class="vtkMRMLSliceNode" singletontag="{color}1">
                    <property name="orientation" action="default">{orientation}</property>
                    <property name="viewlabel" action="default">Fixed - {orientation.lower()}</property>
                    <property name="viewcolor" action="default">{hexColor}</property>
                    </view>
                </item>
                <item>
                    <view class="vtkMRMLSliceNode" singletontag="{color}2">
                    <property name="orientation" action="default">{orientation}</property>
                    <property name="viewlabel" action="default">Moving - {orientation.lower()}</property>
                    <property name="viewcolor" action="default">{hexColor}</property>
                    </view>
                </item>
            </layout>
        </item>
    </layout>
    """

    # Create a unique layout ID based on the color
    layoutIdMap = {"Red": 801, "Green": 802, "Yellow": 803}
    customLayoutId = layoutIdMap[color]

    layoutManager = slicer.app.layoutManager()
    layoutManager.layoutLogic().GetLayoutNode(
    ).AddLayoutDescription(customLayoutId, customLayout)

    # Switch to the new custom layout
    layoutManager.setLayout(customLayoutId)

    # Create event filter
    event_filter = ViewClickFilter(to_layout="set_2x3_layout")

    # Install filter on all views
    view_names = [f"{color}1", f"{color}2"]
    for view_name in view_names:
        slice_widget = layoutManager.sliceWidget(view_name)
        if slice_widget:
            view_widget = slice_widget.sliceView()
            event_filter.add_view(view_name, view_widget)
            view_widget.installEventFilter(event_filter)

    # Keep a reference to the event filter - needs to be global so it won't be deleted
    global _event_filter
    _event_filter = event_filter

    global layout_callback
    if layout_callback:
        layout_callback(Layout.L_1X2_RED if color == "Red" else
                        Layout.L_1X2_GREEN if color == "Green" else
                        Layout.L_1X2_YELLOW)


def set_2x3_layout() -> None:
    customLayout = """
    <layout type="vertical" split="true">
    <item>
        <layout type="horizontal">
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Red1">
            <property name="orientation" action="default">Axial</property>
            <property name="viewlabel" action="default">Fixed - axial</property>
            <property name="viewcolor" action="default">#F34A33</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Green1">
            <property name="orientation" action="default">Coronal</property>
            <property name="viewlabel" action="default">Fixed - coronal</property>
            <property name="viewcolor" action="default">#6EB04B</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Yellow1">
            <property name="orientation" action="default">Sagittal</property>
            <property name="viewlabel" action="default">Fixed - saggital</property>
            <property name="viewcolor" action="default">#EDD54C</property>
            </view>
        </item>
        </layout>
    </item>

    <item>
        <layout type="horizontal">
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Red2">
            <property name="orientation" action="default">Axial</property>
            <property name="viewlabel" action="default">Moving - axial</property>
            <property name="viewcolor" action="default">#F34A33</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Green2">
            <property name="orientation" action="default">Coronal</property>
            <property name="viewlabel" action="default">Moving - coronal</property>
            <property name="viewcolor" action="default">#6EB04B</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Yellow2">
            <property name="orientation" action="default">Sagittal</property>
            <property name="viewlabel" action="default">Moving - sagittal</property>
            <property name="viewcolor" action="default">#EDD54C</property>
            </view>
        </item>
        </layout>
    </item>
    </layout>
    """

    # Built-in layout IDs are all below 100, so you can choose any large random number
    # for your custom layout ID.
    customLayoutId = 701

    layoutManager = slicer.app.layoutManager()
    layoutManager.layoutLogic().GetLayoutNode(
    ).AddLayoutDescription(customLayoutId, customLayout)

    # Switch to the new custom layout
    layoutManager.setLayout(customLayoutId)

    # Create event filter
    event_filter = ViewClickFilter(to_layout="set_1x2_layout")

    # Install filter on all views
    view_names = ['Red1', 'Green1', 'Yellow1', 'Red2', 'Green2', 'Yellow2']
    for view_name in view_names:
        slice_widget = layoutManager.sliceWidget(view_name)
        if slice_widget:
            view_widget = slice_widget.sliceView()
            event_filter.add_view(view_name, view_widget)
            view_widget.installEventFilter(event_filter)

    # Keep a reference to the event filter
    global _event_filter
    _event_filter = event_filter

    global layout_callback
    if layout_callback:
        layout_callback(Layout.L_2X3)


def set_3x3_layout(callback=None) -> None:

    customLayout = """
    <layout type="vertical" split="true">
    <item>
        <layout type="horizontal">
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Red1">
            <property name="orientation" action="default">Axial</property>
            <property name="viewlabel" action="default">Fixed - axial</property>
            <property name="viewcolor" action="default">#F34A33</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Green1">
            <property name="orientation" action="default">Coronal</property>
            <property name="viewlabel" action="default">Fixed - coronal</property>
            <property name="viewcolor" action="default">#6EB04B</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Yellow1">
            <property name="orientation" action="default">Sagittal</property>
            <property name="viewlabel" action="default">Fixed - sagittal</property>
            <property name="viewcolor" action="default">#EDD54C</property>
            </view>
        </item>
        </layout>
    </item>

    <item>
        <layout type="horizontal">
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Red2">
            <property name="orientation" action="default">Axial</property>
            <property name="viewlabel" action="default">Moving - axial</property>
            <property name="viewcolor" action="default">#F34A33</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Green2">
            <property name="orientation" action="default">Coronal</property>
            <property name="viewlabel" action="default">Moving - coronal</property>
            <property name="viewcolor" action="default">#6EB04B</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Yellow2">
            <property name="orientation" action="default">Sagittal</property>
            <property name="viewlabel" action="default">Moving - sagittal</property>
            <property name="viewcolor" action="default">#EDD54C</property>
            </view>
        </item>
        </layout>
    </item>

    <item>
        <layout type="horizontal">
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Red3">
            <property name="orientation" action="default">Axial</property>
            <property name="viewlabel" action="default">Diff - axial</property>
            <property name="viewcolor" action="default">#F34A33</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Green3">
            <property name="orientation" action="default">Coronal</property>
            <property name="viewlabel" action="default">Diff - coronal</property>
            <property name="viewcolor" action="default">#6EB04B</property>
            </view>
        </item>
        <item>
            <view class="vtkMRMLSliceNode" singletontag="Yellow3">
            <property name="orientation" action="default">Sagittal</property>
            <property name="viewlabel" action="default">Diff - sagittal</property>
            <property name="viewcolor" action="default">#EDD54C</property>
            </view>
        </item>
        </layout>
    </item>
    </layout>
    """

    # Built-in layout IDs are all below 100, so you can choose any large random number
    # for your custom layout ID.
    customLayoutId = 601

    layoutManager = slicer.app.layoutManager()
    layoutManager.layoutLogic().GetLayoutNode(
    ).AddLayoutDescription(customLayoutId, customLayout)

    # Switch to the new custom layout
    layoutManager.setLayout(customLayoutId)

    # Create event filter
    event_filter = ViewClickFilter(to_layout="set_1x2_layout")

    view_names = [
        "Red1", "Green1", "Yellow1",
        "Red2", "Green2", "Yellow2",
        "Red3", "Green3", "Yellow3"]

    # Install filter on all views
    for view_name in view_names:
        slice_widget = layoutManager.sliceWidget(view_name)
        if slice_widget:
            view_widget = slice_widget.sliceView()
            event_filter.add_view(view_name, view_widget)
            view_widget.installEventFilter(event_filter)

    # Keep a reference to the event filter
    global _event_filter
    _event_filter = event_filter

    global layout_callback
    if layout_callback:
        layout_callback(Layout.L_3X3)

    if callback:
        callback()


def get_view_offset(view: str) -> float:
    """
    Get the current offset of the given view.
    """

    sliceLogic = slicer.app.layoutManager().sliceWidget(view).sliceLogic()
    sliceNode = sliceLogic.GetSliceNode()

    return sliceNode.GetSliceOffset()


def set_view_offset(view: str, offset: float) -> None:
    """
    Set the offset for the given view.
    """

    sliceLogic = slicer.app.layoutManager().sliceWidget(view).sliceLogic()
    sliceNode = sliceLogic.GetSliceNode()

    sliceNode.SetSliceOffset(offset)


def randomise_offsets(views: List[str], min_v: int = 10, max_v: int = 15) -> None:
    """
    Randomly change the offset of the given views.
    """

    if max_v <= min_v:
        raise ValueError("max_v must be greater than min_v")

    offsets = [get_view_offset(view) for view in views]

    for view, offset in zip(views, offsets):

        change = random.randint(min_v, max_v)
        sign = random.choice([-1, 1])

        set_view_offset(view, offset + change * sign)


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


def attach_continuous_slice_offset_observers(view_name: str) -> None:

    controller = slicer.app.layoutManager().sliceWidget(view_name).sliceController()
    mrml_slider = controller.sliceOffsetSlider()

    q_slider = mrml_slider.findChild(qt.QSlider)
    if not q_slider:
        return

    mrml_slider.valueIsChanging.connect(lambda position: log(
        logging.INFO, LogType.U_MOUSE, f"Slider_Scroll ~ {view_name} ~ pos={position:.1f}") if disable_sectra is False else None)


def enable_sectra_movements(
    self: "registrationViewerWidget",
    sensitivity_pan: float = 1.0,
    sensitivity_window_level: float = 1.0,
    sensitivity_scroll: float = 0.4,
    sensitivity_zoom: float = 0.01
):

    global disable_sectra
    disable_sectra = False

    def createDragHandlers(view_name):
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
            if disable_sectra:
                return

            dragging[view_name]["left_click_drag"] = True
            dragging[view_name]["last_mouse_position"] = caller.GetEventPosition()

        def start_middle_drag(caller, event):
            if disable_sectra:
                return

            dragging[view_name]["middle_click_drag"] = True
            dragging[view_name]["last_mouse_position"] = caller.GetEventPosition()

        def start_right_drag(caller, event):
            if disable_sectra:
                return

            dragging[view_name]["right_click_drag"] = True
            dragging[view_name]["last_mouse_position"] = caller.GetEventPosition()

        def start_wheel_scroll_forward(caller, event):
            if disable_sectra:
                return
            _wheel_scroll(caller, event, 1)

        def start_wheel_scroll_backward(caller, event):
            if disable_sectra:
                return
            _wheel_scroll(caller, event, -1)

        def _wheel_scroll(caller, event, delta):
            sliceLogic = slicer.app.layoutManager().sliceWidget(view_name).sliceLogic()

            sliceOffset = sliceLogic.GetSliceOffset()

            newSliceOffset = sliceOffset + delta * sensitivity_scroll

            sliceLogic.SetSliceOffset(newSliceOffset)

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
                    sliceLogic = slicer.app.layoutManager().sliceWidget(current_view).sliceLogic()
                    sliceOffset = sliceLogic.GetSliceOffset()
                    newSliceOffset = sliceOffset - dy * sensitivity_scroll
                    sliceLogic.SetSliceOffset(newSliceOffset)

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

            if self.current_view in self.views_first_row:
                current_node = self.node_fixed
            elif self.current_view in self.views_second_row:
                current_node = self.node_moving
            else:
                return

            displayNode = current_node.GetDisplayNode()
            if not displayNode:
                return

            current_window = displayNode.GetWindow()
            current_level = displayNode.GetLevel()

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

            dragging[view_name]["last_mouse_position"] = current_mouse_position

            slice_node = slicer.app.layoutManager().sliceWidget(view_name).sliceLogic().GetSliceNode()  # nopep8

            new_FOV_x = slice_node.GetFieldOfView()[0] * (1 - dy)
            new_FOV_y = slice_node.GetFieldOfView()[1] * (1 - dy)
            new_FOV_z = slice_node.GetFieldOfView()[2]

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

            if disable_sectra:
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
            if disable_sectra:
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
        # if interactor.HasObserver(vtk.vtkCommand.LeftButtonPressEvent):
        #     interactor.RemoveObservers(vtk.vtkCommand.LeftButtonPressEvent)
        if interactor.HasObserver(vtk.vtkCommand.RightButtonPressEvent):
            interactor.RemoveObservers(vtk.vtkCommand.RightButtonPressEvent)
        if interactor.HasObserver(vtk.vtkCommand.MouseWheelBackwardEvent):
            interactor.RemoveObservers(vtk.vtkCommand.MouseWheelBackwardEvent)
        if interactor.HasObserver(vtk.vtkCommand.MouseWheelForwardEvent):
            interactor.RemoveObservers(vtk.vtkCommand.MouseWheelForwardEvent)

        (start_letf_drag, start_middle_drag, start_right_drag,
         start_wheel_scroll_forward, start_wheel_scroll_backward, drag, drag_end) = createDragHandlers(view_name)

        interactor.AddObserver(vtk.vtkCommand.LeftButtonPressEvent, start_letf_drag)  # nopep8
        interactor.AddObserver(vtk.vtkCommand.MiddleButtonPressEvent, start_middle_drag)  # nopep8
        interactor.AddObserver(vtk.vtkCommand.RightButtonPressEvent, start_right_drag)  # nopep8
        interactor.AddObserver(vtk.vtkCommand.MouseWheelForwardEvent, start_wheel_scroll_forward)  # nopep8
        interactor.AddObserver(vtk.vtkCommand.MouseWheelBackwardEvent, start_wheel_scroll_backward)  # nopep8

        interactor.AddObserver(vtk.vtkCommand.MouseMoveEvent, drag, 1.0)  # nopep8

        interactor.AddObserver(vtk.vtkCommand.LeftButtonReleaseEvent, drag_end)  # nopep8
        interactor.AddObserver(vtk.vtkCommand.MiddleButtonReleaseEvent, drag_end)  # nopep8
        interactor.AddObserver(vtk.vtkCommand.RightButtonReleaseEvent, drag_end)  # nopep8

        attach_continuous_slice_offset_observers(view_name)


def disable_sectra_movements():
    """
    Disable scrolling through dragging by removing observers from slice views.

    This function should be called after enable_scrolling_through_dragging() 
    to remove the drag event observers.
    """
    global disable_sectra
    disable_sectra = True


def configure_roi(node_roi: slicer.vtkMRMLMarkupsROINode,
                  views: List[str],
                  size: Tuple[int, int, int] = (20, 20, 20)) -> None:

    if not views:
        return
    if not node_roi:
        return

    # geometry
    offsets = [get_view_offset(view) for view in views]
    node_roi.SetCenter(-offsets[2],
                       offsets[1],
                       offsets[0])
    node_roi.SetSize(size)

    # display
    node_display = node_roi.GetDisplayNode()
    if not node_display:
        return

    node_display.SetOpacity(0.5)
    node_display.SetFillOpacity(0)

    node_display.SetTextScale(2.0)
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
