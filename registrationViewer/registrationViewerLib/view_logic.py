from typing import List, Literal

from qt import QEvent, QObject
import slicer
from slicer import vtkMRMLScalarVolumeNode, vtkMRMLLayoutNode


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


class ViewClickFilter(QObject):
    def __init__(self, to_layout: Literal["set_custom_compare_layout", "set_three_over_three_layout"], parent=None):
        super().__init__(parent)
        self.view_widgets = {}
        self.to_layout = to_layout

    def add_view(self, name, widget):
        self.view_widgets[widget] = name

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonDblClick:
            if watched in self.view_widgets:
                view_name = self.view_widgets[watched]

                view_name = view_name[:-
                                      1] if view_name.endswith('+') else view_name

                if self.to_layout == "set_custom_compare_layout":
                    set_custom_compare_layout(view_name)

                elif self.to_layout == "set_three_over_three_layout":
                    set_three_over_three_layout()

                return True  # Event has been handled
        return QObject.eventFilter(self, watched, event)


def set_custom_compare_layout(view_name: Literal["Red", "Green", "Yellow"]) -> None:
    """
    Create a custom 1x2 layout for the given color.
    The two views (e.g., Red1 and Red2) are shown side by side.

    Parameters:
    - color (str): The color of the slice view to use ("Red", "Green", or "Yellow").
    """

    if view_name not in ["Red", "Green", "Yellow"]:
        raise ValueError("Invalid color. Must be 'Red', 'Green', or 'Yellow'.")

    customLayout = f"""
    <layout type="vertical" split="true">
        <item>
            <layout type="horizontal">
                <item>
                    <view class="vtkMRMLSliceNode" singletontag="{view_name}">
                    </view>
                </item>
                <item>
                    <view class="vtkMRMLSliceNode" singletontag="{view_name}+">
                    </view>
                </item>
            </layout>
        </item>
    </layout>
    """

    # Create a unique layout ID based on the color
    layoutIdMap = {"Red": 801, "Green": 802, "Yellow": 803}
    customLayoutId = layoutIdMap[view_name]

    layoutManager = slicer.app.layoutManager()
    layoutManager.layoutLogic().GetLayoutNode(
    ).AddLayoutDescription(customLayoutId, customLayout)

    # Switch to the new custom layout
    layoutManager.setLayout(customLayoutId)

    # Create event filter
    event_filter = ViewClickFilter(to_layout="set_three_over_three_layout")

    # Install filter on all views
    view_names = [f"{view_name}", f"{view_name}+"]
    for view_name in view_names:
        slice_widget = layoutManager.sliceWidget(view_name)
        if slice_widget:
            view_widget = slice_widget.sliceView()
            event_filter.add_view(view_name, view_widget)
            view_widget.installEventFilter(event_filter)

    # Keep a reference to the event filter - needs to be global so it won't be deleted
    global _event_filter
    _event_filter = event_filter


def set_three_over_three_layout() -> None:

    layoutManager = slicer.app.layoutManager()

    # Switch to the new custom layout
    layoutManager.setLayout(vtkMRMLLayoutNode.SlicerLayoutThreeOverThreeView)

    # Create event filter
    event_filter = ViewClickFilter(to_layout="set_custom_compare_layout")

    # Install filter on all views
    view_names = ['Red', 'Green', 'Yellow', 'Red+', 'Green+', 'Yellow+']
    for view_name in view_names:
        slice_widget = layoutManager.sliceWidget(view_name)
        if slice_widget:
            view_widget = slice_widget.sliceView()
            event_filter.add_view(view_name, view_widget)
            view_widget.installEventFilter(event_filter)

    # Keep a reference to the event filter
    global _event_filter
    _event_filter = event_filter


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


def set_offset_to_ras(position_ras, view):

    layoutManager = slicer.app.layoutManager()

    sliceWidget = layoutManager.sliceWidget(view)

    sliceLogic = sliceWidget.sliceLogic()
    sliceNode = sliceLogic.GetSliceNode()

    # Get the SliceToRAS matrix for the current slice view.
    sliceToRAS = sliceNode.GetSliceToRAS()

    # Typically, the third column of the SliceToRAS matrix is the slice normal.
    normal = [sliceToRAS.GetElement(0, 2),
              sliceToRAS.GetElement(1, 2),
              sliceToRAS.GetElement(2, 2)]

    # Compute the offset as the dot product of the slice normal with the target RAS position.
    offset = normal[0]*position_ras[0] + normal[1] * \
        position_ras[1] + normal[2]*position_ras[2]

    # Set the computed offset for this view.
    set_view_offset(view, offset)
