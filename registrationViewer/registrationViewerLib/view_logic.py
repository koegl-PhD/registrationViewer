

from enum import Enum
from typing import List, Literal

from qt import QEvent, QObject
import slicer
from slicer import vtkMRMLScalarVolumeNode


class Layout(Enum):
    L_1X2_RED = 801
    L_1X2_GREEN = 802
    L_1X2_YELLOW = 803
    L_2X3 = 701
    L_3X3 = 601


layout_callback = None


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
                elif self.to_layout == "set_2x3_layout":
                    set_2x3_layout()
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


def set_3x3_layout() -> None:

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


#
# registrationViewer
#
